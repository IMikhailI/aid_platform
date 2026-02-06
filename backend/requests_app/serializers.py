from rest_framework import serializers
from .models import AidRequest, RequestStatusHistory, HelpCommitment, RequestStatus


class AidRequestCreateSerializer(serializers.ModelSerializer):
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

        # Базовый rule-based антифрод (MVP)
        risk = 0
        if validated_data.get("requested_amount", 0) and validated_data["requested_amount"] > 20000:
            risk += 40
        if validated_data.get("urgency", 3) >= 5:
            risk += 20

        flagged = risk >= 50

        obj = AidRequest.objects.create(
            applicant=user,
            status=RequestStatus.ON_MODERATION,
            risk_score=risk,
            is_flagged=flagged,
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

