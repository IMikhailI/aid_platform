from django.db import transaction
from rest_framework import serializers

from .models import AidRequest, RequestStatusHistory, HelpCommitment, RequestStatus
from .services.transitions import transition_request


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

    class Meta:
        model = AidRequest
        fields = (
            "id", "title", "category", "region", "requested_amount", "urgency",
            "status", "risk_score", "is_flagged", "applicant_username", "created_at"
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
