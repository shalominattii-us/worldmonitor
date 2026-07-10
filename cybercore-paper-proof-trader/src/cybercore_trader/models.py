from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PaperTrade:
    trade_id: str
    strategy_id: str
    product_id: str
    side: str
    opened_at: datetime
    closed_at: datetime
    quote_size: Decimal
    pnl_quote: Decimal
    fees_quote: Decimal
    slippage_bps: Decimal

    @property
    def net_pnl_quote(self) -> Decimal:
        return self.pnl_quote - self.fees_quote

    @property
    def return_bps(self) -> Decimal:
        if self.quote_size <= 0:
            return Decimal("0")
        return (self.net_pnl_quote / self.quote_size) * Decimal("10000")

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        for field in ("opened_at", "closed_at"):
            data[field] = data[field].isoformat()
        for field in ("quote_size", "pnl_quote", "fees_quote", "slippage_bps"):
            data[field] = str(data[field])
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "PaperTrade":
        return cls(
            trade_id=str(data["trade_id"]),
            strategy_id=str(data["strategy_id"]),
            product_id=str(data["product_id"]),
            side=str(data["side"]).upper(),
            opened_at=datetime.fromisoformat(str(data["opened_at"])),
            closed_at=datetime.fromisoformat(str(data["closed_at"])),
            quote_size=Decimal(str(data["quote_size"])),
            pnl_quote=Decimal(str(data["pnl_quote"])),
            fees_quote=Decimal(str(data.get("fees_quote", "0"))),
            slippage_bps=Decimal(str(data.get("slippage_bps", "0"))),
        )


@dataclass(frozen=True)
class CandidateOrder:
    candidate_id: str
    strategy_id: str
    product_id: str
    side: str
    quote_size: Decimal
    confidence: Decimal
    created_at: datetime

    def to_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "product_id": self.product_id,
            "side": self.side,
            "quote_size": str(self.quote_size),
            "confidence": str(self.confidence),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CandidateOrder":
        return cls(
            candidate_id=str(data["candidate_id"]),
            strategy_id=str(data["strategy_id"]),
            product_id=str(data["product_id"]),
            side=str(data["side"]).upper(),
            quote_size=Decimal(str(data["quote_size"])),
            confidence=Decimal(str(data.get("confidence", "0"))),
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )


@dataclass(frozen=True)
class ProofResult:
    passed: bool
    score: Decimal
    reasons: tuple[str, ...]
    metrics: dict[str, Decimal | int]
