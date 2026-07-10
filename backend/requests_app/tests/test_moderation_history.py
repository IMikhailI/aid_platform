from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from fraud.models import FraudAction, FraudDecision, FraudRiskLevel
from requests_app.management.commands.seed_demo_stand import DEMO_MARKER
from requests_app.models import AidRequest, RequestStatus, RequestStatusHistory


User = get_user_model()


class ModerationRequestListTests(APITestCase):
    endpoint = "/api/moderation/requests/"

    def setUp(self):
        self.applicant = User.objects.create_user(
            username="history_applicant",
            email="history-applicant@example.test",
            password="Pass12345!",
            role="applicant",
            region="Сургут",
        )
        self.helper = User.objects.create_user(
            username="history_helper",
            password="Pass12345!",
            role="helper",
            region="Сургут",
        )
        self.moderator = User.objects.create_user(
            username="history_moderator",
            password="Pass12345!",
            role="moderator",
            region="Сургут",
        )
        self.admin = User.objects.create_user(
            username="history_admin",
            password="Pass12345!",
            role="admin",
            region="Сургут",
        )

        self.requests_by_status = {
            status_value: self._create_request(status_value)
            for status_value in (
                RequestStatus.ON_MODERATION,
                RequestStatus.PUBLISHED,
                RequestStatus.IN_PROGRESS,
                RequestStatus.REJECTED,
                RequestStatus.CLOSED,
            )
        }
        self._create_request(RequestStatus.DRAFT)

        reviewed = self.requests_by_status[RequestStatus.PUBLISHED]
        RequestStatusHistory.objects.create(
            aid_request=reviewed,
            old_status=RequestStatus.ON_MODERATION,
            new_status=RequestStatus.PUBLISHED,
            changed_by=self.moderator,
            comment="Approved after document check",
        )
        FraudDecision.objects.create(
            aid_request=reviewed,
            score=28,
            risk_level=FraudRiskLevel.LOW,
            base_action=FraudAction.ALLOW,
            action=FraudAction.ALLOW,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _create_request(self, status_value):
        return AidRequest.objects.create(
            applicant=self.applicant,
            category="food",
            title=f"History request {status_value}",
            description="Private moderation test description",
            region="Сургут",
            requested_amount="2500.00",
            urgency=3,
            status=status_value,
            risk_score=28,
            is_flagged=False,
            device_id_hash="device-secret-hash",
            ip_hash="ip-secret-hash",
            user_agent_hash="agent-secret-hash",
        )

    def _results(self, response):
        return response.data.get("results", response.data)

    def test_moderator_can_list_supported_statuses(self):
        self._auth(self.moderator)

        for status_value, aid_request in self.requests_by_status.items():
            with self.subTest(status=status_value):
                response = self.client.get(self.endpoint, {"status": status_value})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                ids = {item["id"] for item in self._results(response)}
                self.assertIn(aid_request.id, ids)

    def test_admin_can_access_request_history_list(self):
        self._auth(self.admin)
        response = self.client.get(self.endpoint, {"status": RequestStatus.PUBLISHED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_applicant_helper_and_anonymous_are_rejected(self):
        self._auth(self.applicant)
        applicant_response = self.client.get(self.endpoint)

        self._auth(self.helper)
        helper_response = self.client.get(self.endpoint)

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(self.endpoint)

        self.assertEqual(applicant_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(helper_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_status_filter_and_pagination(self):
        self._auth(self.moderator)
        response = self.client.get(
            self.endpoint,
            {"status": RequestStatus.PUBLISHED, "page": 1, "page_size": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], RequestStatus.PUBLISHED)

    def test_comma_separated_status_filter_is_supported(self):
        self._auth(self.moderator)
        response = self.client.get(
            self.endpoint,
            {"status": f"{RequestStatus.PUBLISHED},{RequestStatus.CLOSED}", "page_size": 10},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["status"] for item in self._results(response)},
            {RequestStatus.PUBLISHED, RequestStatus.CLOSED},
        )

    def test_response_fields_are_service_safe(self):
        self._auth(self.moderator)
        response = self.client.get(self.endpoint, {"status": RequestStatus.PUBLISHED})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertEqual(
            set(item),
            {
                "id",
                "title",
                "category",
                "region",
                "requested_amount",
                "urgency",
                "status",
                "risk_score",
                "risk_level",
                "fraud_action",
                "is_flagged",
                "applicant_username",
                "applicant_verification_status",
                "latest_moderation_comment",
                "created_at",
                "updated_at",
            },
        )
        for forbidden in (
            "password",
            "email",
            "device_id_hash",
            "ip_hash",
            "user_agent_hash",
            "traceback",
            "engine_version",
            "reasons",
        ):
            self.assertNotIn(forbidden, item)
        self.assertEqual(item["risk_level"], FraudRiskLevel.LOW)
        self.assertEqual(item["fraud_action"], FraudAction.ALLOW)
        self.assertEqual(item["latest_moderation_comment"], "Approved after document check")

    def test_existing_approve_reject_endpoint_still_uses_transition_flow(self):
        pending = self.requests_by_status[RequestStatus.ON_MODERATION]
        self._auth(self.moderator)
        response = self.client.post(
            f"/api/requests/moderation/{pending.id}/",
            {"action": "reject", "comment": "Not enough detail"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending.refresh_from_db()
        self.assertEqual(pending.status, RequestStatus.REJECTED)
        self.assertTrue(
            RequestStatusHistory.objects.filter(
                aid_request=pending,
                new_status=RequestStatus.REJECTED,
                comment="Not enough detail",
            ).exists()
        )


class ModerationRequestListDemoSeedTests(APITestCase):
    def setUp(self):
        out = StringIO()
        call_command("seed_demo_stand", stdout=out)
        self.moderator = User.objects.get(username="moderator_demo")

    def _auth(self):
        self.client.force_authenticate(user=self.moderator)

    def _titles(self, response):
        return {item["title"] for item in response.data.get("results", response.data)}

    def test_demo_seed_requests_are_visible_in_history_endpoint(self):
        self._auth()

        on_moderation = self.client.get(
            "/api/moderation/requests/",
            {"status": RequestStatus.ON_MODERATION, "page_size": 50},
        )
        published = self.client.get(
            "/api/moderation/requests/",
            {"status": RequestStatus.PUBLISHED, "page_size": 50},
        )
        rejected = self.client.get(
            "/api/moderation/requests/",
            {"status": RequestStatus.REJECTED, "page_size": 50},
        )

        self.assertEqual(on_moderation.status_code, status.HTTP_200_OK)
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)

        self.assertTrue(any(f"{DEMO_MARKER} request_pending_allow:" in title for title in self._titles(on_moderation)))
        self.assertTrue(any(f"{DEMO_MARKER} request_published:" in title for title in self._titles(published)))
        self.assertTrue(any(f"{DEMO_MARKER} request_rejected:" in title for title in self._titles(rejected)))
