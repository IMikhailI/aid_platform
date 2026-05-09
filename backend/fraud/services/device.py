from __future__ import annotations

import hashlib

from django.conf import settings


def _stable_hash(kind: str, value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    payload = f"{settings.SECRET_KEY}:{kind}:{normalized}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def extract_request_telemetry(request) -> dict[str, str]:
    raw_device_id = request.headers.get("X-Device-Id", "")
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    remote_addr = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    return {
        "device_id_hash": _stable_hash("device_id", raw_device_id),
        "ip_hash": _stable_hash("ip", remote_addr),
        "user_agent_hash": _stable_hash("user_agent", user_agent),
    }
