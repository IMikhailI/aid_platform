from django.contrib import admin
from .models import AidRequest, RequestStatusHistory, HelpCommitment


@admin.register(AidRequest)
class AidRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "category", "region", "status",
        "risk_score", "is_flagged", "applicant", "created_at"
    )
    list_filter = ("status", "category", "region", "is_flagged")
    search_fields = ("title", "description", "region", "applicant__username")


@admin.register(RequestStatusHistory)
class RequestStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status",)


@admin.register(HelpCommitment)
class HelpCommitmentAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "helper", "method", "created_at")
    list_filter = ("method",)

