from decimal import Decimal

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from requests_app.models import AidFulfillment, HelpCommitment


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


class HelperOwnedRequestSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(source="aid_request_id", read_only=True)
    title = serializers.CharField(source="aid_request.title", read_only=True)
    category = serializers.CharField(source="aid_request.category", read_only=True)
    region = serializers.CharField(source="aid_request.region", read_only=True)
    requested_amount = serializers.DecimalField(
        source="aid_request.requested_amount", max_digits=10, decimal_places=2,
        read_only=True,
    )
    urgency = serializers.IntegerField(source="aid_request.urgency", read_only=True)
    request_status = serializers.CharField(source="aid_request.status", read_only=True)
    created_at = serializers.DateTimeField(source="aid_request.created_at", read_only=True)
    taken_at = serializers.DateTimeField(source="created_at", read_only=True)
    commitment_method = serializers.CharField(source="method", read_only=True)
    commitment_note = serializers.CharField(source="note", read_only=True)
    fulfillment_status = serializers.SerializerMethodField()
    fulfillment_type = serializers.CharField(
        source="fulfillment.fulfillment_type", allow_null=True, default=None,
        read_only=True,
    )
    provider_name = serializers.CharField(
        source="fulfillment.provider_name", allow_null=True, default=None,
        read_only=True,
    )
    fulfillment_amount = serializers.DecimalField(
        source="fulfillment.amount", max_digits=10, decimal_places=2,
        allow_null=True, default=None, read_only=True,
    )
    masked_certificate_code = serializers.SerializerMethodField()
    delivered_at = serializers.DateTimeField(
        source="fulfillment.delivered_at", allow_null=True, default=None,
        read_only=True,
    )
    confirmed_at = serializers.DateTimeField(
        source="fulfillment.confirmed_at", allow_null=True, default=None,
        read_only=True,
    )

    class Meta:
        model = HelpCommitment
        fields = (
            "request_id", "title", "category", "region", "requested_amount",
            "urgency", "request_status", "created_at", "taken_at",
            "commitment_method", "commitment_note", "fulfillment_status",
            "fulfillment_type", "provider_name", "fulfillment_amount",
            "masked_certificate_code", "delivered_at", "confirmed_at",
        )
        read_only_fields = fields

    @staticmethod
    def _fulfillment(obj):
        try:
            return obj.fulfillment
        except AidFulfillment.DoesNotExist:
            return None

    @extend_schema_field(
        serializers.CharField(
            read_only=True,
            help_text="Без fulfillment: none; иначе created, delivered или confirmed.",
        )
    )
    def get_fulfillment_status(self, obj) -> str:
        fulfillment = self._fulfillment(obj)
        return fulfillment.status if fulfillment else "none"

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_masked_certificate_code(self, obj):
        fulfillment = self._fulfillment(obj)
        return mask_certificate_code(fulfillment.certificate_code) if fulfillment else None


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
