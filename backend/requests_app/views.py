from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import AidRequest, RequestStatus, RequestStatusHistory, HelpCommitment
from .permissions import IsApplicant, IsModerator, IsHelper, CanCloseRequest
from .serializers import (
    AidRequestCreateSerializer,
    AidRequestListSerializer,
    ModerationActionSerializer,
    HelpCommitSerializer,
    RequestStatusHistorySerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse

class DefaultPagePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ApplicantCreateRequestView(generics.CreateAPIView):
    serializer_class = AidRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

class ApplicantOwnRequestsView(generics.ListAPIView):
    serializer_class = AidRequestListSerializer
    permission_classes = [permissions.IsAuthenticated, IsApplicant]

    def get_queryset(self):
        return AidRequest.objects.filter(applicant=self.request.user)

class PublicPublishedRequestsView(generics.ListAPIView):
    serializer_class = AidRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DefaultPagePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category"]  # region лучше через кастом, чтобы iexact
    search_fields = ["title", "description", "region"]
    ordering_fields = ["created_at", "risk_score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AidRequest.objects.filter(status=RequestStatus.PUBLISHED)

        # region case-insensitive exact
        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region__iexact=region)

        return qs

class ModerationQueueView(generics.ListAPIView):
    serializer_class = AidRequestListSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator]
    pagination_class = DefaultPagePagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category"]
    search_fields = ["title", "description", "region"]
    ordering_fields = ["created_at", "risk_score"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = AidRequest.objects.filter(status=RequestStatus.ON_MODERATION)

        region = self.request.query_params.get("region")
        if region:
            qs = qs.filter(region__iexact=region)

        return qs

class ModerateRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    @extend_schema(
        request=ModerationActionSerializer,
        responses={
            200: OpenApiResponse(description="Заявка обработана"),
            400: OpenApiResponse(description="Ошибка валидации"),
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

        try:
            obj = AidRequest.objects.select_for_update().get(id=request_id)
        except AidRequest.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=404)

        if obj.status != RequestStatus.ON_MODERATION:
            return Response({"detail": "Заявка не в статусе модерации"}, status=400)

        old = obj.status
        action = serializer.validated_data["action"]
        comment = serializer.validated_data.get("comment", "")

        if action == "approve":
            obj.status = RequestStatus.PUBLISHED
        else:
            obj.status = RequestStatus.REJECTED

        obj.save(update_fields=["status", "updated_at"])

        RequestStatusHistory.objects.create(
            aid_request=obj,
            old_status=old,
            new_status=obj.status,
            changed_by=request.user,
            comment=comment,
        )
        return Response({"id": obj.id, "new_status": obj.status}, status=200)


class TakeRequestIntoWorkView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHelper]
    
    @extend_schema(
        request=HelpCommitSerializer,
        responses={
            200: OpenApiResponse(description="Заявка взята в работу"),
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

        if obj.status != RequestStatus.PUBLISHED:
            return Response({"detail": "Можно взять только опубликованную заявку"}, status=400)

        if hasattr(obj, "commitment"):
            return Response({"detail": "Заявка уже взята в работу"}, status=400)

        HelpCommitment.objects.create(
            aid_request=obj,
            helper=request.user,
            method=serializer.validated_data["method"],
            note=serializer.validated_data.get("note", ""),
        )

        old = obj.status
        obj.status = RequestStatus.IN_PROGRESS
        obj.save(update_fields=["status", "updated_at"])

        RequestStatusHistory.objects.create(
            aid_request=obj,
            old_status=old,
            new_status=obj.status,
            changed_by=request.user,
            comment="Заявка взята в работу",
        )
        return Response({"id": obj.id, "new_status": obj.status}, status=200)

@extend_schema(
    summary="Закрыть заявку",
    description="Закрывает заявку в статусе in_progress. Доступно admin или helper, который взял заявку в работу.",
    responses={
        200: OpenApiResponse(description="Заявка успешно закрыта"),
        400: OpenApiResponse(description="Нельзя закрыть заявку в текущем статусе"),
        403: OpenApiResponse(description="Недостаточно прав"),
        404: OpenApiResponse(description="Заявка не найдена"),
    },
)
class CloseRequestView(APIView):
    permission_classes = [IsAuthenticated, CanCloseRequest]

    @transaction.atomic
    def patch(self, request, request_id):
        aid_request = get_object_or_404(
            AidRequest.objects.select_for_update(),
            id=request_id
        )

        # 1) Проверка допустимого текущего статуса
        if aid_request.status != RequestStatus.IN_PROGRESS:
            return Response(
                {"detail": "Only in_progress requests can be closed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) helper — может закрыть только свою взятую заявку
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

        # 3) Закрытие
        aid_request.status = RequestStatus.CLOSED
        aid_request.save(update_fields=["status"])

        RequestStatusHistory.objects.create(
            aid_request=aid_request,
            old_status=RequestStatus.IN_PROGRESS,
            new_status=RequestStatus.CLOSED,
            changed_by=request.user,
            comment="Заявка закрыта",
        )


        return Response(
            {"detail": "Request closed successfully."},
            status=status.HTTP_200_OK
        )

class RequestHistoryView(APIView):
    permission_classes = [IsAuthenticated]

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

        qs = RequestStatusHistory.objects.filter(aid_request=aid_request).select_related("changed_by").order_by("-changed_at")
        serializer = RequestStatusHistorySerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

