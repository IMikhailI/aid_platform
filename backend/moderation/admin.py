from django.contrib import admin

from moderation.models import ApplicantVerification


@admin.register(ApplicantVerification)
class ApplicantVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )
    list_filter = ("status",)
    list_select_related = ("profile", "profile__user", "reviewed_by")
    readonly_fields = (
        "profile",
        "status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "review_comment",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
