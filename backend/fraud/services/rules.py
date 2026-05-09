from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


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


def rule_high_requested_amount(aid_request: AidRequest) -> list[Signal]:
    """
    Высокие суммы не блокируем автоматически, но отправляем в review.
    Для платформы адресной помощи это важный финансовый риск-сигнал.
    """
    amount = _to_decimal(aid_request.requested_amount)

    if amount >= Decimal("50000"):
        weight = 45
    elif amount >= Decimal("20000"):
        weight = 30
    elif amount >= Decimal("10000"):
        weight = 15
    else:
        return []

    return [
        Signal(
            code="HIGH_REQUESTED_AMOUNT",
            weight=weight,
            details={
                "requested_amount": str(amount),
                "thresholds": {"10000+": 15, "20000+": 30, "50000+": 45},
            },
        )
    ]


def rule_extreme_urgency(aid_request: AidRequest) -> list[Signal]:
    """
    Срочность сама по себе не должна сильно штрафовать,
    но в связке с другими сигналами помогает быстрее вывести кейс в review.
    """
    urgency = aid_request.urgency or 0

    if urgency >= 5:
        return [
            Signal(
                code="EXTREME_URGENCY",
                weight=10,
                details={"urgency": urgency},
            )
        ]
    return []


def rule_amount_urgency_combo(aid_request: AidRequest) -> list[Signal]:
    """
    Комбинация "высокая сумма + максимальная срочность" —
    типичный кандидат на ручную проверку.
    """
    amount = _to_decimal(aid_request.requested_amount)
    urgency = aid_request.urgency or 0

    if amount >= Decimal("20000") and urgency >= 5:
        return [
            Signal(
                code="AMOUNT_URGENCY_COMBO",
                weight=15,
                details={
                    "requested_amount": str(amount),
                    "urgency": urgency,
                },
            )
        ]
    return []


def rule_device_shared_across_accounts(aid_request: AidRequest) -> list[Signal]:
    """
    Один и тот же device_id у нескольких аккаунтов — не приговор,
    но сильный сигнал к ручной проверке.
    """
    if not aid_request.device_id_hash:
        return []

    applicant_ids = list(
        AidRequest.objects.filter(device_id_hash=aid_request.device_id_hash)
        .order_by()
        .values_list("applicant_id", flat=True)
        .distinct()
    )
    accounts_count = len(applicant_ids)

    if accounts_count >= 3:
        weight = 30
    elif accounts_count >= 2:
        weight = 15
    else:
        return []

    return [
        Signal(
            code="DEVICE_SHARED_ACROSS_ACCOUNTS",
            weight=weight,
            details={
                "accounts_count": accounts_count,
                "applicant_ids": applicant_ids[:10],
            },
        )
    ]


def rule_same_device_exact_duplicate_cross_account(aid_request: AidRequest) -> list[Signal]:
    """
    Точный дубль текста с того же device_id, но от другого аккаунта —
    один из самых полезных мультиаккаунтных сигналов.
    """
    if not aid_request.device_id_hash:
        return []

    title_norm = _norm_text(aid_request.title)
    desc_norm = _norm_text(aid_request.description)
    if not title_norm and not desc_norm:
        return []

    candidates = AidRequest.objects.filter(
        device_id_hash=aid_request.device_id_hash,
    ).exclude(
        id=aid_request.id,
    ).exclude(
        applicant=aid_request.applicant,
    ).only("id", "title", "description", "applicant_id")[:200]

    matched = []
    for candidate in candidates:
        if _norm_text(candidate.title) == title_norm and _norm_text(candidate.description) == desc_norm:
            matched.append({"id": candidate.id, "applicant_id": candidate.applicant_id})

    if not matched:
        return []

    return [
        Signal(
            code="SAME_DEVICE_EXACT_DUPLICATE_CROSS_ACCOUNT",
            weight=35,
            details={
                "matches_count": len(matched),
                "matched_requests": matched[:20],
            },
        )
    ]


