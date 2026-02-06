from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AidRequest, RequestStatus, RequestStatusHistory, HelpCommitment
from .permissions import IsApplicant, IsModerator, IsHelper
from .serializers import (
    AidRequestCreateSerializer,
    AidRequestListSerializer,
    ModerationActionSerializer,
    HelpCommitSerializer,
)


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

    def get_queryset(self):
        qs = AidRequest.objects.filter(status=RequestStatus.PUBLISHED)
        region = self.request.query_params.get("region")
        category = self.request.query_params.get("category")
        if region:
            qs = qs.filter(region__iexact=region)
        if category:
            qs = qs.filter(category=category)
        return qs


class ModerationQueueView(generics.ListAPIView):
    serializer_class = AidRequestListSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator]

    def get_queryset(self):
        return AidRequest.objects.filter(status=RequestStatus.ON_MODERATION)


class ModerateRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsModerator]

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

class CloseRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, request_id: int):
        try:
            obj = AidRequest.objects.select_for_update().get(id=request_id)
        except AidRequest.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=404)

        if obj.status != RequestStatus.IN_PROGRESS:
            return Response({"detail": "Закрыть можно только заявку в работе"}, status=400)

        # закрыть может helper, который взял заявку, или admin
        is_admin = getattr(request.user, "role", "") == "admin"
        is_owner_helper = hasattr(obj, "commitment") and obj.commitment.helper_id == request.user.id
        if not (is_admin or is_owner_helper):
            return Response({"detail": "Недостаточно прав"}, status=403)

        old = obj.status
        obj.status = RequestStatus.CLOSED
        obj.save(update_fields=["status", "updated_at"])

        RequestStatusHistory.objects.create(
            aid_request=obj,
            old_status=old,
            new_status=obj.status,
            changed_by=request.user,
            comment="Заявка закрыта",
        )
        return Response({"id": obj.id, "new_status": obj.status}, status=200)


class RequestHistoryView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, request_id: int):
        try:
            obj = AidRequest.objects.get(id=request_id)
        except AidRequest.DoesNotExist:
            return Response({"detail": "Заявка не найдена"}, status=404)

        # права: автор заявки, назначенный helper, moderator/admin
        is_applicant = obj.applicant_id == request.user.id
        is_helper = hasattr(obj, "commitment") and obj.commitment.helper_id == request.user.id
        is_mod_admin = request.user.role in ("moderator", "admin")

        if not (is_applicant or is_helper or is_mod_admin):
            return Response({"detail": "Недостаточно прав"}, status=403)

        history = obj.status_history.all().values(
            "old_status", "new_status", "comment", "created_at", "changed_by_id"
        )
        return Response(list(history), status=200)

