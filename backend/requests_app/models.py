from django.conf import settings
from django.db import models


class RequestCategory(models.TextChoices):
    FOOD = "food", "Еда"
    CHILDREN = "children", "Детские товары"
    MEDICINE = "medicine", "Лекарства"
    CLOTHES = "clothes", "Одежда"
    OTHER = "other", "Другое"


class RequestStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    ON_MODERATION = "on_moderation", "На модерации"
    PUBLISHED = "published", "Опубликована"
    IN_PROGRESS = "in_progress", "В работе"
    CLOSED = "closed", "Закрыта"
    REJECTED = "rejected", "Отклонена"


class AidRequest(models.Model):
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aid_requests",
    )
    category = models.CharField(max_length=20, choices=RequestCategory.choices)
    title = models.CharField(max_length=180)
    description = models.TextField()
    region = models.CharField(max_length=120)
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    urgency = models.PositiveSmallIntegerField(default=3)  # 1..5
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.ON_MODERATION
    )
    is_flagged = models.BooleanField(default=False)
    risk_score = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.id} {self.title} [{self.status}]"


class RequestStatusHistory(models.Model):
    aid_request = models.ForeignKey(
        AidRequest, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=20, blank=True, default="")
    new_status = models.CharField(max_length=20, choices=RequestStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    comment = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class HelpCommitment(models.Model):
    aid_request = models.OneToOneField(
        AidRequest, on_delete=models.CASCADE, related_name="commitment"
    )
    helper = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commitments"
    )
    method = models.CharField(
        max_length=30,
        choices=[
            ("certificate", "Сертификат"),
            ("cart", "Оплата корзины"),
            ("invoice", "Оплата счёта"),
            ("mock", "Mock-помощь"),
        ],
        default="mock",
    )
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

