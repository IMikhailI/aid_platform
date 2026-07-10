from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from fraud.models import FraudAction, FraudCheck, FraudDecision
from requests_app.models import AidRequest, HelpCommitment, RequestStatus, RequestStatusHistory
from requests_app.services.transitions import transition_request


User = get_user_model()


FORBIDDEN_EXTERNAL_KEYS = {
    "applicant",
    "applicant_id",
    "applicant_username",
    "username",
    "email",
    "risk_score",
    "risk_level",
    "is_flagged",
    "fraud",
    "fraud_checks",
    "fraud_decision",
    "reasons",
    "action",
    "base_action",
    "is_overridden",
    "changed_by",
    "changed_by_username",
    "changed_by_role",
    "device_hash",
    "device_id_hash",
    "ip_hash",
    "user_agent_hash",
}


class PrivacyApiContractTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="privacy_applicant",
            email="applicant@example.test",
            password="Pass12345!",
            role="applicant",
            region="Berlin",
        )
        self.other_applicant = User.objects.create_user(
            username="other_applicant",
            email="other@example.test",
            password="Pass12345!",
            role="applicant",
            region="Berlin",
        )
        self.helper = User.objects.create_user(
            username="privacy_helper", password="Pass12345!", role="helper", region="Berlin"
        )
        self.moderator = User.objects.create_user(
            username="privacy_moderator", password="Pass12345!", role="moderator", region="Berlin"
        )
        self.admin = User.objects.create_user(
            username="privacy_admin", password="Pass12345!", role="admin", region="Berlin"
        )

        self.published_request = self._create_request(
            applicant=self.applicant,
            title="Public aid request",
            status_value=RequestStatus.PUBLISHED,
        )
        self.foreign_request = self._create_request(
            applicant=self.other_applicant,
            title="Another public request",
            status_value=RequestStatus.PUBLISHED,
        )
        self.moderation_request = self._create_request(
            applicant=self.applicant,
            title="Request awaiting moderation",
            status_value=RequestStatus.ON_MODERATION,
        )

        self._add_fraud_data(self.published_request)
        self._add_fraud_data(self.moderation_request)

        RequestStatusHistory.objects.create(
            aid_request=self.published_request,
            old_status="",
            new_status=RequestStatus.ON_MODERATION,
            changed_by=self.applicant,
            comment="Applicant identity must stay private",
        )
        RequestStatusHistory.objects.create(
            aid_request=self.published_request,
            old_status=RequestStatus.ON_MODERATION,
            new_status=RequestStatus.PUBLISHED,
            changed_by=self.moderator,
            comment="Internal moderator comment",
        )

    def _create_request(self, *, applicant, title, status_value):
        return AidRequest.objects.create(
            applicant=applicant,
            category="food",
            title=title,
            description="Description must not expose service metadata",
            region="Berlin",
            requested_amount="2500.00",
            urgency=3,
            status=status_value,
            risk_score=82,
            is_flagged=True,
            device_id_hash="device-internal-hash",
            ip_hash="ip-internal-hash",
            user_agent_hash="agent-internal-hash",
        )

    def _add_fraud_data(self, aid_request):
        FraudDecision.objects.create(
            aid_request=aid_request,
            score=82,
            risk_level="critical",
            base_action=FraudAction.BLOCK,
            action=FraudAction.BLOCK,
            reasons=[{"code": "INTERNAL_SIGNAL", "weight": 82}],
            engine_version="privacy-test",
        )
        FraudCheck.objects.create(
            aid_request=aid_request,
            signal_code="INTERNAL_SIGNAL",
            weight=82,
            value={"internal": True},
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _results(self, response):
        return response.data.get("results", response.data)

    def assert_forbidden_keys_absent(self, payload):
        if isinstance(payload, dict):
            leaked = FORBIDDEN_EXTERNAL_KEYS.intersection(payload.keys())
            self.assertFalse(leaked, f"Forbidden API keys leaked: {sorted(leaked)}")
            for value in payload.values():
                self.assert_forbidden_keys_absent(value)
        elif isinstance(payload, list):
            for value in payload:
                self.assert_forbidden_keys_absent(value)

    def test_helper_published_list_is_anonymized(self):
        self._auth(self.helper)
        response = self.client.get(
            "/api/requests/published/",
            {"ordering": "risk_score"},
        )
        hidden_description_search = self.client.get(
            "/api/requests/published/",
            {"search": "private"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_forbidden_keys_absent(response.data)
        self.assertTrue(self._results(response))
        for item in self._results(response):
            self.assertEqual(
                set(item),
                {"id", "title", "category", "region", "requested_amount", "urgency", "status", "created_at"},
            )
        self.assertEqual(hidden_description_search.status_code, status.HTTP_200_OK)
        self.assertEqual(self._results(hidden_description_search), [])

    def test_helper_take_response_is_anonymized(self):
        self._auth(self.helper)
        response = self.client.post(
            f"/api/requests/helper/take/{self.published_request.id}/",
            {"method": "certificate", "note": "Safe note"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], RequestStatus.IN_PROGRESS)
        self.assert_forbidden_keys_absent(response.data)

    def test_helper_history_is_anonymized(self):
        HelpCommitment.objects.create(
            aid_request=self.published_request,
            helper=self.helper,
            method="certificate",
        )
        self._auth(self.helper)
        response = self.client.get(f"/api/requests/{self.published_request.id}/history/")
        foreign_response = self.client.get(f"/api/requests/{self.foreign_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_forbidden_keys_absent(response.data)
        for item in response.data:
            self.assertEqual(set(item), {"from_status", "to_status", "changed_at"})
        self.assertEqual(foreign_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_close_response_is_safe(self):
        transition_request(
            request_id=self.published_request.id,
            target_status=RequestStatus.IN_PROGRESS,
            actor=self.helper,
            comment="Privacy test setup",
        )
        HelpCommitment.objects.create(
            aid_request=self.published_request,
            helper=self.helper,
            method="certificate",
        )
        self._auth(self.helper)
        response = self.client.patch(f"/api/requests/close/{self.published_request.id}/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_forbidden_keys_absent(response.data)
        self.published_request.refresh_from_db()
        self.assertEqual(self.published_request.status, RequestStatus.IN_PROGRESS)

    def test_applicant_create_response_hides_fraud_and_telemetry(self):
        self._auth(self.applicant)
        response = self.client.post(
            "/api/requests/applicant/create/",
            {
                "category": "food",
                "title": "New private request",
                "description": "Applicant-visible description",
                "region": "Berlin",
                "requested_amount": "1200.00",
                "urgency": 2,
            },
            format="json",
            HTTP_X_DEVICE_ID="private-device",
            REMOTE_ADDR="10.10.10.10",
            HTTP_USER_AGENT="privacy-test-agent",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assert_forbidden_keys_absent(response.data)

    def test_applicant_own_list_hides_internal_fields_and_foreign_requests(self):
        self._auth(self.applicant)
        response = self.client.get("/api/requests/applicant/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_forbidden_keys_absent(response.data)
        request_ids = {item["id"] for item in self._results(response)}
        self.assertIn(self.published_request.id, request_ids)
        self.assertNotIn(self.foreign_request.id, request_ids)

    def test_applicant_history_is_safe_and_foreign_history_is_forbidden(self):
        self._auth(self.applicant)
        own_response = self.client.get(f"/api/requests/{self.published_request.id}/history/")
        foreign_response = self.client.get(f"/api/requests/{self.foreign_request.id}/history/")

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assert_forbidden_keys_absent(own_response.data)
        self.assertEqual(foreign_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_cannot_access_moderation_queue(self):
        self._auth(self.helper)
        response = self.client.get("/api/requests/moderation/queue/")
        history_response = self.client.get("/api/moderation/requests/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(history_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_applicant_and_helper_cannot_cross_role_list_endpoints(self):
        self._auth(self.helper)
        applicant_list_response = self.client.get("/api/requests/applicant/my/")

        self._auth(self.applicant)
        helper_list_response = self.client.get("/api/requests/published/")
        moderation_history_response = self.client.get("/api/moderation/requests/")

        self.assertEqual(applicant_list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(helper_list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(moderation_history_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_applicant_and_helper_cannot_access_any_fraud_endpoint(self):
        endpoints = [
            ("get", f"/api/fraud/requests/{self.published_request.id}/decision/", None),
            ("get", f"/api/fraud/requests/{self.published_request.id}/checks/", None),
            (
                "post",
                f"/api/fraud/requests/{self.published_request.id}/override/",
                {"new_action": FraudAction.ALLOW, "comment": "Forbidden"},
            ),
            ("post", f"/api/fraud/requests/{self.published_request.id}/recheck/", {}),
        ]

        for user in (self.applicant, self.helper):
            self._auth(user)
            for method, url, payload in endpoints:
                response = getattr(self.client, method)(url, payload or {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, (user.role, method, url))

    def test_moderator_retains_applicant_fraud_and_full_history_access(self):
        self._auth(self.moderator)
        queue_response = self.client.get("/api/requests/moderation/queue/")
        decision_response = self.client.get(
            f"/api/fraud/requests/{self.moderation_request.id}/decision/"
        )
        history_response = self.client.get(f"/api/requests/{self.published_request.id}/history/")

        self.assertEqual(queue_response.status_code, status.HTTP_200_OK)
        queue_item = next(
            item for item in self._results(queue_response) if item["id"] == self.moderation_request.id
        )
        self.assertEqual(queue_item["applicant_username"], self.applicant.username)
        self.assertIn("risk_score", queue_item)
        self.assertIn("is_flagged", queue_item)

        self.assertEqual(decision_response.status_code, status.HTTP_200_OK)
        self.assertIn("risk_level", decision_response.data)
        self.assertIn("reasons", decision_response.data)

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertIn("changed_by_username", history_response.data[0])
        self.assertIn("comment", history_response.data[0])

    def test_admin_retains_moderation_and_fraud_access(self):
        self._auth(self.admin)
        queue_response = self.client.get("/api/requests/moderation/queue/")
        decision_response = self.client.get(
            f"/api/fraud/requests/{self.moderation_request.id}/decision/"
        )

        self.assertEqual(queue_response.status_code, status.HTTP_200_OK)
        self.assertEqual(decision_response.status_code, status.HTTP_200_OK)

    def test_anonymous_user_is_rejected_by_protected_endpoints(self):
        self.client.force_authenticate(user=None)
        published_response = self.client.get("/api/requests/published/")
        history_response = self.client.get(f"/api/requests/{self.published_request.id}/history/")
        moderation_history_response = self.client.get("/api/moderation/requests/")

        self.assertEqual(published_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(history_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(moderation_history_response.status_code, status.HTTP_401_UNAUTHORIZED)
