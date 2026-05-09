from rest_framework import serializers
from .models import AidRequest, RequestStatusHistory, HelpCommitment, RequestStatus


class AidRequestCreateSerializer(serializers.ModelSerializer):
    urgency = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = AidRequest
        fields = (
            "id", "category", "title", "description", "region",
            "requested_amount", "urgency", "status", "risk_score", "is_flagged",
            "created_at"
        )
        read_only_fields = ("id", "status", "risk_score", "is_flagged", "created_at")

    def create(self, validated_data):
        user = self.context["request"].user

        obj = AidRequest.objects.create(
            applicant=user,
            status=RequestStatus.ON_MODERATION,
            risk_score=0,
            is_flagged=False,
            **validated_data
        )

        RequestStatusHistory.objects.create(
            aid_request=obj,
            old_status="",
            new_status=obj.status,
            changed_by=user,
            comment="Заявка создана"
        )
        return obj


class AidRequestListSerializer(serializers.ModelSerializer):
    applicant_username = serializers.CharField(source="applicant.username", read_only=True)

    class Meta:
        model = AidRequest
        fields = (
            "id", "title", "category", "region", "requested_amount", "urgency",
            "status", "risk_score", "is_flagged", "applicant_username", "created_at"
        )


class ModerationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class HelpCommitSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["certificate", "cart", "invoice", "mock"])
    note = serializers.CharField(required=False, allow_blank=True, default="")

class RequestStatusHistorySerializer(serializers.ModelSerializer):
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
