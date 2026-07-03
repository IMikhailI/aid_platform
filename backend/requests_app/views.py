from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend


from .models import AidRequest, RequestStatus, RequestStatusHistory, HelpCommitment
from .permissions import IsApplicant, IsModerator, IsHelper, CanCloseRequest
from .services.transitions import InvalidRequestTransition, transition_request
from .serializers import (
    AidRequestCreateSerializer,
    ApplicantAidRequestSerializer,
    HelperAidRequestSerializer,
    ModeratorAidRequestSerializer,
    ModerationActionSerializer,
    HelpCommitSerializer,
    ApplicantRequestStatusHistorySerializer,
    HelperRequestStatusHistorySerializer,
    ModeratorRequestStatusHistorySerializer,
    StatusTransitionResponseSerializer,
    DetailResponseSerializer,
    FraudPolicyErrorSerializer,
)
from fraud.services.engine import evaluate_request_safe
from fraud.services.device import extract_request_telemetry
from fraud.models import FraudDecision
from fraud.services.policy import FraudPolicyViolation, assert_request_can_be_published
from moderation.models import ApplicantVerification
from drf_spectacular.utils import extend_schema, OpenApiResponse, PolymorphicProxySerializer

class DefaultPagePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ApplicantCreateRequestView(generics.CreateAPIView):
    serializer_class = AidRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    @transaction.atomic
    def perform_create(self, serializer):
        # 1) Создаем заявку от текущего applicant
        obj = serializer.save()
        telemetry = extract_request_telemetry(self.request)
        obj.device_id_hash = telemetry["device_id_hash"]
        obj.ip_hash = telemetry["ip_hash"]
        obj.user_agent_hash = telemetry["user_agent_hash"]
        obj.save(update_fields=["device_id_hash", "ip_hash", "user_agent_hash", "updated_at"])

        # 2) Антифрод обновляет только fraud-метаданные, не lifecycle status.
        evaluate_request_safe(obj)


class ApplicantOwnRequestsView(generics.ListAPIView):
    queryset = AidRequest.objects.none()
    serializer_class = ApplicantAidRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    def get_queryset(self):
        return AidRequest.objects.filter(applicant=self.request.user)

class PublicPublishedRequestsView(generics.ListAPIView):
    serializer_class = HelperAidRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsHelper]
    pagination_class = DefaultPagePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category"]  # region лучше через кастом, чтобы iexact
    search_fields = ["title", "region"]
    ordering_fields = ["created_at", "requested_amount", "urgency"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AidRequest.objects.filter(status=RequestStatus.PUBLISHED)

        # region case-insensitive exact
        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region__iexact=region)

        return qs

class ModerationQueueView(generics.ListAPIView):
    serializer_class = ModeratorAidRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator]
    pagination_class = DefaultPagePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "is_flagged"]   # добавили is_flagged
    search_fields = ["title", "description", "region"]
    ordering_fields = ["created_at", "risk_score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            AidRequest.objects
            .filter(status=RequestStatus.ON_MODERATION)
            .select_related("applicant", "applicant__applicant_profile")
            .prefetch_related(
                "fraud_decision",
                Prefetch(
                    "applicant__applicant_profile__verification_requests",
                    queryset=ApplicantVerification.objects.order_by("-submitted_at", "-id"),
                ),
            )
        )

        # region case-insensitive
        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region__iexact=region)

        # risk range
        risk_min = self.request.query_params.get("risk_min")
        if risk_min is not None and risk_min != "":
            try:
                qs = qs.filter(risk_score__gte=float(risk_min))
            except ValueError:
                pass

        risk_max = self.request.query_params.get("risk_max")
        if risk_max is not None and risk_max != "":
            try:
                qs = qs.filter(risk_score__lte=float(risk_max))
            except ValueError:
                pass

        # fraud action from related FraudDecision
        # (если related_name у тебя другой — подправь "fraud_decision__action")
        fraud_action = self.request.query_params.get("fraud_action")
        if fraud_action:
            qs = qs.filter(fraud_decision__action=fraud_action)

        return qs


class ModerateRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    @extend_schema(
        request=ModerationActionSerializer,
        responses={
            200: StatusTransitionResponseSerializer,
            400: OpenApiResponse(
                description="Ошибка валидации или недопустимый lifecycle-переход"
            ),
            409: OpenApiResponse(
                response=FraudPolicyErrorSerializer,
                description=(
                    "Approve запрещён: effective action=block "
                    "(fraud_publication_blocked) или решение отсутствует "
                    "(fraud_decision_missing)"
                ),
            ),
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Заявка не найдена"),
        },
        summary="Модерация заявки",
        description="Moderator/admin: approve или reject заявки в очереди модерации",
    ) 
    @transaction.atomic
    def post(self, request, request_id: int):
        serializer = ModerationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        comment = serializer.validated_data.get("comment", "")
        target_status = RequestStatus.PUBLISHED if action == "approve" else RequestStatus.REJECTED

        try:
            aid_request = AidRequest.objects.select_for_update().get(id=request_id)
            if action == "approve":
                decision = (
                    FraudDecision.objects.select_for_update()
                    .filter(aid_request=aid_request)
                    .first()
                )
                assert_request_can_be_published(decision)

            result = transition_request(
                request_id=aid_request.id,
                target_status=target_status,
                actor=request.user,
                comment=comment,
            )
        except AidRequest.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=404)
        except FraudPolicyViolation as exc:
            return Response(
                {"code": exc.code, "detail": exc.detail},
                status=status.HTTP_409_CONFLICT,
            )
        except InvalidRequestTransition:
            return Response({"detail": "Недопустимый переход статуса заявки."}, status=400)

        if not result.changed:
            return Response({"detail": "Заявка уже находится в целевом статусе."}, status=400)

        obj = result.aid_request
        return Response({"id": obj.id, "new_status": obj.status}, status=200)


