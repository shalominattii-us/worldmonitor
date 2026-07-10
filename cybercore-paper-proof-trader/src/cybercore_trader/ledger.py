from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import CandidateOrder, PaperTrade


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        handle.write("\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return rows


def load_paper_trades(path: Path) -> list[PaperTrade]:
    return [PaperTrade.from_json(row) for row in read_jsonl(path)]


def load_candidates(path: Path) -> list[CandidateOrder]:
    return [CandidateOrder.from_json(row) for row in read_jsonl(path)]


def rewrite_candidates(path: Path, candidates: Iterable[CandidateOrder]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate.to_json(), separators=(",", ":"), sort_keys=True))
            handle.write("\n")