def rule_device_linked_to_rejected_other_account(aid_request: AidRequest) -> list[Signal]:
    """
    Если device уже участвовал в отклоненных кейсах другого аккаунта,
    это повышает риск, но не должно автоматически блокировать.
    """
    if not aid_request.device_id_hash:
        return []

    rejected_qs = AidRequest.objects.filter(
        device_id_hash=aid_request.device_id_hash,
        status=RequestStatus.REJECTED,
    ).exclude(applicant=aid_request.applicant)

    rejected_count = rejected_qs.count()
    if rejected_count == 0:
        return []

    weight = 20 if rejected_count >= 2 else 10
    return [
        Signal(
            code="DEVICE_LINKED_TO_REJECTED_OTHER_ACCOUNT",
            weight=weight,
            details={
                "rejected_count": rejected_count,
                "request_ids": list(rejected_qs.values_list("id", flat=True)[:20]),
            },
        )
    ]


def rule_ip_shared_across_accounts_recent(aid_request: AidRequest) -> list[Signal]:
    """
    Общий IP между аккаунтами — очень шумный сигнал, поэтому:
    - смотрим только короткое окно
    - даём мягкий вес
    - используем как контекст, а не как повод для block
    """
    if not aid_request.ip_hash:
        return []

    window_hours = 24
    since = timezone.now() - timedelta(hours=window_hours)
    applicant_ids = list(
        AidRequest.objects.filter(
            ip_hash=aid_request.ip_hash,
            created_at__gte=since,
        )
        .order_by()
        .values_list("applicant_id", flat=True)
        .distinct()
    )
    accounts_count = len(applicant_ids)

    if accounts_count >= 5:
        weight = 6
    elif accounts_count >= 2:
        weight = 3
    else:
        return []

    return [
        Signal(
            code="IP_SHARED_ACROSS_ACCOUNTS",
            weight=weight,
            details={
                "accounts_count": accounts_count,
                "applicant_ids": applicant_ids[:10],
                "window_hours": window_hours,
            },
        )
    ]


def rule_same_ip_exact_duplicate_cross_account_recent(aid_request: AidRequest) -> list[Signal]:
    """
    Один и тот же IP + точный дубль текста + другой аккаунт в коротком окне.
    Более полезный сигнал, чем просто shared IP, но всё ещё только manual review.
    """
    if not aid_request.ip_hash:
        return []

    title_norm = _norm_text(aid_request.title)
    desc_norm = _norm_text(aid_request.description)
    if not title_norm and not desc_norm:
        return []

    window_hours = 24
    since = timezone.now() - timedelta(hours=window_hours)
    candidates = AidRequest.objects.filter(
        ip_hash=aid_request.ip_hash,
        created_at__gte=since,
    ).exclude(
        id=aid_request.id,
    ).exclude(
        applicant=aid_request.applicant,
    ).only("id", "title", "description", "applicant_id")[:200]

    matched = []
    for candidate in candidates:
        if _norm_text(candidate.title) == title_norm and _norm_text(candidate.description) == desc_norm:
            matched.append({"id": candidate.id, "applicant_id": candidate.applicant_id})

    if not matched:
        return []

    return [
        Signal(
            code="SAME_IP_EXACT_DUPLICATE_CROSS_ACCOUNT",
            weight=22,
            details={
                "matches_count": len(matched),
                "matched_requests": matched[:20],
                "window_hours": window_hours,
            },
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
    signals.extend(rule_high_requested_amount(aid_request))
    signals.extend(rule_extreme_urgency(aid_request))
    signals.extend(rule_amount_urgency_combo(aid_request))
    signals.extend(rule_device_shared_across_accounts(aid_request))
    signals.extend(rule_same_device_exact_duplicate_cross_account(aid_request))
    signals.extend(rule_device_linked_to_rejected_other_account(aid_request))
    signals.extend(rule_ip_shared_across_accounts_recent(aid_request))
    signals.extend(rule_same_ip_exact_duplicate_cross_account_recent(aid_request))

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
