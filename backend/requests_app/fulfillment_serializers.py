from decimal import Decimal

from rest_framework import serializers

from requests_app.models import AidFulfillment, FulfillmentStatus


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


class ApplicantFulfillmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AidFulfillment
        fields = (
            "id", "provider_name", "amount", "status", "certificate_code",
            "created_at", "delivered_at", "confirmed_at",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.status == FulfillmentStatus.CREATED:
            data.pop("certificate_code", None)
        return data


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
