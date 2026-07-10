from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOGS = ROOT / "logs"

INBOX = DATA / "paper_fill_inbox.jsonl"
LEDGER = DATA / "paper_trades.jsonl"
CHECKPOINT = DATA / "paper_fill_inbox.offset"
WORKER_LOG = LOGS / "paper_qualification_worker.log"

INTERVAL_SECONDS = max(
    1,
    int(os.getenv("PAPER_WORKER_INTERVAL_SECONDS", "5")),
)

DATA.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)
INBOX.touch(exist_ok=True)
LEDGER.touch(exist_ok=True)


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"{timestamp} {message}"

    print(line, flush=True)

    with WORKER_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def parse_datetime(value: Any, field: str) -> str:
    text = str(value or "").strip()

    if not text:
        raise ValueError(f"{field} is required")

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            f"{field} must be an ISO-8601 timestamp"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.isoformat()


def parse_decimal(
    value: Any,
    field: str,
    *,
    minimum: Decimal | None = None,
) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc

    if minimum is not None and parsed < minimum:
        raise ValueError(
            f"{field} must be greater than or equal to {minimum}"
        )

    return parsed


def normalize_trade(raw: dict[str, Any]) -> dict[str, str]:
    trade_id = str(raw.get("trade_id") or "").strip()
    strategy_id = str(raw.get("strategy_id") or "").strip()
    product_id = str(raw.get("product_id") or "").strip().upper()
    side = str(raw.get("side") or "").strip().upper()

    if not trade_id:
        raise ValueError("trade_id is required")

    if not strategy_id:
        raise ValueError("strategy_id is required")

    if not product_id:
        raise ValueError("product_id is required")

    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    opened_at = parse_datetime(raw.get("opened_at"), "opened_at")
    closed_at = parse_datetime(raw.get("closed_at"), "closed_at")

    opened = datetime.fromisoformat(opened_at)
    closed = datetime.fromisoformat(closed_at)

    if closed < opened:
        raise ValueError("closed_at cannot precede opened_at")

    quote_size = parse_decimal(
        raw.get("quote_size"),
        "quote_size",
        minimum=Decimal("0.00000001"),
    )
    pnl_quote = parse_decimal(
        raw.get("pnl_quote"),
        "pnl_quote",
    )
    fees_quote = parse_decimal(
        raw.get("fees_quote", "0"),
        "fees_quote",
        minimum=Decimal("0"),
    )
    slippage_bps = parse_decimal(
        raw.get("slippage_bps", "0"),
        "slippage_bps",
    )

    return {
        "trade_id": trade_id,
        "strategy_id": strategy_id,
        "product_id": product_id,
        "side": side,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "quote_size": str(quote_size),
        "pnl_quote": str(pnl_quote),
        "fees_quote": str(fees_quote),
        "slippage_bps": str(slippage_bps),
    }


def load_existing_ids() -> set[str]:
    identifiers: set[str] = set()

    with LEDGER.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()

            if not text:
                continue

            try:
                record = json.loads(text)
            except json.JSONDecodeError:
                continue

            if isinstance(record, dict) and record.get("trade_id"):
                identifiers.add(str(record["trade_id"]))

    return identifiers


def append_trade(record: dict[str, str]) -> None:
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        )
        handle.flush()
        os.fsync(handle.fileno())


def load_offset() -> int:
    if not CHECKPOINT.exists():
        return 0

    try:
        return max(
            0,
            int(CHECKPOINT.read_text(encoding="utf-8").strip()),
        )
    except (OSError, ValueError):
        return 0


def save_offset(offset: int) -> None:
    temporary = CHECKPOINT.with_suffix(".offset.tmp")
    temporary.write_text(str(offset), encoding="utf-8")
    temporary.replace(CHECKPOINT)


def refresh_brief() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cybercore_trader.cli",
            "brief",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode == 0:
        log("Morning brief refreshed.")
    else:
        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "unknown brief error"
        )
        log(f"Morning brief refresh failed: {error}")


def process_inbox() -> int:
    offset = load_offset()
    inbox_size = INBOX.stat().st_size

    if inbox_size < offset:
        log("Inbox was truncated; resetting checkpoint.")
        offset = 0

    existing_ids = load_existing_ids()
    accepted = 0

    with INBOX.open("rb") as handle:
        handle.seek(offset)

        while True:
            raw_line = handle.readline()

            if not raw_line:
                break

            # Leave an incomplete final line for the next cycle.
            if not raw_line.endswith(b"\n"):
                break

            next_offset = handle.tell()

            try:
                text = raw_line.decode("utf-8").strip()

                if not text:
                    offset = next_offset
                    continue

                raw = json.loads(text)

                if not isinstance(raw, dict):
                    raise ValueError(
                        "paper fill must be a JSON object"
                    )

                trade = normalize_trade(raw)
                trade_id = trade["trade_id"]

                if trade_id in existing_ids:
                    log(
                        f"Duplicate paper fill ignored: "
                        f"{trade_id}"
                    )
                else:
                    append_trade(trade)
                    existing_ids.add(trade_id)
                    accepted += 1

                    log(
                        f"Accepted paper fill {trade_id}: "
                        f"{trade['product_id']} "
                        f"{trade['side']} "
                        f"pnl={trade['pnl_quote']}"
                    )

            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                log(
                    f"Paper fill rejected at inbox byte "
                    f"{offset}: {exc}"
                )

            offset = next_offset
            save_offset(offset)

    return accepted


def main() -> None:
    log(
        "Paper qualification worker started. "
        f"Inbox={INBOX}"
    )

    while True:
        try:
            accepted = process_inbox()

            if accepted:
                log(
                    f"Ingested {accepted} completed paper "
                    f"trade(s)."
                )
                refresh_brief()

        except Exception as exc:
            log(
                f"Worker cycle failed: "
                f"{type(exc).__name__}: {exc}"
            )

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Paper qualification worker stopped.")
