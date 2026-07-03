from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class UserRole(models.TextChoices):
    APPLICANT = "applicant", "Applicant"      # Нуждающийся
    HELPER = "helper", "Helper"               # Помогающий
    MODERATOR = "moderator", "Moderator"      # Модератор (НКО)
    ADMIN = "admin", "Admin"                  # Админ


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.APPLICANT,
        db_index=True
    )

    # Минимум полей для профиля можно добавить позже отдельной моделью Profile
    region = models.CharField(max_length=120, blank=True, default="")

    def __str__(self):
        return f"{self.username} ({self.role})"


class ApplicantProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="applicant_profile",
    )
    household_size = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    dependents_count = models.PositiveSmallIntegerField(default=0)
    consent_to_data_processing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        if self.user_id and self.user.role != UserRole.APPLICANT:
            errors["user"] = "ApplicantProfile can be created only for an applicant."
        if self.household_size < 1:
            errors["household_size"] = "Household size must be at least 1."
        if self.dependents_count < 0:
            errors["dependents_count"] = "Dependents count cannot be negative."
        if self.dependents_count > self.household_size:
            errors["dependents_count"] = "Dependents count cannot exceed household size."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"ApplicantProfile(user_id={self.user_id})"
