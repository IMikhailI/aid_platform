from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from requests_app.models import (
    AidFulfillment, AidRequest, FulfillmentStatus, HelpCommitment,
    RequestStatus, RequestStatusHistory,
)
from requests_app.admin import AidRequestAdmin
from requests_app.services.transitions import InvalidRequestTransition, transition_request
from fraud.models import FraudAction, FraudDecision


User = get_user_model()


def make_request(*, applicant, request_status):
    return AidRequest.objects.create(
        applicant=applicant,
        category="food",
        title=f"State fixture {request_status}",
        description="State machine test fixture",
        region="Test region",
        requested_amount="1000.00",
        urgency=3,
        status=request_status,
    )


class RequestTransitionServiceTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="state_applicant", role="applicant")
        self.helper = User.objects.create_user(username="state_helper", role="helper")
        self.moderator = User.objects.create_user(username="state_moderator", role="moderator")

    def assert_transition(self, source, target, actor):
        aid_request = make_request(applicant=self.applicant, request_status=source)
        result = transition_request(
            request_id=aid_request.id,
            target_status=target,
            actor=actor,
            comment="Expected transition",
        )

        aid_request.refresh_from_db()
        self.assertTrue(result.changed)
        self.assertEqual(aid_request.status, target)
        history = RequestStatusHistory.objects.get(aid_request=aid_request)
        self.assertEqual(history.old_status, source)
        self.assertEqual(history.new_status, target)
        self.assertEqual(history.changed_by, actor)

    def test_draft_to_on_moderation_is_allowed(self):
        self.assert_transition(RequestStatus.DRAFT, RequestStatus.ON_MODERATION, self.applicant)

    def test_on_moderation_to_published_is_allowed(self):
        self.assert_transition(RequestStatus.ON_MODERATION, RequestStatus.PUBLISHED, self.moderator)

    def test_on_moderation_to_rejected_is_allowed(self):
        self.assert_transition(RequestStatus.ON_MODERATION, RequestStatus.REJECTED, self.moderator)

    def test_published_to_in_progress_is_allowed(self):
        self.assert_transition(RequestStatus.PUBLISHED, RequestStatus.IN_PROGRESS, self.helper)

    def test_in_progress_to_closed_is_allowed(self):
        self.assert_transition(RequestStatus.IN_PROGRESS, RequestStatus.CLOSED, self.helper)

    def test_on_moderation_to_closed_is_forbidden(self):
        self.assert_failed_transition(RequestStatus.ON_MODERATION, RequestStatus.CLOSED)

    def test_published_to_rejected_is_forbidden(self):
        self.assert_failed_transition(RequestStatus.PUBLISHED, RequestStatus.REJECTED)

    def assert_failed_transition(self, source, target):
        aid_request = make_request(applicant=self.applicant, request_status=source)
        with self.assertRaises(InvalidRequestTransition):
            transition_request(
                request_id=aid_request.id,
                target_status=target,
                actor=self.moderator,
                comment="Must not be persisted",
            )

        aid_request.refresh_from_db()
        self.assertEqual(aid_request.status, source)
        self.assertFalse(RequestStatusHistory.objects.filter(aid_request=aid_request).exists())

    def test_closed_is_terminal(self):
        for target in (
            RequestStatus.DRAFT,
            RequestStatus.ON_MODERATION,
            RequestStatus.PUBLISHED,
            RequestStatus.IN_PROGRESS,
            RequestStatus.REJECTED,
        ):
            with self.subTest(target=target):
                self.assert_failed_transition(RequestStatus.CLOSED, target)

    def test_rejected_is_terminal(self):
        for target in (
            RequestStatus.DRAFT,
            RequestStatus.ON_MODERATION,
            RequestStatus.PUBLISHED,
            RequestStatus.IN_PROGRESS,
            RequestStatus.CLOSED,
        ):
            with self.subTest(target=target):
                self.assert_failed_transition(RequestStatus.REJECTED, target)

    def test_same_status_is_noop_without_duplicate_history(self):
        aid_request = make_request(
            applicant=self.applicant,
            request_status=RequestStatus.ON_MODERATION,
        )

        result = transition_request(
            request_id=aid_request.id,
            target_status=RequestStatus.ON_MODERATION,
            actor=self.moderator,
            comment="No-op",
        )

        self.assertFalse(result.changed)
        self.assertFalse(RequestStatusHistory.objects.filter(aid_request=aid_request).exists())

    def test_successful_transition_creates_exactly_one_history_event(self):
        aid_request = make_request(
            applicant=self.applicant,
            request_status=RequestStatus.ON_MODERATION,
        )
        transition_request(
            request_id=aid_request.id,
            target_status=RequestStatus.PUBLISHED,
            actor=self.moderator,
            comment="Single event",
        )

        self.assertEqual(RequestStatusHistory.objects.filter(aid_request=aid_request).count(), 1)

    def test_admin_cannot_add_or_directly_edit_status(self):
        model_admin = AidRequestAdmin(AidRequest, AdminSite())

        self.assertIn("status", model_admin.get_readonly_fields(request=None))
        self.assertFalse(model_admin.has_add_permission(request=None))


class RequestTransitionApiTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="api_state_applicant", role="applicant")
        self.helper = User.objects.create_user(username="api_state_helper", role="helper")
        self.moderator = User.objects.create_user(username="api_state_moderator", role="moderator")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_approve_uses_transition_service(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.ON_MODERATION)
        FraudDecision.objects.create(
            aid_request=aid_request,
            base_action=FraudAction.ALLOW,
            action=FraudAction.ALLOW,
        )
        self.auth(self.moderator)
        with patch("requests_app.views.transition_request", wraps=transition_request) as service:
            response = self.client.post(
                f"/api/requests/moderation/{aid_request.id}/",
                {"action": "approve", "comment": "Approved"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.assert_called_once()
        self.assertTrue(
            RequestStatusHistory.objects.filter(
                aid_request=aid_request,
                new_status=RequestStatus.PUBLISHED,
            ).exists()
        )

    def test_reject_uses_transition_service(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.ON_MODERATION)
        self.auth(self.moderator)
        with patch("requests_app.views.transition_request", wraps=transition_request) as service:
            response = self.client.post(
                f"/api/requests/moderation/{aid_request.id}/",
                {"action": "reject", "comment": "Rejected"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.assert_called_once()

    def test_take_uses_transition_service(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.PUBLISHED)
        self.auth(self.helper)
        with patch("requests_app.views.transition_request", wraps=transition_request) as service:
            response = self.client.post(
                f"/api/requests/helper/take/{aid_request.id}/",
                {"method": "certificate", "note": "Taken"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.assert_called_once()
        self.assertTrue(HelpCommitment.objects.filter(aid_request=aid_request, helper=self.helper).exists())

    def test_close_uses_transition_service(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.IN_PROGRESS)
        commitment = HelpCommitment.objects.create(aid_request=aid_request, helper=self.helper, method="certificate")
        AidFulfillment.objects.create(
            commitment=commitment, provider_name="Mock", amount="100.00",
            created_by=self.helper, status=FulfillmentStatus.DELIVERED,
        )
        self.auth(self.applicant)
        with patch("requests_app.services.fulfillment.transition_request", wraps=transition_request) as service:
            response = self.client.patch(f"/api/requests/close/{aid_request.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.assert_called_once()

    def test_repeated_take_creates_no_duplicate_commitment_or_history(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.PUBLISHED)
        self.auth(self.helper)
        first = self.client.post(
            f"/api/requests/helper/take/{aid_request.id}/",
            {"method": "certificate"},
            format="json",
        )
        second = self.client.post(
            f"/api/requests/helper/take/{aid_request.id}/",
            {"method": "certificate"},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(HelpCommitment.objects.filter(aid_request=aid_request).count(), 1)
        self.assertEqual(
            RequestStatusHistory.objects.filter(
                aid_request=aid_request,
                new_status=RequestStatus.IN_PROGRESS,
            ).count(),
            1,
        )

    def test_repeated_close_creates_no_duplicate_history(self):
        aid_request = make_request(applicant=self.applicant, request_status=RequestStatus.IN_PROGRESS)
        commitment = HelpCommitment.objects.create(aid_request=aid_request, helper=self.helper, method="certificate")
        AidFulfillment.objects.create(
            commitment=commitment, provider_name="Mock", amount="100.00",
            created_by=self.helper, status=FulfillmentStatus.DELIVERED,
        )
        self.auth(self.applicant)
        first = self.client.patch(f"/api/requests/close/{aid_request.id}/", {}, format="json")
        second = self.client.patch(f"/api/requests/close/{aid_request.id}/", {}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            RequestStatusHistory.objects.filter(
                aid_request=aid_request,
                new_status=RequestStatus.CLOSED,
            ).count(),
            1,
        )

    def test_repeated_moderation_actions_create_no_duplicate_history(self):
        self.auth(self.moderator)
        for action, target in (
            ("approve", RequestStatus.PUBLISHED),
            ("reject", RequestStatus.REJECTED),
        ):
            aid_request = make_request(
                applicant=self.applicant,
                request_status=RequestStatus.ON_MODERATION,
            )
            if action == "approve":
                FraudDecision.objects.create(
                    aid_request=aid_request,
                    base_action=FraudAction.ALLOW,
                    action=FraudAction.ALLOW,
                )
            first = self.client.post(
                f"/api/requests/moderation/{aid_request.id}/",
                {"action": action},
                format="json",
            )
            second = self.client.post(
                f"/api/requests/moderation/{aid_request.id}/",
                {"action": action},
                format="json",
            )

            self.assertEqual(first.status_code, status.HTTP_200_OK)
            self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                RequestStatusHistory.objects.filter(
                    aid_request=aid_request,
                    new_status=target,
                ).count(),
                1,
            )


class FraudRecheckStatusPreservationTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="fraud_state_applicant", role="applicant")
        self.moderator = User.objects.create_user(username="fraud_state_moderator", role="moderator")
        self.client.force_authenticate(user=self.moderator)

    def assert_recheck_preserves_status(self, request_status):
        aid_request = make_request(applicant=self.applicant, request_status=request_status)
        response = self.client.post(f"/api/fraud/requests/{aid_request.id}/recheck/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aid_request.refresh_from_db()
        self.assertEqual(aid_request.status, request_status)

    def test_recheck_preserves_published_status(self):
        self.assert_recheck_preserves_status(RequestStatus.PUBLISHED)

    def test_recheck_preserves_in_progress_status(self):
        self.assert_recheck_preserves_status(RequestStatus.IN_PROGRESS)

    def test_recheck_preserves_closed_status(self):
        self.assert_recheck_preserves_status(RequestStatus.CLOSED)
