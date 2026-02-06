from django.contrib.auth.models import AbstractUser
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

