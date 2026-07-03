from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import ApplicantProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra", {"fields": ("role", "region")}),
    )
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "household_size",
        "dependents_count",
        "consent_to_data_processing",
        "updated_at",
    )
    list_select_related = ("user",)
    readonly_fields = ("user", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