class TakeRequestIntoWorkView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHelper]
    
    @extend_schema(
        request=HelpCommitSerializer,
        responses={
            200: HelperAidRequestSerializer,
            400: OpenApiResponse(description="Ошибка валидации"),
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Заявка не найдена"),
        },
        summary="Взять заявку в работу",
        description="Helper/admin берёт опубликованную заявку в работу",
    )
    @transaction.atomic
    def post(self, request, request_id: int):
        serializer = HelpCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            obj = AidRequest.objects.select_for_update().get(id=request_id)
        except AidRequest.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=404)

        if hasattr(obj, "commitment"):
            return Response({"detail": "Заявка уже взята в работу"}, status=400)

        try:
            result = transition_request(
                request_id=obj.id,
                target_status=RequestStatus.IN_PROGRESS,
                actor=request.user,
                comment="Заявка взята в работу",
            )
        except InvalidRequestTransition:
            return Response({"detail": "Недопустимый переход статуса заявки."}, status=400)

        if not result.changed:
            return Response({"detail": "Заявка уже находится в работе."}, status=400)

        HelpCommitment.objects.create(
            aid_request=result.aid_request,
            helper=request.user,
            method=serializer.validated_data["method"],
            note=serializer.validated_data.get("note", ""),
        )

        obj = result.aid_request
        return Response(HelperAidRequestSerializer(obj).data, status=200)

class CloseRequestView(APIView):
    permission_classes = [IsAuthenticated, CanCloseRequest]

    @extend_schema(
        request=None,
        summary="Закрыть заявку",
        description="Закрывает заявку в статусе in_progress. Доступно admin или helper, который взял заявку в работу.",
        responses={
            200: DetailResponseSerializer,
            400: OpenApiResponse(description="Нельзя закрыть заявку в текущем статусе"),
            403: OpenApiResponse(description="Недостаточно прав"),
            404: OpenApiResponse(description="Заявка не найдена"),
        },
    )
    @transaction.atomic
    def patch(self, request, request_id):
        aid_request = get_object_or_404(
            AidRequest.objects.select_for_update(),
            id=request_id
        )

        # helper — может закрыть только свою взятую заявку
        if request.user.role == "helper":
            has_commitment = HelpCommitment.objects.filter(
                aid_request=aid_request,
                helper=request.user
            ).exists()
            if not has_commitment:
                return Response(
                    {"detail": "You can close only your own in-progress requests."},
                    status=status.HTTP_403_FORBIDDEN
                )

        try:
            result = transition_request(
                request_id=aid_request.id,
                target_status=RequestStatus.CLOSED,
                actor=request.user,
                comment="Заявка закрыта",
            )
        except InvalidRequestTransition:
            return Response(
                {"detail": "Недопустимый переход статуса заявки."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not result.changed:
            return Response(
                {"detail": "Заявка уже закрыта."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Request closed successfully."},
            status=status.HTTP_200_OK
        )

class RequestHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=PolymorphicProxySerializer(
            component_name="RequestHistoryByRole",
            serializers=[
                ApplicantRequestStatusHistorySerializer,
                HelperRequestStatusHistorySerializer,
                ModeratorRequestStatusHistorySerializer,
            ],
            resource_type_field_name=None,
            many=True,
        ),
        summary="История статусов заявки",
    )
    def get(self, request, request_id):
        aid_request = get_object_or_404(AidRequest, id=request_id)

        # Политика доступа к истории:
        # - admin/moderator видят всё
        # - applicant видит только свои заявки
        # - helper видит только заявки, которые он взял
        if request.user.role not in ("admin", "moderator"):
            if request.user.role == "applicant":
                if aid_request.applicant_id != request.user.id:
                    return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
            elif request.user.role == "helper":
                has_commitment = HelpCommitment.objects.filter(
                    aid_request=aid_request,
                    helper=request.user
                ).exists()
                if not has_commitment:
                    return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        qs = RequestStatusHistory.objects.filter(aid_request=aid_request).select_related("changed_by").order_by("-created_at")
        if request.user.role in ("admin", "moderator"):
            serializer_class = ModeratorRequestStatusHistorySerializer
        elif request.user.role == "applicant":
            serializer_class = ApplicantRequestStatusHistorySerializer
        else:
            serializer_class = HelperRequestStatusHistorySerializer

        serializer = serializer_class(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
