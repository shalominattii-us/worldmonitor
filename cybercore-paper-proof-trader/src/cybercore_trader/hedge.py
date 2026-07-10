from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .config import RiskPolicy
from .models import CandidateOrder


FILLED_STATUSES = {"filled", "partially_filled"}
VALID_SIDES = {"BUY", "SELL"}


@dataclass(frozen=True)
class HedgePlan:
    product_id: str
    side: str
    quote_size: Decimal
    mode: str
    reduce_only: bool
    parent_exchange_order_id: str
    trigger_distance_bps: Decimal | None

    def to_executor_payload(
        self,
        *,
        client_order_id: str,
        strategy_id: str,
        proof_score: str,
        proof_digest: str,
        approval_date: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "client_order_id": client_order_id,
            "product_id": self.product_id,
            "side": self.side,
            "quote_size": str(self.quote_size),
            "source": "moltbook-autohedge",
            "strategy_id": strategy_id,
            "order_role": "protective_hedge",
            "parent_exchange_order_id": self.parent_exchange_order_id,
            "hedge_mode": self.mode,
            "reduce_only": self.reduce_only,
            "paper_proof_score": proof_score,
            "paper_proof_digest": proof_digest,
            "morning_approval_date": approval_date,
        }
        if self.trigger_distance_bps is not None:
            payload["trigger_distance_bps"] = str(
                self.trigger_distance_bps
            )
        return payload


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def build_hedge_plan(
    candidate: CandidateOrder,
    order_id: str,
    verification: dict[str, Any],
    policy: RiskPolicy,
) -> HedgePlan:
    if not bool(verification.get("verified")):
        raise ValueError("primary fill was not independently verified")

    status = str(verification.get("status", "")).lower()
    if status not in FILLED_STATUSES:
        raise ValueError(
            f"primary order status is not hedgeable: {status or 'missing'}"
        )

    verified_order_id = str(
        verification.get("exchange_order_id") or ""
    ).strip()
    if not verified_order_id or verified_order_id != str(order_id):
        raise ValueError("verified exchange order id does not match")

    filled_quote_size = _decimal(
        verification.get("filled_quote_size"),
        "filled_quote_size",
    )
    if filled_quote_size <= 0:
        raise ValueError("filled_quote_size must be positive")

    capability = verification.get("hedge_capability")
    if not isinstance(capability, dict):
        raise ValueError("hedge capability was not supplied by verifier")

    if not bool(capability.get("supported")):
        raise ValueError("executor does not support a verified hedge")

    mode = str(capability.get("mode", "")).strip()
    if mode not in policy.allowed_hedge_modes:
        raise ValueError(f"hedge mode is not allowed: {mode or 'missing'}")

    product_id = str(
        capability.get("product_id") or candidate.product_id
    ).strip().upper()
    if product_id not in policy.allowed_hedge_products:
        raise ValueError(
            f"hedge product is not allowlisted: {product_id}"
        )

    side = str(capability.get("hedge_side", "")).strip().upper()
    if side not in VALID_SIDES:
        raise ValueError("verifier must supply hedge_side BUY or SELL")

    if side == candidate.side:
        raise ValueError("hedge side cannot equal the primary order side")

    reduce_only = bool(capability.get("reduce_only"))
    if not reduce_only:
        raise ValueError("hedge must be reduce-only")

    quote_size = filled_quote_size * policy.hedge_ratio

    capability_max = capability.get("maximum_quote_size")
    if capability_max is not None:
        quote_size = min(
            quote_size,
            _decimal(
                capability_max,
                "hedge_capability.maximum_quote_size",
            ),
        )

    quote_size = min(
        quote_size,
        policy.maximum_hedge_quote_usd,
    )

    if quote_size < policy.minimum_hedge_quote_usd:
        raise ValueError(
            "calculated hedge is below the minimum hedge size"
        )

    trigger_distance = (
        policy.protective_stop_distance_bps
        if mode == "protective_stop"
        else None
    )

    return HedgePlan(
        product_id=product_id,
        side=side,
        quote_size=quote_size,
        mode=mode,
        reduce_only=True,
        parent_exchange_order_id=verified_order_id,
        trigger_distance_bps=trigger_distance,
    )


def write_daily_hedge_lock(
    path: Path,
    *,
    timezone: Any,
    reason: str,
    primary_order_id: str | None,
) -> None:
    now = datetime.now(timezone)
    payload = {
        "date": now.date().isoformat(),
        "created_at": now.isoformat(),
        "reason": reason,
        "primary_order_id": primary_order_id,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_daily_hedge_lock(
    path: Path,
    *,
    timezone: Any,
) -> tuple[bool, str]:
    if not path.exists():
        return False, ""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, "hedge lock file is invalid"

    today = datetime.now(timezone).date().isoformat()
    if payload.get("date") != today:
        return False, ""

    return True, str(payload.get("reason") or "daily hedge lock active")
