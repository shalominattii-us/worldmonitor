from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from cybercore_trader.config import RiskPolicy
from cybercore_trader.hedge import build_hedge_plan
from cybercore_trader.models import CandidateOrder


def policy() -> RiskPolicy:
    return RiskPolicy.load(Path("config/risk-policy.json"))


def candidate() -> CandidateOrder:
    return CandidateOrder(
        candidate_id="candidate-1",
        strategy_id="aggregate",
        product_id="BTC-USD",
        side="BUY",
        quote_size=Decimal("5"),
        confidence=Decimal("0.9"),
        created_at=datetime.now(timezone.utc),
    )


def test_verified_fill_builds_reduce_only_hedge():
    verification = {
        "verified": True,
        "exchange_order_id": "order-1",
        "status": "filled",
        "filled_quote_size": "5",
        "hedge_capability": {
            "supported": True,
            "mode": "reduce_only_market",
            "product_id": "BTC-USD",
            "hedge_side": "SELL",
            "reduce_only": True,
            "maximum_quote_size": "5",
        },
    }

    plan = build_hedge_plan(
        candidate(),
        "order-1",
        verification,
        policy(),
    )

    assert plan.side == "SELL"
    assert plan.quote_size == Decimal("2.5")
    assert plan.reduce_only is True


def test_unverified_fill_cannot_create_hedge():
    with pytest.raises(ValueError, match="not independently verified"):
        build_hedge_plan(
            candidate(),
            "order-1",
            {"verified": False},
            policy(),
        )


def test_same_side_is_rejected():
    verification = {
        "verified": True,
        "exchange_order_id": "order-1",
        "status": "filled",
        "filled_quote_size": "5",
        "hedge_capability": {
            "supported": True,
            "mode": "reduce_only_market",
            "product_id": "BTC-USD",
            "hedge_side": "BUY",
            "reduce_only": True,
        },
    }

    with pytest.raises(ValueError, match="cannot equal"):
        build_hedge_plan(
            candidate(),
            "order-1",
            verification,
            policy(),
        )
