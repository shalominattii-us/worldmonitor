from __future__ import annotations

from decimal import Decimal

from .config import RiskPolicy
from .models import PaperTrade, ProofResult


ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def _clamp(value: Decimal, low: Decimal = ZERO, high: Decimal = ONE) -> Decimal:
    return min(max(value, low), high)


def evaluate_paper_proof(
    trades: list[PaperTrade],
    policy: RiskPolicy,
    strategy_id: str | None = None,
) -> ProofResult:
    selected = [t for t in trades if strategy_id is None or t.strategy_id == strategy_id]
    selected = sorted(selected, key=lambda t: t.closed_at)[-policy.paper_window_trades :]

    if not selected:
        return ProofResult(
            passed=False,
            score=ZERO,
            reasons=("no paper trades available",),
            metrics={
                "trade_count": 0,
                "distinct_days": 0,
                "win_rate": ZERO,
                "expectancy_bps": ZERO,
                "profit_factor": ZERO,
                "max_drawdown_pct": ZERO,
                "average_slippage_bps": ZERO,
            },
        )

    trade_count = len(selected)
    distinct_days = len({trade.closed_at.date() for trade in selected})
    wins = sum(1 for trade in selected if trade.net_pnl_quote > 0)
    win_rate = Decimal(wins) / Decimal(trade_count)
    expectancy_bps = sum((trade.return_bps for trade in selected), ZERO) / Decimal(trade_count)

    gross_profit = sum(
        (trade.net_pnl_quote for trade in selected if trade.net_pnl_quote > 0),
        ZERO,
    )
    gross_loss = abs(sum(
        (trade.net_pnl_quote for trade in selected if trade.net_pnl_quote < 0),
        ZERO,
    ))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("999")

    average_slippage = sum(
        (abs(trade.slippage_bps) for trade in selected),
        ZERO,
    ) / Decimal(trade_count)

    equity = ZERO
    peak = ZERO
    max_drawdown = ZERO
    deployed = max(sum((trade.quote_size for trade in selected), ZERO), Decimal("1"))

    for trade in selected:
        equity += trade.net_pnl_quote
        peak = max(peak, equity)
        drawdown = peak - equity
        max_drawdown = max(max_drawdown, drawdown)

    max_drawdown_pct = (max_drawdown / deployed) * HUNDRED

    score_parts = [
        _clamp(Decimal(trade_count) / Decimal(max(policy.minimum_paper_trades, 1))),
        _clamp(Decimal(distinct_days) / Decimal(max(policy.minimum_distinct_days, 1))),
        _clamp(win_rate / max(policy.minimum_win_rate, Decimal("0.0001"))),
        _clamp(expectancy_bps / max(policy.minimum_expectancy_bps, Decimal("0.0001"))),
        _clamp(profit_factor / max(policy.minimum_profit_factor, Decimal("0.0001"))),
        _clamp(
            ONE - (max_drawdown_pct / max(policy.maximum_drawdown_pct, Decimal("0.0001")))
        ),
        _clamp(
            ONE - (
                average_slippage
                / max(policy.maximum_average_slippage_bps, Decimal("0.0001"))
            )
        ),
    ]
    score = sum(score_parts, ZERO) / Decimal(len(score_parts))

    reasons: list[str] = []
    checks = [
        (trade_count >= policy.minimum_paper_trades, "insufficient paper trades"),
        (distinct_days >= policy.minimum_distinct_days, "insufficient distinct paper days"),
        (win_rate >= policy.minimum_win_rate, "paper win rate below threshold"),
        (expectancy_bps >= policy.minimum_expectancy_bps, "paper expectancy below threshold"),
        (profit_factor >= policy.minimum_profit_factor, "paper profit factor below threshold"),
        (max_drawdown_pct <= policy.maximum_drawdown_pct, "paper drawdown above threshold"),
        (
            average_slippage <= policy.maximum_average_slippage_bps,
            "paper slippage above threshold",
        ),
        (score >= policy.minimum_proof_score, "paper proof score below threshold"),
    ]

    for passed, reason in checks:
        if not passed:
            reasons.append(reason)

    return ProofResult(
        passed=not reasons,
        score=score,
        reasons=tuple(reasons),
        metrics={
            "trade_count": trade_count,
            "distinct_days": distinct_days,
            "win_rate": win_rate,
            "expectancy_bps": expectancy_bps,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "average_slippage_bps": average_slippage,
        },
    )
