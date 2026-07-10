from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class RiskPolicy:
    paper_window_trades: int
    minimum_paper_trades: int
    minimum_distinct_days: int
    minimum_win_rate: Decimal
    minimum_expectancy_bps: Decimal
    minimum_profit_factor: Decimal
    maximum_drawdown_pct: Decimal
    maximum_average_slippage_bps: Decimal
    minimum_proof_score: Decimal
    maximum_live_order_quote_usd: Decimal
    maximum_live_daily_notional_pct_of_balance: Decimal
    maximum_live_daily_loss_pct_of_balance: Decimal
    maximum_live_trades_per_day: int
    minimum_quote_size_usd: Decimal
    approval_expires_local_hour: int
    approval_expires_local_minute: int
    hedge_required: bool
    hedge_ratio: Decimal
    minimum_hedge_quote_usd: Decimal
    maximum_hedge_quote_usd: Decimal
    maximum_hedges_per_day: int
    allowed_hedge_modes: tuple[str, ...]
    allowed_hedge_products: tuple[str, ...]
    protective_stop_distance_bps: Decimal

    @classmethod
    def load(cls, path: Path) -> "RiskPolicy":
        raw = json.loads(path.read_text(encoding="utf-8"))

        # Backward-compatible defaults for an older policy file.
        raw.setdefault("hedge_required", True)
        raw.setdefault("hedge_ratio", 0.50)
        raw.setdefault("minimum_hedge_quote_usd", 1.00)
        raw.setdefault("maximum_hedge_quote_usd", 10.00)
        raw.setdefault("maximum_hedges_per_day", 8)
        raw.setdefault(
            "allowed_hedge_modes",
            ["reduce_only_market", "protective_stop"],
        )
        raw.setdefault(
            "allowed_hedge_products",
            ["BTC-USD", "ETH-USD", "SOL-USD"],
        )
        raw.setdefault("protective_stop_distance_bps", 125.0)

        decimal_fields = {
            "minimum_win_rate",
            "minimum_expectancy_bps",
            "minimum_profit_factor",
            "maximum_drawdown_pct",
            "maximum_average_slippage_bps",
            "minimum_proof_score",
            "maximum_live_order_quote_usd",
            "maximum_live_daily_notional_pct_of_balance",
            "maximum_live_daily_loss_pct_of_balance",
            "minimum_quote_size_usd",
            "hedge_ratio",
            "minimum_hedge_quote_usd",
            "maximum_hedge_quote_usd",
            "protective_stop_distance_bps",
        }
        for field in decimal_fields:
            raw[field] = Decimal(str(raw[field]))

        raw["allowed_hedge_modes"] = tuple(
            str(value) for value in raw["allowed_hedge_modes"]
        )
        raw["allowed_hedge_products"] = tuple(
            str(value).upper() for value in raw["allowed_hedge_products"]
        )

        return cls(**raw)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    log_dir: Path
    policy_path: Path
    timezone: ZoneInfo
    live_trading_enabled: bool
    coinbase_executor_url: str
    interval_seconds: int
    autohedge_enabled: bool = False
    coinbase_order_status_url_template: str = (
        "http://127.0.0.1:8088/v1/orders/{order_id}"
    )
    hedge_verification_timeout_seconds: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("CYBERCORE_DATA_DIR", "./data")),
            log_dir=Path(os.getenv("CYBERCORE_LOG_DIR", "./logs")),
            policy_path=Path(
                os.getenv(
                    "CYBERCORE_POLICY_PATH",
                    "./config/risk-policy.json",
                )
            ),
            timezone=ZoneInfo(
                os.getenv("CYBERCORE_TIMEZONE", "America/Denver")
            ),
            live_trading_enabled=(
                os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
            ),
            coinbase_executor_url=os.getenv(
                "COINBASE_EXECUTOR_URL",
                "http://127.0.0.1:8088/v1/orders",
            ),
            interval_seconds=int(
                os.getenv("CONTROLLER_INTERVAL_SECONDS", "20")
            ),
            autohedge_enabled=(
                os.getenv("AUTOHEDGE_ENABLED", "false").lower() == "true"
            ),
            coinbase_order_status_url_template=os.getenv(
                "COINBASE_ORDER_STATUS_URL_TEMPLATE",
                "http://127.0.0.1:8088/v1/orders/{order_id}",
            ),
            hedge_verification_timeout_seconds=int(
                os.getenv("HEDGE_VERIFICATION_TIMEOUT_SECONDS", "15")
            ),
        )
