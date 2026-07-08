from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, PolymorphicProxySerializer, extend_schema

from requests_app.fulfillment_serializers import (
    ApplicantDeliveredFulfillmentSerializer, ApplicantPreparedFulfillmentSerializer,
    FulfillmentCreateSerializer,
    FulfillmentErrorSerializer, HelperFulfillmentSerializer,
    HelperOwnedRequestSerializer, ModeratorFulfillmentSerializer,
    ReceiptConfirmationSerializer,
)
from requests_app.models import AidFulfillment, HelpCommitment
from requests_app.permissions import IsApplicant, IsHelperOnly, IsModerator
from requests_app.services.fulfillment import (
    FulfillmentNotFound, FulfillmentStateConflict, FulfillmentValidationError,
    confirm_certificate_received, create_mock_certificate, mark_certificate_delivered,
)


def fulfillment_error_response(exc):
    if isinstance(exc, FulfillmentNotFound):
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, FulfillmentStateConflict):
        response_status = status.HTTP_409_CONFLICT
    else:
        response_status = status.HTTP_400_BAD_REQUEST
    return Response({"code": exc.code, "detail": exc.detail}, status=response_status)


class HelperOwnedRequestsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class HelperOwnedRequestsView(generics.ListAPIView):
    queryset = HelpCommitment.objects.none()
    serializer_class = HelperOwnedRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsHelperOnly]
    pagination_class = HelperOwnedRequestsPagination
    filter_backends = []

    @extend_schema(
        operation_id="helper_owned_requests_list",
        tags=["helper-requests"],
        summary="Получить заявки, взятые текущим helper",
        description=(
            "Privacy-safe список собственных HelpCommitment с безопасной "
            "сводкой fulfillment. Applicant identity, fraud, verification, "
            "telemetry и полный certificate_code не возвращаются."
        ),
        responses={
            200: HelperOwnedRequestSerializer(many=True),
            403: OpenApiResponse(description="Недостаточно прав"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return HelpCommitment.objects.none()
        return (
            HelpCommitment.objects
            .filter(helper=self.request.user)
            .select_related("aid_request", "fulfillment")
            .order_by("-created_at", "-id")
        )


class HelperFulfillmentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHelperOnly]

    @extend_schema(operation_id="helper_fulfillment_retrieve", tags=["helper-fulfillment"], summary="Получить собственный fulfillment", responses={200: HelperFulfillmentSerializer, 403: OpenApiResponse(description="Недостаточно прав"), 404: FulfillmentErrorSerializer})
    def get(self, request, request_id: int):
        fulfillment = get_object_or_404(
            AidFulfillment.objects.select_related("commitment"),
            commitment__aid_request_id=request_id, commitment__helper=request.user,
        )
        return Response(HelperFulfillmentSerializer(fulfillment).data)

    @extend_schema(operation_id="helper_fulfillment_create", tags=["helper-fulfillment"], summary="Создать демонстрационный сертификат", request=FulfillmentCreateSerializer, responses={201: HelperFulfillmentSerializer, 400: FulfillmentErrorSerializer, 403: OpenApiResponse(description="Недостаточно прав"), 404: FulfillmentErrorSerializer, 409: FulfillmentErrorSerializer})
    def post(self, request, request_id: int):
        serializer = FulfillmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            fulfillment = create_mock_certificate(
                request_id=request_id, helper=request.user,
                provider_name=serializer.validated_data["provider_name"],
                amount=serializer.validated_data["amount"],
            )
        except (FulfillmentNotFound, FulfillmentValidationError, FulfillmentStateConflict) as exc:
            return fulfillment_error_response(exc)
        return Response(HelperFulfillmentSerializer(fulfillment).data, status=201)


class HelperFulfillmentDeliverView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHelperOnly]

    @extend_schema(operation_id="helper_fulfillment_deliver", tags=["helper-fulfillment"], summary="Отметить сертификат переданным", request=None, responses={200: HelperFulfillmentSerializer, 403: OpenApiResponse(description="Недостаточно прав"), 404: FulfillmentErrorSerializer, 409: FulfillmentErrorSerializer})
    def post(self, request, request_id: int):
        try:
            fulfillment = mark_certificate_delivered(request_id=request_id, helper=request.user)
        except (FulfillmentNotFound, FulfillmentStateConflict) as exc:
            return fulfillment_error_response(exc)
        return Response(HelperFulfillmentSerializer(fulfillment).data)


class ApplicantFulfillmentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    @extend_schema(
        operation_id="applicant_fulfillment_retrieve",
        tags=["applicant-fulfillment"],
        summary="Получить fulfillment собственной заявки",
        responses={
            200: PolymorphicProxySerializer(
                component_name="ApplicantFulfillmentResponse",
                serializers=[
                    ApplicantPreparedFulfillmentSerializer,
                    ApplicantDeliveredFulfillmentSerializer,
                ],
                resource_type_field_name=None,
            ),
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Fulfillment не найден"),
        },
    )
    def get(self, request, request_id: int):
        fulfillment = get_object_or_404(
            AidFulfillment.objects.select_related("commitment__aid_request"),
            commitment__aid_request_id=request_id,
            commitment__aid_request__applicant=request.user,
        )
        serializer_class = (
            ApplicantPreparedFulfillmentSerializer
            if fulfillment.status == "created"
            else ApplicantDeliveredFulfillmentSerializer
        )
        return Response(serializer_class(fulfillment).data)


class ApplicantConfirmReceiptView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    @extend_schema(operation_id="applicant_receipt_confirm", tags=["applicant-fulfillment"], summary="Подтвердить получение помощи", request=None, responses={200: ReceiptConfirmationSerializer, 403: OpenApiResponse(description="Недостаточно прав"), 404: FulfillmentErrorSerializer, 409: FulfillmentErrorSerializer})
    def post(self, request, request_id: int):
        try:
            fulfillment = confirm_certificate_received(request_id=request_id, applicant=request.user)
        except (FulfillmentNotFound, FulfillmentStateConflict) as exc:
            return fulfillment_error_response(exc)
        return Response({"request_status": "closed", "fulfillment_status": fulfillment.status})


class ModeratorFulfillmentView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    @extend_schema(operation_id="moderation_fulfillment_retrieve", tags=["moderation-fulfillment"], summary="Получить служебные сведения fulfillment", responses={200: ModeratorFulfillmentSerializer, 403: OpenApiResponse(description="Недостаточно прав"), 404: OpenApiResponse(description="Fulfillment не найден")})
    def get(self, request, request_id: int):
        fulfillment = get_object_or_404(
            AidFulfillment.objects.select_related(
                "commitment__helper", "commitment__aid_request__applicant", "created_by"
            ), commitment__aid_request_id=request_id,
        )
        return Response(ModeratorFulfillmentSerializer(fulfillment).data)
