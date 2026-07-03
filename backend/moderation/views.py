from rest_framework import filters, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema

from moderation.models import ApplicantVerification, VerificationStatus
from moderation.serializers import (
    ApplicantProfileSerializer,
    ApplicantVerificationHistorySerializer,
    ApplicantVerificationSummarySerializer,
    ModeratorVerificationSerializer,
    VerificationDecisionSerializer,
    VerificationErrorSerializer,
)
from moderation.services import (
    VerificationStateConflict,
    VerificationValidationError,
    review_verification,
    submit_verification,
)
from requests_app.permissions import IsApplicant, IsModerator
from users.models import ApplicantProfile


class ApplicantProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ApplicantProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        profile, _ = ApplicantProfile.objects.get_or_create(user=self.request.user)
        return profile

    @extend_schema(
        operation_id="applicant_profile_retrieve",
        tags=["applicant-profile"],
        summary="Получить профиль текущего applicant",
        responses={200: ApplicantProfileSerializer, 403: OpenApiResponse(description="Недостаточно прав")}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id="applicant_profile_update",
        tags=["applicant-profile"],
        summary="Обновить профиль текущего applicant",
        request=ApplicantProfileSerializer,
        responses={
            200: ApplicantProfileSerializer,
            400: OpenApiResponse(description="Ошибка валидации профиля"),
            403: OpenApiResponse(description="Недостаточно прав"),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ApplicantVerificationSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    @extend_schema(
        operation_id="applicant_verification_submit",
        tags=["applicant-verification"],
        summary="Отправить профиль на верификацию",
        request=None,
        responses={
            201: ApplicantVerificationSummarySerializer,
            400: VerificationErrorSerializer,
            403: OpenApiResponse(description="Недостаточно прав"),
            409: VerificationErrorSerializer,
        },
    )
    def post(self, request):
        profile, _ = ApplicantProfile.objects.get_or_create(user=request.user)
        try:
            verification = submit_verification(profile=profile)
        except VerificationValidationError as exc:
            return Response({"code": exc.code, "detail": exc.detail}, status=400)
        except VerificationStateConflict as exc:
            return Response({"code": exc.code, "detail": exc.detail}, status=409)
        return Response(
            ApplicantVerificationSummarySerializer(verification).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicantVerificationHistoryView(generics.ListAPIView):
    serializer_class = ApplicantVerificationHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]
    pagination_class = None
    filter_backends = []

    @extend_schema(
        operation_id="applicant_verification_history",
        tags=["applicant-verification"],
        summary="Получить собственную историю верификации",
        responses={
            200: ApplicantVerificationHistorySerializer(many=True),
            403: OpenApiResponse(description="Недостаточно прав"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ApplicantVerification.objects.none()
        return ApplicantVerification.objects.filter(profile__user=self.request.user)


class ModeratorVerificationQueueView(generics.ListAPIView):
    serializer_class = ModeratorVerificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["submitted_at"]
    ordering = ["-submitted_at", "-id"]

    @extend_schema(
        operation_id="moderation_verification_list",
        tags=["moderation-verification"],
        summary="Получить очередь верификаций",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                enum=[choice for choice, _ in VerificationStatus.choices],
                description="Фильтр статуса; по умолчанию pending",
            ),
            OpenApiParameter(
                name="region",
                type=OpenApiTypes.STR,
                description="Регион applicant, регистронезависимое точное совпадение",
            ),
        ],
        responses={
            200: ModeratorVerificationSerializer(many=True),
            403: OpenApiResponse(description="Недостаточно прав"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = ApplicantVerification.objects.select_related(
            "profile", "profile__user", "reviewed_by"
        )
        requested_status = self.request.query_params.get("status", VerificationStatus.PENDING)
        valid_statuses = {choice for choice, _ in VerificationStatus.choices}
        if requested_status in valid_statuses:
            queryset = queryset.filter(status=requested_status)
        region = self.request.query_params.get("region")
        if region:
            queryset = queryset.filter(profile__user__region__iexact=region)
        return queryset


class ModeratorVerificationDetailView(generics.RetrieveAPIView):
    serializer_class = ModeratorVerificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator]
    queryset = ApplicantVerification.objects.select_related(
        "profile", "profile__user", "reviewed_by"
    )

    @extend_schema(
        operation_id="moderation_verification_retrieve",
        tags=["moderation-verification"],
        summary="Получить верификацию",
        responses={
            200: ModeratorVerificationSerializer,
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Verification не найдена"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ModeratorVerificationDecisionView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    @extend_schema(
        operation_id="moderation_verification_decide",
        tags=["moderation-verification"],
        summary="Принять решение по верификации",
        request=VerificationDecisionSerializer,
        responses={
            200: ModeratorVerificationSerializer,
            400: VerificationErrorSerializer,
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Verification не найдена"),
            409: VerificationErrorSerializer,
        },
    )
    def post(self, request, pk: int):
        serializer = VerificationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            verification = review_verification(
                verification_id=pk,
                reviewer=request.user,
                decision=serializer.validated_data["decision"],
                comment=serializer.validated_data["comment"],
            )
        except ApplicantVerification.DoesNotExist:
            return Response({"detail": "Verification не найдена."}, status=404)
        except VerificationValidationError as exc:
            return Response({"code": exc.code, "detail": exc.detail}, status=400)
        except VerificationStateConflict as exc:
            return Response({"code": exc.code, "detail": exc.detail}, status=409)
        return Response(ModeratorVerificationSerializer(verification).data, status=200)
