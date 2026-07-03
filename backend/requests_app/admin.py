from django.contrib import admin
from .models import AidFulfillment, AidRequest, RequestStatusHistory, HelpCommitment


@admin.register(AidRequest)
class AidRequestAdmin(admin.ModelAdmin):
    readonly_fields = ("status",)
    list_display = (
        "id", "title", "category", "region", "status",
        "risk_score", "is_flagged", "applicant", "created_at"
    )
    list_filter = ("status", "category", "region", "is_flagged")
    search_fields = ("title", "description", "region", "applicant__username")

    def has_add_permission(self, request):
        return False


@admin.register(RequestStatusHistory)
class RequestStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "old_status", "new_status", "changed_by", "created_at")
    list_filter = ("new_status",)


@admin.register(HelpCommitment)
class HelpCommitmentAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "helper", "method", "created_at")
    list_filter = ("method",)


@admin.register(AidFulfillment)
class AidFulfillmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "commitment", "request_id", "helper", "provider_name", "amount", "status"
    )
    list_select_related = ("commitment", "commitment__aid_request", "commitment__helper")
    readonly_fields = (
        "commitment", "fulfillment_type", "provider_name", "amount", "certificate_code",
        "status", "created_by", "delivered_at", "confirmed_at", "created_at", "updated_at",
    )

    @admin.display(description="Request")
    def request_id(self, obj):
        return obj.commitment.aid_request_id

    @admin.display(description="Helper")
    def helper(self, obj):
        return obj.commitment.helper

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
