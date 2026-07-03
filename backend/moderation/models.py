from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils import timezone


class VerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class ApplicantVerification(models.Model):
    profile = models.ForeignKey(
        "users.ApplicantProfile",
        on_delete=models.CASCADE,
        related_name="verification_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applicant_verifications_reviewed",
    )
    review_comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("profile",),
                condition=Q(status=VerificationStatus.PENDING),
                name="unique_pending_verification_per_profile",
            )
        ]

    def __str__(self):
        return f"Verification(id={self.id}, profile_id={self.profile_id}, status={self.status})"
