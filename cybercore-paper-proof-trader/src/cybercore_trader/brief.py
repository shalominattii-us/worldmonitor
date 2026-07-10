from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import ProofResult


def proof_digest(proof: ProofResult) -> str:
    payload = {
        "passed": proof.passed,
        "score": str(proof.score),
        "reasons": list(proof.reasons),
        "metrics": {key: str(value) for key, value in proof.metrics.items()},
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_brief(
    proof: ProofResult,
    timezone: ZoneInfo,
    live_trading_enabled: bool,
) -> str:
    now = datetime.now(timezone)
    status = "QUALIFIED" if proof.passed else "PAPER ONLY"
    lines = [
        f"# Cybercore Morning Trade Brief — {now.date().isoformat()}",
        "",
        f"- Control timezone: `{timezone.key}`",
        f"- Paper proof status: **{status}**",
        f"- Paper proof score: **{proof.score:.3f}**",
        f"- Deployment live switch: **{'ON' if live_trading_enabled else 'OFF'}**",
        f"- Proof digest: `{proof_digest(proof)}`",
        "",
        "## Paper proof metrics",
        "",
    ]
    for key, value in proof.metrics.items():
        if isinstance(value, Decimal):
            lines.append(f"- {key}: `{value:.4f}`")
        else:
            lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Qualification findings", ""])
    if proof.reasons:
        for reason in proof.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- Paper proof policy passed.")

    lines.extend([
        "",
        "## Daily control",
        "",
        "Approving this brief authorizes the controller for this Denver calendar day only.",
        "If the paper proof digest changes or qualification fails, live routing stops automatically.",
        "Exchange keys remain inside the existing Coinbase executor.",
        "",
    ])
    return "\n".join(lines)


def write_brief(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
