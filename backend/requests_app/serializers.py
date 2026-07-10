from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import AidRequest, RequestStatusHistory, HelpCommitment, RequestStatus
from .services.transitions import transition_request
from fraud.models import FraudAction, FraudRiskLevel


class AidRequestCreateSerializer(serializers.ModelSerializer):
    urgency = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = AidRequest
        fields = (
            "id", "category", "title", "description", "region",
            "requested_amount", "urgency", "status", "created_at", "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        obj = AidRequest.objects.create(
            applicant=user,
            status=RequestStatus.DRAFT,
            risk_score=0,
            is_flagged=False,
            **validated_data
        )
        result = transition_request(
            request_id=obj.id,
            target_status=RequestStatus.ON_MODERATION,
            actor=user,
            comment="Заявка создана",
        )
        return result.aid_request


class ApplicantAidRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AidRequest
        fields = (
            "id", "category", "title", "description", "region",
            "requested_amount", "urgency", "status", "created_at", "updated_at",
        )
        read_only_fields = fields


class HelperAidRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AidRequest
        fields = (
            "id", "title", "category", "region", "requested_amount", "urgency",
            "status", "created_at",
        )
        read_only_fields = fields


class ModeratorAidRequestSerializer(serializers.ModelSerializer):
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)
    applicant_verification_status = serializers.SerializerMethodField()
    risk_level = serializers.SerializerMethodField()
    fraud_action = serializers.SerializerMethodField()
    latest_moderation_comment = serializers.SerializerMethodField()

    @extend_schema_field(
        serializers.ChoiceField(
            choices=["not_submitted", "pending", "verified", "rejected"]
        )
    )
    def get_applicant_verification_status(self, obj):
        try:
            profile = obj.applicant.applicant_profile
        except ObjectDoesNotExist:
            return "not_submitted"
        latest = profile.verification_requests.first()
        return latest.status if latest else "not_submitted"

    @extend_schema_field(serializers.ChoiceField(choices=FraudRiskLevel.choices, allow_null=True))
    def get_risk_level(self, obj):
        try:
            return obj.fraud_decision.risk_level
        except ObjectDoesNotExist:
            return None

    @extend_schema_field(serializers.ChoiceField(choices=FraudAction.choices, allow_null=True))
    def get_fraud_action(self, obj):
        try:
            return obj.fraud_decision.action
        except ObjectDoesNotExist:
            return None

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_latest_moderation_comment(self, obj):
        histories = getattr(obj, "_prefetched_objects_cache", {}).get("status_history")
        if histories is not None:
            for item in histories:
                if item.new_status in {RequestStatus.PUBLISHED, RequestStatus.REJECTED} and item.comment:
                    return item.comment
            return ""

        latest = (
            obj.status_history
            .filter(new_status__in=[RequestStatus.PUBLISHED, RequestStatus.REJECTED])
            .exclude(comment="")
            .order_by("-created_at")
            .first()
        )
        return latest.comment if latest else ""

    class Meta:
        model = AidRequest
        fields = (
            "id", "title", "category", "region", "requested_amount", "urgency",
            "status", "risk_score", "risk_level", "fraud_action", "is_flagged",
            "applicant_username", "applicant_verification_status",
            "latest_moderation_comment", "created_at", "updated_at",
        )
        read_only_fields = fields


class ModerationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class HelpCommitSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["certificate", "cart", "invoice", "mock"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ApplicantRequestStatusHistorySerializer(serializers.ModelSerializer):
    from_status = serializers.CharField(source="old_status", read_only=True)
    to_status = serializers.CharField(source="new_status", read_only=True)
    changed_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = RequestStatusHistory
        fields = ("from_status", "to_status", "changed_at")
        read_only_fields = fields


class HelperRequestStatusHistorySerializer(serializers.ModelSerializer):
    from_status = serializers.CharField(source="old_status", read_only=True)
    to_status = serializers.CharField(source="new_status", read_only=True)
    changed_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = RequestStatusHistory
        fields = ("from_status", "to_status", "changed_at")
        read_only_fields = fields


class ModeratorRequestStatusHistorySerializer(serializers.ModelSerializer):
    from_status = serializers.CharField(source="old_status", read_only=True)
    to_status = serializers.CharField(source="new_status", read_only=True)
    changed_at = serializers.DateTimeField(source="created_at", read_only=True)
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)
    changed_by_role = serializers.CharField(source="changed_by.role", read_only=True)

    class Meta:
        model = RequestStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "comment",
            "changed_at",
            "changed_by",
            "changed_by_username",
            "changed_by_role",
        ]
        read_only_fields = fields


class StatusTransitionResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    new_status = serializers.CharField(read_only=True)


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class FraudPolicyErrorSerializer(serializers.Serializer):
    code = serializers.ChoiceField(
        choices=["fraud_publication_blocked", "fraud_decision_missing"],
        read_only=True,
    )
    detail = serializers.CharField(read_only=True)
