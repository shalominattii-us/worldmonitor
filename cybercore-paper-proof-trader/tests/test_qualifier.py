from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from cybercore_trader.config import RiskPolicy
from cybercore_trader.models import PaperTrade
from cybercore_trader.qualifier import evaluate_paper_proof


def policy() -> RiskPolicy:
    return RiskPolicy.load(Path("config/risk-policy.json"))


def test_paper_proof_requires_trades():
    proof = evaluate_paper_proof([], policy())
    assert proof.passed is False
    assert "no paper trades available" in proof.reasons


def test_profitable_paper_window_can_qualify():
    now = datetime.now(timezone.utc)
    trades = []

    for index in range(40):
        won = index % 4 != 0
        trades.append(PaperTrade(
            trade_id=str(index),
            strategy_id="aggregate",
            product_id="BTC-USD",
            side="BUY",
            opened_at=now - timedelta(days=4, minutes=index + 1),
            closed_at=now - timedelta(days=index % 4, minutes=index),
            quote_size=Decimal("5"),
            pnl_quote=Decimal("0.10") if won else Decimal("-0.05"),
            fees_quote=Decimal("0.01"),
            slippage_bps=Decimal("3"),
        ))

    proof = evaluate_paper_proof(trades, policy())
    assert proof.metrics["trade_count"] == 40
    assert proof.passed is True
