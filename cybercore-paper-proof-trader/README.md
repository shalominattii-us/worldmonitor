# Cybercore Paper-Proof Trade Controller

A GitHub-ready controller that treats paper trading as the proof layer for live execution.

## Control model

1. Candidate strategies run continuously in paper mode.
2. The controller scores recent paper results.
3. A live session is eligible only when the paper proof policy passes.
4. The morning brief is the daily human control point.
5. Approval expires automatically at the end of the Denver business day.
6. If proof quality degrades, the controller falls back to paper immediately.
7. Exchange credentials stay inside the existing Coinbase executor. They are never stored here.

## What this package does

- Reads paper fills from a JSONL ledger.
- Calculates win rate, expectancy, profit factor, drawdown, and slippage.
- Produces a Markdown morning brief.
- Records a daily approval without storing credentials.
- Accepts candidate orders through a local queue.
- Routes approved live candidates to an existing internal Coinbase executor.
- Writes a complete decision and execution audit log.
- Supports continuous operation while preserving automatic paper fallback.

## Quick start

```powershell
cd cybercore-paper-proof-trader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[test]

Copy-Item .env.example .env
python -m cybercore_trader.cli init-data
python -m cybercore_trader.cli brief
python -m cybercore_trader.cli approve-brief
python -m cybercore_trader.cli run-once
```

For continuous operation:

```powershell
python -m cybercore_trader.cli run-loop
```

## Existing Coinbase executor contract

Set `COINBASE_EXECUTOR_URL` to an internal service that already owns the Coinbase keys.

The controller sends:

```json
{
  "client_order_id": "uuid",
  "product_id": "BTC-USD",
  "side": "BUY",
  "quote_size": "5.00",
  "source": "moltbook-paper-proof",
  "paper_proof_score": 0.82,
  "morning_approval_date": "2026-07-10"
}
```

Expected response:

```json
{
  "accepted": true,
  "exchange_order_id": "exchange-id",
  "status": "submitted"
}
```

## Required environment variables

See `.env.example`.

No exchange API key, secret, private key, seed, or signing material belongs in this repository.


## Verified autohedge

Every accepted primary order is independently queried through
`COINBASE_ORDER_STATUS_URL_TEMPLATE`. The verifier must return an actual fill and
an explicit hedge capability. The controller does not infer shorting support,
inventory, hedge side, or instrument.

Required primary-order verification fields:

```json
{
  "verified": true,
  "exchange_order_id": "primary-order-id",
  "status": "filled",
  "filled_quote_size": "5.00",
  "hedge_capability": {
    "supported": true,
    "mode": "reduce_only_market",
    "product_id": "BTC-USD",
    "hedge_side": "SELL",
    "reduce_only": true,
    "maximum_quote_size": "5.00"
  }
}
```

The resulting child request includes:

```json
{
  "order_role": "protective_hedge",
  "parent_exchange_order_id": "primary-order-id",
  "hedge_mode": "reduce_only_market",
  "reduce_only": true
}
```

If the primary fill, hedge capability, hedge order, or hedge verification cannot
be confirmed, the controller writes `data/hedge_lock.json`. Further live routing
falls back to paper for the remainder of that Denver calendar day.
