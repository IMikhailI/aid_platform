from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.utils import timezone

from requests_app.models import AidRequest, RequestStatus


@dataclass
class Signal:
    code: str
    weight: int
    details: dict[str, Any]


def _norm_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


_digit_re = re.compile(r"\d+")
_punct_re = re.compile(r"[^\w\s]+", flags=re.UNICODE)

def _norm_text_loose(value: str) -> str:
    """
    Нормализация для near-duplicate:
    - lower
    - убрать пунктуацию
    - заменить цифры на '#'
    - схлопнуть пробелы
    """
    s = (value or "").strip().lower()
    s = _punct_re.sub(" ", s)
    s = _digit_re.sub("#", s)
    s = " ".join(s.split())
    return s


def rule_burst_creation(aid_request: AidRequest) -> list[Signal]:
    """
    Эскалация за частые создания.
    """
    window_minutes = 30
    since = timezone.now() - timedelta(minutes=window_minutes)

    cnt = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
    ).count()

    # эскалация по корзинам
    if cnt >= 8:
        weight = 55
    elif cnt >= 5:
        weight = 35
    elif cnt >= 3:
        weight = 20
    else:
        return []

    return [
        Signal(
            code="BURST_CREATION",
            weight=weight,
            details={"count_last_30m": cnt, "buckets": {"3+": 20, "5+": 35, "8+": 55}},
        )
    ]


def rule_duplicate_text(aid_request: AidRequest) -> list[Signal]:
    """
    Дубль-текст с эскалацией по числу дублей.
    Важно: считаем только по этому же автору, чтобы снизить false positives.
    """
    lookback_days = 30

    title_norm = _norm_text(aid_request.title)
    desc_norm = _norm_text(aid_request.description)
    if not title_norm and not desc_norm:
        return []

    since = timezone.now() - timedelta(days=lookback_days)

    # только этот автор
    candidates = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
    ).exclude(id=aid_request.id).only("id", "title", "description")[:500]

    dup_ids = []
    for c in candidates:
        same_title = title_norm and _norm_text(c.title) == title_norm
        same_desc = desc_norm and _norm_text(c.description) == desc_norm
        if same_title or same_desc:
            dup_ids.append(c.id)

    dup_count = len(dup_ids)
    if dup_count == 0:
        return []

    # эскалация
    if dup_count >= 4:
        weight = 60
    elif dup_count >= 2:
        weight = 40
    else:
        weight = 25

    return [
        Signal(
            code="DUPLICATE_TEXT",
            weight=weight,
            details={"duplicates_count": dup_count, "duplicate_ids": dup_ids[:20], "lookback_days": lookback_days},
        )
    ]


def rule_exact_duplicate_same_author_recent(aid_request: AidRequest) -> list[Signal]:
    """
    Жёсткий сигнал: полностью одинаковые title+description (оба) у того же автора
    в коротком окне.
    """
    window_minutes = 60
    since = timezone.now() - timedelta(minutes=window_minutes)

    title_norm = _norm_text(aid_request.title)
    desc_norm = _norm_text(aid_request.description)
    if not title_norm and not desc_norm:
        return []

    candidates = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
    ).exclude(id=aid_request.id).only("id", "title", "description")[:500]

    exact_ids = []
    for c in candidates:
        if _norm_text(c.title) == title_norm and _norm_text(c.description) == desc_norm:
            exact_ids.append(c.id)

    exact_count = len(exact_ids)
    if exact_count == 0:
        return []

    # 2-й дубль => exact_count=1 (уже есть один такой)
    # exact_count = сколько точных дублей уже есть у автора в окне
    # 2-я заявка => exact_count = 1  -> НЕ блокируем
    # 3-я заявка => exact_count = 2  -> блокируем
    if exact_count >= 2:
        weight = 75   # с 3-й и дальше выводит в critical даже без других сигналов
    else:
        weight = 30   # 2-я — только review/high

    return [
        Signal(
            code="EXACT_DUPLICATE_SAME_AUTHOR",
            weight=weight,
            details={
                "exact_duplicates_count": exact_count,
                "exact_duplicate_ids": exact_ids[:20],
                "window_minutes": window_minutes,
            },
        )
    ]


def rule_loose_duplicate_same_author_recent(aid_request: AidRequest) -> list[Signal]:
    """
    Near-duplicate (цифры/пунктуация) для одного автора в коротком окне.
    Ловит обход "заявка 1/2/3", "описание 1/2/3".
    """
    window_minutes = 60
    since = timezone.now() - timedelta(minutes=window_minutes)

    title_loose = _norm_text_loose(aid_request.title)
    desc_loose = _norm_text_loose(aid_request.description)
    if not title_loose and not desc_loose:
        return []

    candidates = AidRequest.objects.filter(
        applicant=aid_request.applicant,
        created_at__gte=since,
    ).exclude(id=aid_request.id).only("id", "title", "description")[:500]

    loose_ids = []
    for c in candidates:
        if _norm_text_loose(c.title) == title_loose and _norm_text_loose(c.description) == desc_loose:
            loose_ids.append(c.id)

    loose_count = len(loose_ids)
    if loose_count == 0:
        return []

    # Эскалация мягче, чем strict exact, но растёт
    if loose_count >= 3:
        weight = 55
    elif loose_count >= 2:
        weight = 40
    else:
        weight = 25

    return [
        Signal(
            code="LOOSE_DUPLICATE_SAME_AUTHOR",
            weight=weight,
            details={
                "loose_duplicates_count": loose_count,
                "loose_duplicate_ids": loose_ids[:20],
                "window_minutes": window_minutes,
            },
        )
    ]


def rule_repeat_rejected_author(aid_request: AidRequest) -> list[Signal]:
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

    # Частота — всегда отдельно
    signals.extend(rule_burst_creation(aid_request))

    # Сначала самые сильные дубли
    exact = rule_exact_duplicate_same_author_recent(aid_request)
    if exact:
        signals.extend(exact)
        # exact покрывает и loose, и duplicate_text — не добавляем их
        signals.extend(rule_repeat_rejected_author(aid_request))
        return signals

    loose = rule_loose_duplicate_same_author_recent(aid_request)
    if loose:
        signals.extend(loose)
        # loose покрывает duplicate_text — не добавляем его
        signals.extend(rule_repeat_rejected_author(aid_request))
        return signals

    # Только если нет exact/loose — используем более общий duplicate_text
    signals.extend(rule_duplicate_text(aid_request))

    signals.extend(rule_repeat_rejected_author(aid_request))
    return signals
