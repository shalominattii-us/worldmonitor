from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .approval import write_approval
from .brief import proof_digest, render_brief, write_brief
from .config import RiskPolicy, Settings
from .controller import process_once
from .ledger import append_jsonl, load_paper_trades
from .models import PaperTrade
from .qualifier import evaluate_paper_proof


def _settings_and_policy():
    settings = Settings.from_env()
    policy = RiskPolicy.load(settings.policy_path)
    return settings, policy


def _balance_provider() -> Decimal:
    # Use an existing balance feed or inject it at deployment time.
    raw = os.getenv("COINBASE_TRADING_BALANCE_USD", "")
    if not raw:
        raise RuntimeError(
            "COINBASE_TRADING_BALANCE_USD is required unless a real balance provider is wired"
        )
    balance = Decimal(raw)
    if balance <= 0:
        raise RuntimeError("Coinbase trading balance must be positive")
    return balance


def cmd_init_data() -> None:
    settings, _ = _settings_and_policy()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    for name in ("paper_trades.jsonl", "candidates.jsonl"):
        path = settings.data_dir / name
        path.touch(exist_ok=True)

    print(json.dumps({
        "ok": True,
        "data_dir": str(settings.data_dir.resolve()),
        "log_dir": str(settings.log_dir.resolve()),
    }, indent=2))


def cmd_brief() -> None:
    settings, policy = _settings_and_policy()
    trades = load_paper_trades(settings.data_dir / "paper_trades.jsonl")
    proof = evaluate_paper_proof(trades, policy)
    content = render_brief(proof, settings.timezone, settings.live_trading_enabled)
    path = settings.data_dir / "morning_brief.md"
    write_brief(path, content)
    print(content)
    print(f"\nBrief written to {path}")


def cmd_approve_brief(approver: str) -> None:
    settings, policy = _settings_and_policy()
    trades = load_paper_trades(settings.data_dir / "paper_trades.jsonl")
    proof = evaluate_paper_proof(trades, policy)

    if not proof.passed:
        raise RuntimeError(
            "Morning brief cannot unlock live routing because paper proof did not pass"
        )

    digest = proof_digest(proof)
    payload = write_approval(
        settings.data_dir / "morning_approval.json",
        settings.timezone,
        digest,
        approver,
    )
    print(json.dumps(payload, indent=2))


def cmd_run_once() -> None:
    settings, policy = _settings_and_policy()
    result = process_once(settings, policy, _balance_provider)
    print(json.dumps(result, indent=2))


def cmd_run_loop() -> None:
    settings, policy = _settings_and_policy()
    while True:
        try:
            result = process_once(settings, policy, _balance_provider)
            print(json.dumps(result, separators=(",", ":"), sort_keys=True), flush=True)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), flush=True)
        time.sleep(settings.interval_seconds)


def cmd_seed_demo() -> None:
    settings, _ = _settings_and_policy()
    now = datetime.now(settings.timezone)
    path = settings.data_dir / "paper_trades.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    for index in range(36):
        won = index % 3 != 0
        trade = PaperTrade(
            trade_id=f"demo-{index}",
            strategy_id="moltbook-aggregate",
            product_id="BTC-USD",
            side="BUY" if index % 2 == 0 else "SELL",
            opened_at=now - timedelta(days=4, minutes=index * 30 + 5),
            closed_at=now - timedelta(days=4, minutes=index * 30),
            quote_size=Decimal("5"),
            pnl_quote=Decimal("0.08") if won else Decimal("-0.07"),
            fees_quote=Decimal("0.01"),
            slippage_bps=Decimal("4"),
        )
        append_jsonl(path, trade.to_json())

    print(f"Seeded demo paper trades at {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cybercore paper-proof trade controller")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-data")
    sub.add_parser("brief")

    approve = sub.add_parser("approve-brief")
    approve.add_argument("--approver", default="iphone-morning-review")

    sub.add_parser("run-once")
    sub.add_parser("run-loop")
    sub.add_parser("seed-demo")

    args = parser.parse_args()

    commands = {
        "init-data": cmd_init_data,
        "brief": cmd_brief,
        "approve-brief": lambda: cmd_approve_brief(args.approver),
        "run-once": cmd_run_once,
        "run-loop": cmd_run_loop,
        "seed-demo": cmd_seed_demo,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
