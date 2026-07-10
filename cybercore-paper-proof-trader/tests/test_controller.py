from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from cybercore_trader.config import RiskPolicy, Settings
from cybercore_trader.controller import DailyLiveState, decision_for_candidate
from cybercore_trader.models import CandidateOrder, ProofResult


def settings(live: bool) -> Settings:
    return Settings(
        data_dir=Path("data"),
        log_dir=Path("logs"),
        policy_path=Path("config/risk-policy.json"),
        timezone=ZoneInfo("America/Denver"),
        live_trading_enabled=live,
        coinbase_executor_url="http://127.0.0.1:8088/v1/orders",
        interval_seconds=20,
        autohedge_enabled=True,
    )


def test_live_requires_switch_proof_and_approval():
    policy = RiskPolicy.load(Path("config/risk-policy.json"))
    candidate = CandidateOrder(
        candidate_id="one",
        strategy_id="aggregate",
        product_id="BTC-USD",
        side="BUY",
        quote_size=Decimal("5"),
        confidence=Decimal("0.9"),
        created_at=datetime.now(timezone.utc),
    )
    proof = ProofResult(
        passed=True,
        score=Decimal("0.9"),
        reasons=(),
        metrics={},
    )
    daily = DailyLiveState(
        balance_usd=Decimal("98"),
        live_notional_usd=Decimal("0"),
        live_realized_pnl_usd=Decimal("0"),
        live_trade_count=0,
    )

    mode, reasons = decision_for_candidate(
        candidate,
        proof,
        True,
        settings(True),
        policy,
        daily,
    )
    assert mode == "live"
    assert reasons == []

    mode, reasons = decision_for_candidate(
        candidate,
        proof,
        False,
        settings(True),
        policy,
        daily,
    )
    assert mode == "paper"
    assert reasons



def test_required_autohedge_must_be_enabled():
    policy = RiskPolicy.load(Path("config/risk-policy.json"))
    candidate = CandidateOrder(
        candidate_id="two",
        strategy_id="aggregate",
        product_id="BTC-USD",
        side="BUY",
        quote_size=Decimal("5"),
        confidence=Decimal("0.9"),
        created_at=datetime.now(timezone.utc),
    )
    proof = ProofResult(
        passed=True,
        score=Decimal("0.9"),
        reasons=(),
        metrics={},
    )
    daily = DailyLiveState(
        balance_usd=Decimal("98"),
        live_notional_usd=Decimal("0"),
        live_realized_pnl_usd=Decimal("0"),
        live_trade_count=0,
    )

    from dataclasses import replace
    disabled = replace(settings(True), autohedge_enabled=False)
    mode, reasons = decision_for_candidate(
        candidate,
        proof,
        True,
        disabled,
        policy,
        daily,
    )
    assert mode == "paper"
    assert "required autohedge is disabled" in reasons
