from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from moderation.models import ApplicantVerification, VerificationStatus
from users.models import ApplicantProfile


def current_verification_status(profile: ApplicantProfile) -> str:
    latest = profile.verification_requests.first()
    return latest.status if latest else "not_submitted"


class ApplicantVerificationSummarySerializer(serializers.ModelSerializer):
    comment = serializers.CharField(source="review_comment", read_only=True)

    class Meta:
        model = ApplicantVerification
        fields = ("id", "status", "submitted_at", "reviewed_at", "comment")
        read_only_fields = fields


class ApplicantProfileSerializer(serializers.ModelSerializer):
    region = serializers.CharField(source="user.region", read_only=True)
    verification_status = serializers.SerializerMethodField()
    latest_verification = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantProfile
        fields = (
            "household_size",
            "dependents_count",
            "consent_to_data_processing",
            "region",
            "verification_status",
            "latest_verification",
        )
        read_only_fields = ("region", "verification_status", "latest_verification")

    def validate(self, attrs):
        household_size = attrs.get("household_size", self.instance.household_size)
        dependents_count = attrs.get("dependents_count", self.instance.dependents_count)
        if household_size < 1:
            raise serializers.ValidationError({"household_size": "Минимальное значение — 1."})
        if dependents_count > household_size:
            raise serializers.ValidationError(
                {"dependents_count": "Количество иждивенцев не может превышать размер домохозяйства."}
            )
        return attrs

    @extend_schema_field(
        serializers.ChoiceField(
            choices=["not_submitted", "pending", "verified", "rejected"]
        )
    )
    def get_verification_status(self, obj):
        return current_verification_status(obj)

    @extend_schema_field(ApplicantVerificationSummarySerializer(allow_null=True))
    def get_latest_verification(self, obj):
        latest = obj.verification_requests.first()
        return ApplicantVerificationSummarySerializer(latest).data if latest else None


class ApplicantVerificationHistorySerializer(ApplicantVerificationSummarySerializer):
    pass


class ModeratorVerificationSerializer(serializers.ModelSerializer):
    applicant_user_id = serializers.IntegerField(source="profile.user_id", read_only=True)
    applicant_username = serializers.CharField(source="profile.user.username", read_only=True)
    region = serializers.CharField(source="profile.user.region", read_only=True)
    household_size = serializers.IntegerField(source="profile.household_size", read_only=True)
    dependents_count = serializers.IntegerField(source="profile.dependents_count", read_only=True)
    consent_to_data_processing = serializers.BooleanField(
        source="profile.consent_to_data_processing", read_only=True
    )
    reviewed_by = serializers.IntegerField(source="reviewed_by_id", read_only=True)

    class Meta:
        model = ApplicantVerification
        fields = (
            "id",
            "applicant_user_id",
            "applicant_username",
            "region",
            "household_size",
            "dependents_count",
            "consent_to_data_processing",
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "review_comment",
        )
        read_only_fields = fields


class VerificationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[VerificationStatus.VERIFIED, VerificationStatus.REJECTED]
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=1000,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        if attrs["decision"] == VerificationStatus.REJECTED and not attrs["comment"].strip():
            raise serializers.ValidationError(
                {"comment": "Для отклонения необходимо указать комментарий."}
            )
        return attrs


class VerificationErrorSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
