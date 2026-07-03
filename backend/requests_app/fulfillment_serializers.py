from decimal import Decimal

from rest_framework import serializers

from requests_app.models import AidFulfillment


def mask_certificate_code(value) -> str:
    code = str(value)
    return f"********-****-****-****-********{code[-4:]}"


class FulfillmentCreateSerializer(serializers.Serializer):
    provider_name = serializers.CharField(max_length=120, trim_whitespace=True)
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )


class HelperFulfillmentSerializer(serializers.ModelSerializer):
    masked_certificate_code = serializers.SerializerMethodField()

    class Meta:
        model = AidFulfillment
        fields = (
            "id", "fulfillment_type", "provider_name", "amount", "status",
            "masked_certificate_code", "created_at", "delivered_at", "confirmed_at",
        )
        read_only_fields = fields

    def get_masked_certificate_code(self, obj) -> str:
        return mask_certificate_code(obj.certificate_code)


class ApplicantPreparedFulfillmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AidFulfillment
        fields = (
            "id", "provider_name", "amount", "status",
            "created_at", "delivered_at", "confirmed_at",
        )
        read_only_fields = fields


class ApplicantDeliveredFulfillmentSerializer(ApplicantPreparedFulfillmentSerializer):
    certificate_code = serializers.UUIDField(read_only=True)

    class Meta(ApplicantPreparedFulfillmentSerializer.Meta):
        fields = ApplicantPreparedFulfillmentSerializer.Meta.fields + ("certificate_code",)


class ModeratorFulfillmentSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(source="commitment.aid_request_id", read_only=True)
    helper_id = serializers.IntegerField(source="commitment.helper_id", read_only=True)
    helper_username = serializers.CharField(source="commitment.helper.username", read_only=True)
    applicant_id = serializers.IntegerField(source="commitment.aid_request.applicant_id", read_only=True)
    applicant_username = serializers.CharField(source="commitment.aid_request.applicant.username", read_only=True)
    created_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = AidFulfillment
        fields = (
            "id", "request_id", "fulfillment_type", "provider_name", "amount",
            "status", "certificate_code", "helper_id", "helper_username",
            "applicant_id", "applicant_username", "created_by_id", "created_at",
            "delivered_at", "confirmed_at",
        )
        read_only_fields = fields


class ReceiptConfirmationSerializer(serializers.Serializer):
    request_status = serializers.CharField(read_only=True)
    fulfillment_status = serializers.CharField(read_only=True)


class FulfillmentErrorSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)
