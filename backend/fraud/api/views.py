from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from requests_app.models import AidRequest
from fraud.models import FraudDecision, FraudCheck, FraudOverride
from fraud.services.engine import evaluate_request_safe
from .permissions import IsModeratorOrAdmin
from .serializers import (
    FraudDecisionSerializer,
    FraudCheckSerializer,
    FraudOverrideSerializer,
    FraudOverrideCreateSerializer,
)


class FraudDecisionView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, request_id: int):
        aid_request = get_object_or_404(AidRequest, id=request_id)
        decision = get_object_or_404(FraudDecision, aid_request=aid_request)
        return Response(FraudDecisionSerializer(decision).data, status=status.HTTP_200_OK)


class FraudChecksView(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = FraudCheckSerializer

    def get_queryset(self):
        request_id = self.kwargs["request_id"]
        aid_request = get_object_or_404(AidRequest, id=request_id)
        return FraudCheck.objects.filter(aid_request=aid_request).order_by("-created_at")


class FraudOverrideView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    @transaction.atomic
    def post(self, request, request_id: int):
        aid_request = get_object_or_404(AidRequest, id=request_id)
        decision = get_object_or_404(FraudDecision, aid_request=aid_request)

        serializer = FraudOverrideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_action = decision.action
        new_action = serializer.validated_data["new_action"]
        comment = serializer.validated_data["comment"]

        decision.action = new_action
        decision.is_overridden = True
        decision.save(update_fields=["action", "is_overridden", "decided_at"])

        override = FraudOverride.objects.create(
            aid_request=aid_request,
            old_action=old_action,
            new_action=new_action,
            comment=comment,
            changed_by=request.user,
        )

        return Response(FraudOverrideSerializer(override).data, status=status.HTTP_201_CREATED)


class FraudRecheckView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, request_id: int):
        aid_request = get_object_or_404(AidRequest, id=request_id)
        decision = evaluate_request_safe(aid_request)

        if decision is None:
            return Response(
                {"detail": "Fraud recheck failed; request kept on manual moderation."},
                status=status.HTTP_200_OK,
            )

        return Response(FraudDecisionSerializer(decision).data, status=status.HTTP_200_OK)
