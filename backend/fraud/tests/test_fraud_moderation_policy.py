from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from fraud.models import FraudAction, FraudDecision, FraudOverride
from fraud.services.engine import evaluate_request
from fraud.services.policy import (
    FraudPolicyViolation,
    FraudPublicationPolicyResult,
    assert_request_can_be_published,
    evaluate_publication_policy,
)
from requests_app.models import AidRequest, RequestStatus, RequestStatusHistory


User = get_user_model()


class FraudPublicationPolicyTests(TestCase):
    def setUp(self):
        applicant = User.objects.create_user(username="policy_applicant", role="applicant")
        self.aid_request = AidRequest.objects.create(
            applicant=applicant,
            category="food",
            title="Policy fixture",
            description="Policy fixture description",
            region="Test region",
            urgency=3,
            status=RequestStatus.ON_MODERATION,
        )

    def decision(self, action):
        return FraudDecision(
            aid_request=self.aid_request,
            base_action=FraudAction.BLOCK,
            action=action,
        )

    def test_policy_uses_effective_action(self):
        self.assertEqual(
            evaluate_publication_policy(self.decision(FraudAction.ALLOW)),
            FraudPublicationPolicyResult.ALLOWED,
        )
        self.assertEqual(
            evaluate_publication_policy(self.decision(FraudAction.MANUAL_REVIEW)),
            FraudPublicationPolicyResult.ALLOWED,
        )
        self.assertEqual(
            evaluate_publication_policy(self.decision(FraudAction.BLOCK)),
            FraudPublicationPolicyResult.BLOCKED,
        )

    def test_policy_distinguishes_missing_decision(self):
        self.assertEqual(
            evaluate_publication_policy(None),
            FraudPublicationPolicyResult.DECISION_MISSING,
        )
        with self.assertRaises(FraudPolicyViolation) as raised:
            assert_request_can_be_published(None)
        self.assertEqual(raised.exception.code, "fraud_decision_missing")


class FraudModerationPolicyApiTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="fm_applicant", role="applicant")
        self.helper = User.objects.create_user(username="fm_helper", role="helper")
        self.moderator = User.objects.create_user(username="fm_moderator", role="moderator")
        self.admin = User.objects.create_user(username="fm_admin", role="admin")

    def make_request(self):
        return AidRequest.objects.create(
            applicant=self.applicant,
            category="food",
            title="Moderation fixture",
            description="Moderation policy fixture",
            region="Test region",
            urgency=3,
            status=RequestStatus.ON_MODERATION,
        )

    def make_decision(self, aid_request, action, *, base_action=None, overridden=False):
        return FraudDecision.objects.create(
            aid_request=aid_request,
            score=80 if (base_action or action) == FraudAction.BLOCK else 10,
            risk_level="critical" if (base_action or action) == FraudAction.BLOCK else "low",
            base_action=base_action or action,
            action=action,
            is_overridden=overridden,
            reasons=[],
            engine_version="policy-test",
        )

    def moderate(self, aid_request, action, user=None):
        self.client.force_authenticate(user=user or self.moderator)
        return self.client.post(
            f"/api/requests/moderation/{aid_request.id}/",
            {"action": action, "comment": "Reviewed"},
            format="json",
        )

    def override(self, aid_request, action, comment="Manual verification passed", user=None):
        self.client.force_authenticate(user=user or self.moderator)
        return self.client.post(
            f"/api/fraud/requests/{aid_request.id}/override/",
            {"new_action": action, "comment": comment},
            format="json",
        )

    def test_allow_decision_can_be_approved(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.ALLOW)
        response = self.moderate(aid_request, "approve")

        aid_request.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(aid_request.status, RequestStatus.PUBLISHED)

    def test_manual_review_decision_can_be_approved(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.MANUAL_REVIEW)
        response = self.moderate(aid_request, "approve", user=self.admin)

        aid_request.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(aid_request.status, RequestStatus.PUBLISHED)

    def test_block_decision_prevents_approve_without_status_or_history_change(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.BLOCK)
        history_before = RequestStatusHistory.objects.filter(aid_request=aid_request).count()
        response = self.moderate(aid_request, "approve")

        aid_request.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "fraud_publication_blocked")
        self.assertEqual(aid_request.status, RequestStatus.ON_MODERATION)
        self.assertEqual(
            RequestStatusHistory.objects.filter(aid_request=aid_request).count(),
            history_before,
        )

    def test_missing_decision_prevents_approve_without_status_or_history_change(self):
        aid_request = self.make_request()
        response = self.moderate(aid_request, "approve")

        aid_request.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "fraud_decision_missing")
        self.assertEqual(aid_request.status, RequestStatus.ON_MODERATION)
        self.assertFalse(RequestStatusHistory.objects.filter(aid_request=aid_request).exists())

    def test_reject_is_allowed_for_block_and_missing_decision(self):
        blocked = self.make_request()
        self.make_decision(blocked, FraudAction.BLOCK)
        missing = self.make_request()

        for aid_request in (blocked, missing):
            with self.subTest(request_id=aid_request.id):
                response = self.moderate(aid_request, "reject")
                aid_request.refresh_from_db()
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(aid_request.status, RequestStatus.REJECTED)
                self.assertEqual(
                    RequestStatusHistory.objects.filter(
                        aid_request=aid_request,
                        new_status=RequestStatus.REJECTED,
                    ).count(),
                    1,
                )

    def test_override_from_base_block_to_allow_or_review_permits_approve(self):
        for effective_action in (FraudAction.ALLOW, FraudAction.MANUAL_REVIEW):
            with self.subTest(effective_action=effective_action):
                aid_request = self.make_request()
                decision = self.make_decision(aid_request, FraudAction.BLOCK)
                override_response = self.override(aid_request, effective_action)
                approve_response = self.moderate(aid_request, "approve")

                decision.refresh_from_db()
                aid_request.refresh_from_db()
                self.assertEqual(override_response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
                self.assertEqual(decision.base_action, FraudAction.BLOCK)
                self.assertEqual(decision.action, effective_action)
                self.assertEqual(aid_request.status, RequestStatus.PUBLISHED)

    def test_override_that_keeps_effective_block_still_prevents_approve(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.BLOCK)
        self.assertEqual(self.override(aid_request, FraudAction.BLOCK).status_code, 201)
        self.assertEqual(self.moderate(aid_request, "approve").status_code, 409)

    def test_override_is_trimmed_audited_and_preserves_lifecycle(self):
        aid_request = self.make_request()
        decision = self.make_decision(aid_request, FraudAction.BLOCK)
        response = self.override(aid_request, FraudAction.ALLOW, "  verified manually  ")

        decision.refresh_from_db()
        aid_request.refresh_from_db()
        override = FraudOverride.objects.get(aid_request=aid_request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(decision.base_action, FraudAction.BLOCK)
        self.assertEqual(decision.action, FraudAction.ALLOW)
        self.assertTrue(decision.is_overridden)
        self.assertEqual(override.old_action, FraudAction.BLOCK)
        self.assertEqual(override.new_action, FraudAction.ALLOW)
        self.assertEqual(override.comment, "verified manually")
        self.assertEqual(override.changed_by, self.moderator)
        self.assertEqual(aid_request.status, RequestStatus.ON_MODERATION)
        self.assertFalse(RequestStatusHistory.objects.filter(aid_request=aid_request).exists())

    def test_override_rejects_empty_or_whitespace_reason(self):
        for comment in ("", "   "):
            with self.subTest(comment=repr(comment)):
                aid_request = self.make_request()
                self.make_decision(aid_request, FraudAction.BLOCK)
                response = self.override(aid_request, FraudAction.ALLOW, comment)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertFalse(FraudOverride.objects.filter(aid_request=aid_request).exists())

    def test_applicant_and_helper_cannot_moderate_override_or_recheck(self):
        for user in (self.applicant, self.helper):
            with self.subTest(role=user.role):
                aid_request = self.make_request()
                self.make_decision(aid_request, FraudAction.BLOCK)
                self.assertEqual(self.moderate(aid_request, "approve", user=user).status_code, 403)
                self.assertEqual(self.override(aid_request, FraudAction.ALLOW, user=user).status_code, 403)
                self.client.force_authenticate(user=user)
                response = self.client.post(f"/api/fraud/requests/{aid_request.id}/recheck/")
                self.assertEqual(response.status_code, 403)

    def test_repeated_approve_creates_no_additional_history(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.ALLOW)
        first = self.moderate(aid_request, "approve")
        second = self.moderate(aid_request, "approve")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            RequestStatusHistory.objects.filter(
                aid_request=aid_request,
                new_status=RequestStatus.PUBLISHED,
            ).count(),
            1,
        )

    def test_approve_and_override_use_row_locks(self):
        aid_request = self.make_request()
        self.make_decision(aid_request, FraudAction.ALLOW)
        with patch(
            "requests_app.views.AidRequest.objects.select_for_update",
            wraps=AidRequest.objects.select_for_update,
        ) as request_lock, patch(
            "requests_app.views.FraudDecision.objects.select_for_update",
            wraps=FraudDecision.objects.select_for_update,
        ) as decision_lock:
            response = self.moderate(aid_request, "approve")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        request_lock.assert_called()
        decision_lock.assert_called_once()

        another_request = self.make_request()
        self.make_decision(another_request, FraudAction.BLOCK)
        with patch(
            "fraud.api.views.FraudDecision.objects.select_for_update",
            wraps=FraudDecision.objects.select_for_update,
        ) as override_lock:
            response = self.override(another_request, FraudAction.ALLOW)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        override_lock.assert_called_once()

    def test_recheck_without_override_updates_effective_action_from_base(self):
        aid_request = self.make_request()
        decision = self.make_decision(aid_request, FraudAction.BLOCK, overridden=False)
        evaluate_request(aid_request)

        decision.refresh_from_db()
        self.assertEqual(decision.action, decision.base_action)
        self.assertFalse(decision.is_overridden)

    def test_recheck_with_override_preserves_effective_action_and_lifecycle(self):
        aid_request = self.make_request()
        decision = self.make_decision(
            aid_request,
            FraudAction.BLOCK,
            base_action=FraudAction.ALLOW,
            overridden=True,
        )
        history_before = RequestStatusHistory.objects.filter(aid_request=aid_request).count()
        evaluate_request(aid_request)

        aid_request.refresh_from_db()
        decision.refresh_from_db()
        self.assertEqual(decision.action, FraudAction.BLOCK)
        self.assertTrue(decision.is_overridden)
        self.assertEqual(aid_request.status, RequestStatus.ON_MODERATION)
        self.assertEqual(
            RequestStatusHistory.objects.filter(aid_request=aid_request).count(),
            history_before,
        )
