from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import RiskPolicy


def _approval_key() -> bytes:
    value = os.getenv("MORNING_APPROVAL_SIGNING_KEY", "")
    if len(value) < 32:
        raise RuntimeError(
            "MORNING_APPROVAL_SIGNING_KEY must be set to at least 32 characters"
        )
    return value.encode("utf-8")


def write_approval(
    path: Path,
    timezone: ZoneInfo,
    proof_digest: str,
    approver: str,
) -> dict:
    now = datetime.now(timezone)
    payload = {
        "approved_date": now.date().isoformat(),
        "approved_at": now.isoformat(),
        "approver": approver,
        "proof_digest": proof_digest,
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload["signature"] = hmac.new(_approval_key(), canonical, hashlib.sha256).hexdigest()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def validate_approval(
    path: Path,
    timezone: ZoneInfo,
    policy: RiskPolicy,
    proof_digest: str,
) -> tuple[bool, str]:
    if not path.exists():
        return False, "morning brief not approved"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "approval file invalid"

    signature = str(payload.pop("signature", ""))
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    expected = hmac.new(_approval_key(), canonical, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return False, "approval signature invalid"

    now = datetime.now(timezone)
    if payload.get("approved_date") != now.date().isoformat():
        return False, "approval expired"

    expires = now.replace(
        hour=policy.approval_expires_local_hour,
        minute=policy.approval_expires_local_minute,
        second=59,
        microsecond=999999,
    )
    if now > expires:
        return False, "approval expired"

    if payload.get("proof_digest") != proof_digest:
        return False, "paper proof changed after approval"

    return True, "approved"
