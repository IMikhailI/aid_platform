from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from requests_app.models import AidRequest, RequestStatus


@dataclass
class Signal:
    code: str
    weight: int
    details: dict[str, Any]


def _norm_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def rule_burst_creation(aid_request: AidRequest) -> list[Signal]:
    """
    Если пользователь создал слишком много заявок за короткий период.
    """
    window_minutes = 30
    threshold = 3
    weight = 20

    since = timezone.now() - timedelta(minutes=window_minutes)
    cnt = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
    ).count()

    if cnt >= threshold:
        return [
            Signal(
                code="BURST_CREATION",
                weight=weight,
                details={"count_last_30m": cnt, "threshold": threshold},
            )
        ]
    return []


def rule_duplicate_text(aid_request: AidRequest) -> list[Signal]:
    """
    Упрощённый дубль-текст:
    сравниваем нормализованные title+description с последними заявками.
    """
    weight = 25
    lookback_days = 30

    title_norm = _norm_text(aid_request.title)
    desc_norm = _norm_text(aid_request.description)
    if not title_norm and not desc_norm:
        return []

    since = timezone.now() - timedelta(days=lookback_days)

    candidates = AidRequest.objects.filter(created_at__gte=since).exclude(id=aid_request.id).only(
        "id", "title", "description", "applicant_id"
    )[:500]

    same_title = []
    same_desc = []

    for c in candidates:
        if _norm_text(c.title) == title_norm and title_norm:
            same_title.append(c.id)
        if _norm_text(c.description) == desc_norm and desc_norm:
            same_desc.append(c.id)

    # Сигналим, если есть совпадения по title или description
    if same_title or same_desc:
        return [
            Signal(
                code="DUPLICATE_TEXT",
                weight=weight,
                details={
                    "same_title_ids": same_title[:20],
                    "same_description_ids": same_desc[:20],
                    "lookback_days": lookback_days,
                },
            )
        ]
    return []


def rule_repeat_rejected_author(aid_request: AidRequest) -> list[Signal]:
    """
    Если у автора много отклонённых заявок за период.
    """
    lookback_days = 60
    min_rejected = 2
    weight = 15

    since = timezone.now() - timedelta(days=lookback_days)

    rejected_count = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
        status=RequestStatus.REJECTED,
    ).count()

    if rejected_count >= min_rejected:
        return [
            Signal(
                code="REPEAT_REJECTED_AUTHOR",
                weight=weight,
                details={"rejected_last_60d": rejected_count, "threshold": min_rejected},
            )
        ]
    return []


def collect_signals(aid_request: AidRequest) -> list[Signal]:
    signals: list[Signal] = []
    signals.extend(rule_burst_creation(aid_request))
    signals.extend(rule_duplicate_text(aid_request))
    signals.extend(rule_repeat_rejected_author(aid_request))
    return signals

