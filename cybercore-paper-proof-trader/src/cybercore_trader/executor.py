from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ExecutorError(RuntimeError):
    pass


def _decode_json_response(response: Any) -> dict[str, Any]:
    body = response.read().decode("utf-8")
    result = json.loads(body)

    if not isinstance(result, dict):
        raise ExecutorError("executor response must be a JSON object")

    return result


def submit_to_existing_executor(
    url: str,
    payload: dict[str, Any],
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "cybercore-paper-proof-controller/0.2",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            return _decode_json_response(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ExecutorError(
            f"executor HTTP {exc.code}: {body[:500]}"
        ) from exc
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        raise ExecutorError(
            f"executor unavailable or returned invalid JSON: {exc}"
        ) from exc


def verify_existing_order(
    url_template: str,
    order_id: str,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    if "{order_id}" not in url_template:
        raise ExecutorError(
            "COINBASE_ORDER_STATUS_URL_TEMPLATE must contain {order_id}"
        )

    encoded_order_id = urllib.parse.quote(
        str(order_id),
        safe="",
    )
    url = url_template.replace("{order_id}", encoded_order_id)

    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "cybercore-paper-proof-controller/0.2",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            return _decode_json_response(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ExecutorError(
            f"order verifier HTTP {exc.code}: {body[:500]}"
        ) from exc
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        raise ExecutorError(
            f"order verifier unavailable or returned invalid JSON: {exc}"
        ) from exc
