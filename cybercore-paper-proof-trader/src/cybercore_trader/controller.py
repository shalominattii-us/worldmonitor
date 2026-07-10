from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .approval import validate_approval
from .brief import proof_digest
from .config import RiskPolicy, Settings
from .executor import (
    ExecutorError,
    submit_to_existing_executor,
    verify_existing_order,
)
from .hedge import (
    build_hedge_plan,
    read_daily_hedge_lock,
    write_daily_hedge_lock,
)
from .ledger import (
    append_jsonl,
    load_candidates,
    load_paper_trades,
    rewrite_candidates,
)
from .models import CandidateOrder, ProofResult
from .qualifier import evaluate_paper_proof


@dataclass(frozen=True)
class DailyLiveState:
    balance_usd: Decimal
    live_notional_usd: Decimal
    live_realized_pnl_usd: Decimal
    live_trade_count: int
    hedge_order_count: int = 0


def _read_daily_state(
    path: Path,
    date_key: str,
    balance_usd: Decimal,
) -> DailyLiveState:
    if not path.exists():
        return DailyLiveState(
            balance_usd,
            Decimal("0"),
            Decimal("0"),
            0,
            0,
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DailyLiveState(
            balance_usd,
            Decimal("0"),
            Decimal("0"),
            0,
            0,
        )

    if data.get("date") != date_key:
        return DailyLiveState(
            balance_usd,
            Decimal("0"),
            Decimal("0"),
            0,
            0,
        )

    return DailyLiveState(
        balance_usd=balance_usd,
        live_notional_usd=Decimal(
            str(data.get("live_notional_usd", "0"))
        ),
        live_realized_pnl_usd=Decimal(
            str(data.get("live_realized_pnl_usd", "0"))
        ),
        live_trade_count=int(data.get("live_trade_count", 0)),
        hedge_order_count=int(data.get("hedge_order_count", 0)),
    )


def _write_daily_state(
    path: Path,
    date_key: str,
    state: DailyLiveState,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "date": date_key,
                "balance_usd": str(state.balance_usd),
                "live_notional_usd": str(
                    state.live_notional_usd
                ),
                "live_realized_pnl_usd": str(
                    state.live_realized_pnl_usd
                ),
                "live_trade_count": state.live_trade_count,
                "hedge_order_count": state.hedge_order_count,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def decision_for_candidate(
    candidate: CandidateOrder,
    proof: ProofResult,
    approval_valid: bool,
    settings: Settings,
    policy: RiskPolicy,
    daily: DailyLiveState,
    hedge_lock_active: bool = False,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if not settings.live_trading_enabled:
        reasons.append("deployment live switch is off")
    if not proof.passed:
        reasons.append("paper proof policy failed")
    if not approval_valid:
        reasons.append(
            "morning brief approval is absent or expired"
        )
    if hedge_lock_active:
        reasons.append("daily autohedge lock is active")
    if policy.hedge_required and not settings.autohedge_enabled:
        reasons.append("required autohedge is disabled")
    if candidate.quote_size < policy.minimum_quote_size_usd:
        reasons.append("candidate below minimum quote size")
    if candidate.quote_size > policy.maximum_live_order_quote_usd:
        reasons.append("candidate above per-order cap")
    if daily.live_trade_count >= policy.maximum_live_trades_per_day:
        reasons.append("daily trade-count cap reached")
    if (
        policy.hedge_required
        and daily.hedge_order_count
        >= policy.maximum_hedges_per_day
    ):
        reasons.append("daily hedge-count cap reached")

    expected_hedge = Decimal("0")
    if policy.hedge_required:
        expected_hedge = min(
            candidate.quote_size * policy.hedge_ratio,
            policy.maximum_hedge_quote_usd,
        )
        if expected_hedge < policy.minimum_hedge_quote_usd:
            reasons.append(
                "expected hedge is below the minimum hedge size"
            )

    max_daily_notional = (
        daily.balance_usd
        * policy.maximum_live_daily_notional_pct_of_balance
        / Decimal("100")
    )
    projected_notional = (
        daily.live_notional_usd
        + candidate.quote_size
        + expected_hedge
    )
    if projected_notional > max_daily_notional:
        reasons.append("daily notional cap reached")

    max_daily_loss = (
        daily.balance_usd
        * policy.maximum_live_daily_loss_pct_of_balance
        / Decimal("100")
    )
    if daily.live_realized_pnl_usd <= -max_daily_loss:
        reasons.append("daily loss cap reached")

    return ("live" if not reasons else "paper", reasons)


def _accepted_order_id(result: dict) -> str:
    return str(
        result.get("exchange_order_id")
        or result.get("order_id")
        or ""
    ).strip()


def process_once(
    settings: Settings,
    policy: RiskPolicy,
    balance_provider: Callable[[], Decimal],
) -> dict:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    paper_path = settings.data_dir / "paper_trades.jsonl"
    candidates_path = settings.data_dir / "candidates.jsonl"
    approval_path = settings.data_dir / "morning_approval.json"
    state_path = settings.data_dir / "daily_live_state.json"
    hedge_lock_path = settings.data_dir / "hedge_lock.json"
    audit_path = settings.log_dir / "trade_decisions.jsonl"

    trades = load_paper_trades(paper_path)
    proof = evaluate_paper_proof(trades, policy)
    digest = proof_digest(proof)
    approval_valid, approval_reason = validate_approval(
        approval_path,
        settings.timezone,
        policy,
        digest,
    )

    now = datetime.now(settings.timezone)
    balance = balance_provider()
    daily = _read_daily_state(
        state_path,
        now.date().isoformat(),
        balance,
    )
    hedge_lock_active, hedge_lock_reason = read_daily_hedge_lock(
        hedge_lock_path,
        timezone=settings.timezone,
    )

    candidates = load_candidates(candidates_path)
    remaining: list[CandidateOrder] = []
    primary_submitted = 0
    hedges_submitted = 0
    hedge_failures = 0

    for candidate in candidates:
        mode, reasons = decision_for_candidate(
            candidate,
            proof,
            approval_valid,
            settings,
            policy,
            daily,
            hedge_lock_active,
        )

        audit = {
            "ts": now.isoformat(),
            "candidate": candidate.to_json(),
            "decision": mode,
            "reasons": reasons,
            "proof_score": str(proof.score),
            "proof_digest": digest,
            "approval_valid": approval_valid,
            "approval_reason": approval_reason,
            "autohedge_enabled": settings.autohedge_enabled,
            "hedge_required": policy.hedge_required,
            "hedge_lock_active": hedge_lock_active,
            "hedge_lock_reason": hedge_lock_reason,
        }

        if mode != "live":
            remaining.append(candidate)
            append_jsonl(audit_path, audit)
            continue

        primary_payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": candidate.product_id,
            "side": candidate.side,
            "quote_size": str(candidate.quote_size),
            "source": "moltbook-paper-proof",
            "strategy_id": candidate.strategy_id,
            "order_role": "primary",
            "paper_proof_score": str(proof.score),
            "paper_proof_digest": digest,
            "morning_approval_date": now.date().isoformat(),
        }

        try:
            primary_result = submit_to_existing_executor(
                settings.coinbase_executor_url,
                primary_payload,
            )
            audit["executor_result"] = primary_result

            if not bool(primary_result.get("accepted")):
                remaining.append(candidate)
                append_jsonl(audit_path, audit)
                continue

            primary_order_id = _accepted_order_id(primary_result)
            if not primary_order_id:
                raise ExecutorError(
                    "accepted primary order did not return an order id"
                )

            primary_submitted += 1
            primary_verification = verify_existing_order(
                settings.coinbase_order_status_url_template,
                primary_order_id,
                settings.hedge_verification_timeout_seconds,
            )
            audit["primary_verification"] = primary_verification

            hedge_quote_size = Decimal("0")

            if policy.hedge_required:
                hedge_plan = build_hedge_plan(
                    candidate,
                    primary_order_id,
                    primary_verification,
                    policy,
                )
                audit["hedge_plan"] = {
                    "product_id": hedge_plan.product_id,
                    "side": hedge_plan.side,
                    "quote_size": str(hedge_plan.quote_size),
                    "mode": hedge_plan.mode,
                    "reduce_only": hedge_plan.reduce_only,
                    "parent_exchange_order_id": (
                        hedge_plan.parent_exchange_order_id
                    ),
                    "trigger_distance_bps": (
                        None
                        if hedge_plan.trigger_distance_bps is None
                        else str(hedge_plan.trigger_distance_bps)
                    ),
                }

                hedge_payload = hedge_plan.to_executor_payload(
                    client_order_id=str(uuid.uuid4()),
                    strategy_id=candidate.strategy_id,
                    proof_score=str(proof.score),
                    proof_digest=digest,
                    approval_date=now.date().isoformat(),
                )

                hedge_result = submit_to_existing_executor(
                    settings.coinbase_executor_url,
                    hedge_payload,
                )
                audit["hedge_executor_result"] = hedge_result

                if not bool(hedge_result.get("accepted")):
                    raise ExecutorError(
                        "executor rejected the required hedge"
                    )

                hedge_order_id = _accepted_order_id(hedge_result)
                if not hedge_order_id:
                    raise ExecutorError(
                        "accepted hedge did not return an order id"
                    )

                hedge_verification = verify_existing_order(
                    settings.coinbase_order_status_url_template,
                    hedge_order_id,
                    settings.hedge_verification_timeout_seconds,
                )
                audit["hedge_verification"] = hedge_verification

                if not bool(hedge_verification.get("verified")):
                    raise ExecutorError(
                        "hedge order was not independently verified"
                    )

                hedge_status = str(
                    hedge_verification.get("status", "")
                ).lower()
                if hedge_status not in {
                    "accepted",
                    "open",
                    "filled",
                    "partially_filled",
                    "trigger_pending",
                }:
                    raise ExecutorError(
                        f"hedge verification status is not active: "
                        f"{hedge_status or 'missing'}"
                    )

                verified_parent = str(
                    hedge_verification.get(
                        "parent_exchange_order_id"
                    )
                    or ""
                ).strip()
                if (
                    verified_parent
                    and verified_parent != primary_order_id
                ):
                    raise ExecutorError(
                        "hedge verifier returned the wrong parent order"
                    )

                hedge_quote_size = hedge_plan.quote_size
                hedges_submitted += 1

            daily = DailyLiveState(
                balance_usd=balance,
                live_notional_usd=(
                    daily.live_notional_usd
                    + candidate.quote_size
                    + hedge_quote_size
                ),
                live_realized_pnl_usd=(
                    daily.live_realized_pnl_usd
                ),
                live_trade_count=daily.live_trade_count + 1,
                hedge_order_count=(
                    daily.hedge_order_count
                    + (1 if hedge_quote_size > 0 else 0)
                ),
            )

        except (ExecutorError, ValueError) as exc:
            hedge_failures += 1
            hedge_lock_active = True
            hedge_lock_reason = str(exc)
            audit["hedge_failure"] = {
                "error": str(exc),
                "daily_lock_activated": True,
            }

            write_daily_hedge_lock(
                hedge_lock_path,
                timezone=settings.timezone,
                reason=str(exc),
                primary_order_id=(
                    locals().get("primary_order_id")
                    if "primary_order_id" in locals()
                    else None
                ),
            )

        append_jsonl(audit_path, audit)

    rewrite_candidates(candidates_path, remaining)
    _write_daily_state(
        state_path,
        now.date().isoformat(),
        daily,
    )

    return {
        "proof_passed": proof.passed,
        "proof_score": str(proof.score),
        "approval_valid": approval_valid,
        "approval_reason": approval_reason,
        "candidate_count": len(candidates),
        "live_submitted": primary_submitted,
        "hedges_submitted": hedges_submitted,
        "hedge_failures": hedge_failures,
        "hedge_lock_active": hedge_lock_active,
        "hedge_lock_reason": hedge_lock_reason,
        "remaining_candidates": len(remaining),
        "live_trade_count_today": daily.live_trade_count,
        "hedge_order_count_today": daily.hedge_order_count,
        "live_notional_today": str(daily.live_notional_usd),
    }
