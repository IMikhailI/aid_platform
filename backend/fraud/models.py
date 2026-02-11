from django.conf import settings
from django.db import models


class FraudRiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class FraudAction(models.TextChoices):
    ALLOW = "allow", "Allow"
    MANUAL_REVIEW = "manual_review", "Manual review"
    BLOCK = "block", "Block"


class FraudCheck(models.Model):
    """
    Отдельный сработавший сигнал антифрода по конкретной заявке.
    Пример: BURST_CREATION, DUPLICATE_TEXT и т.д.
    """
    aid_request = models.ForeignKey(
        "requests_app.AidRequest",
        on_delete=models.CASCADE,
        related_name="fraud_checks",
    )
    signal_code = models.CharField(max_length=64)
    weight = models.IntegerField(default=0)
    value = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["aid_request", "signal_code"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"request={self.aid_request_id} signal={self.signal_code} weight={self.weight}"


class FraudDecision(models.Model):
    """
    Итоговое решение антифрода по заявке.
    Один request -> одно актуальное решение.
    """
    aid_request = models.OneToOneField(
        "requests_app.AidRequest",
        on_delete=models.CASCADE,
        related_name="fraud_decision",
    )
    score = models.IntegerField(default=0)
    risk_level = models.CharField(
        max_length=16,
        choices=FraudRiskLevel.choices,
        default=FraudRiskLevel.LOW,
    )
    action = models.CharField(
        max_length=20,
        choices=FraudAction.choices,
        default=FraudAction.ALLOW,
    )
    reasons = models.JSONField(default=list, blank=True)
    engine_version = models.CharField(max_length=32, default="rules-v1")
    decided_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["score"]),
            models.Index(fields=["risk_level"]),
            models.Index(fields=["action"]),
            models.Index(fields=["decided_at"]),
        ]

    def __str__(self):
        return f"request={self.aid_request_id} score={self.score} level={self.risk_level} action={self.action}"


class FraudOverride(models.Model):
    """
    Ручное изменение действия (override) модератором/админом.
    Обязательно с комментарием.
    """
    aid_request = models.ForeignKey(
        "requests_app.AidRequest",
        on_delete=models.CASCADE,
        related_name="fraud_overrides",
    )
    old_action = models.CharField(max_length=20, choices=FraudAction.choices)
    new_action = models.CharField(max_length=20, choices=FraudAction.choices)
    comment = models.TextField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fraud_overrides_made",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["aid_request", "created_at"]),
            models.Index(fields=["changed_by"]),
        ]

    def __str__(self):
        return f"request={self.aid_request_id} override={self.old_action}->{self.new_action}"

