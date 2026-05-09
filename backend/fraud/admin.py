import json
from django.contrib import admin
from .models import FraudCheck, FraudDecision, FraudOverride


@admin.register(FraudCheck)
class FraudCheckAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "signal_code", "weight", "created_at")
    list_filter = ("signal_code", "created_at")
    search_fields = ("aid_request__id", "signal_code")
    ordering = ("-created_at",)


@admin.register(FraudDecision)
class FraudDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "aid_request",
        "score",
        "risk_level",
        "base_action",
        "action",
        "is_overridden",
        "engine_version",
        "decided_at",
    )
    list_filter = ("risk_level", "base_action", "action", "is_overridden", "engine_version", "decided_at")
    search_fields = ("aid_request__id",)
    ordering = ("-decided_at",)

    readonly_fields = ("pretty_reasons",)

    def pretty_reasons(self, obj):
        return json.dumps(obj.reasons, ensure_ascii=False, indent=2)

    pretty_reasons.short_description = "Reasons (debug)"


@admin.register(FraudOverride)
class FraudOverrideAdmin(admin.ModelAdmin):
    list_display = ("id", "aid_request", "old_action", "new_action", "changed_by", "created_at")
    list_filter = ("old_action", "new_action", "created_at")
    search_fields = ("aid_request__id", "changed_by__username")
    ordering = ("-created_at",)
