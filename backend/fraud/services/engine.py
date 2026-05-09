from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from django.db import transaction

from requests_app.models import AidRequest, RequestStatus
from fraud.models import FraudAction, FraudCheck, FraudDecision, FraudRiskLevel
from fraud.services.rules import Signal, collect_signals


logger = logging.getLogger(__name__)


def _risk_level_from_score(score: int) -> str:
    if score >= 75:
        return FraudRiskLevel.CRITICAL
    if score >= 50:
        return FraudRiskLevel.HIGH
    if score >= 25:
        return FraudRiskLevel.MEDIUM
    return FraudRiskLevel.LOW


def _action_from_level(level: str) -> str:
    if level == FraudRiskLevel.CRITICAL:
        return FraudAction.BLOCK
    if level in (FraudRiskLevel.HIGH, FraudRiskLevel.MEDIUM):
        return FraudAction.MANUAL_REVIEW
    return FraudAction.ALLOW


@transaction.atomic
def evaluate_request(aid_request: AidRequest, engine_version: str = "rules-v3") -> FraudDecision:
    """
    Основной вход антифрода.
    - собирает сигналы
    - пишет FraudCheck (текущий слепок)
    - пишет/обновляет FraudDecision
    - синхронизирует поля риска в AidRequest
    """
    signals: list[Signal] = collect_signals(aid_request)
    score = max(0, min(100, sum(s.weight for s in signals)))
    reasons = [
        {"code": s.code, "weight": s.weight, "details": s.details}
        for s in signals
    ]
    risk_level = _risk_level_from_score(score)
    base_action = _action_from_level(risk_level)

    # Чтобы не копить дубль-сигналы на каждый recheck, чистим предыдущий слепок
    FraudCheck.objects.filter(aid_request=aid_request).delete()

    checks_to_create = [
        FraudCheck(
            aid_request=aid_request,
            signal_code=s.code,
            weight=s.weight,
            value=s.details,
        )
        for s in signals
    ]
    if checks_to_create:
        FraudCheck.objects.bulk_create(checks_to_create)

    decision, created = FraudDecision.objects.get_or_create(
        aid_request=aid_request,
        defaults={
            "score": score,
            "risk_level": risk_level,
            "action": base_action,
            "base_action": base_action,
            "is_overridden": False,
            "reasons": reasons,
            "engine_version": engine_version,
        },
    )

    if not created:
        decision.score = score
        decision.risk_level = risk_level
        decision.base_action = base_action
        decision.reasons = reasons
        decision.engine_version = engine_version
        if not decision.is_overridden:
            decision.action = base_action
        decision.save(
            update_fields=[
                "score",
                "risk_level",
                "base_action",
                "action",
                "reasons",
                "engine_version",
                "decided_at",
            ]
            if not decision.is_overridden
            else [
                "score",
                "risk_level",
                "base_action",
                "reasons",
                "engine_version",
                "decided_at",
            ]
        )

    # Синхронизация denormalized полей в заявке
    aid_request.risk_score = score
    aid_request.is_flagged = risk_level in (FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL)

    # Policy v1:
    # high/critical => только ручная модерация (on_moderation)
    # Здесь ничего не "публикуем" автоматически.
    if aid_request.status != RequestStatus.ON_MODERATION:
        aid_request.status = RequestStatus.ON_MODERATION

    aid_request.save(update_fields=["risk_score", "is_flagged", "status"])

    return decision


def evaluate_request_safe(aid_request: AidRequest, engine_version: str = "rules-v3") -> FraudDecision | None:
    """
    Безопасная обёртка:
    если антифрод падает, не роняем основной create-flow.
    В fail-safe режиме помечаем заявку и оставляем on_moderation.
    """
    try:
        return evaluate_request(aid_request=aid_request, engine_version=engine_version)
    except Exception:
        logger.exception("Fraud evaluation failed for request_id=%s", aid_request.id)

        # Fail-safe режим: ручная модерация + flagged
        aid_request.is_flagged = True
        aid_request.risk_score = max(aid_request.risk_score or 0, 50)
        aid_request.status = RequestStatus.ON_MODERATION
        aid_request.save(update_fields=["is_flagged", "risk_score", "status"])
        return None
