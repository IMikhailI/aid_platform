from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from requests_app.models import AidRequest, RequestStatus
from fraud.models import FraudDecision, FraudAction


class FraudRecheckAndFilterTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="app1", password="Pass12345!", role="applicant", region="Berlin"
        )
        self.moderator = User.objects.create_user(
            username="mod1", password="Pass12345!", role="moderator", region="Berlin"
        )
        self.helper = User.objects.create_user(
            username="help1", password="Pass12345!", role="helper", region="Berlin"
        )

        category_field = AidRequest._meta.get_field("category")
        category_choices = category_field.choices or []
        category_value = category_choices[0][0] if category_choices else "other"

        urgency_field = AidRequest._meta.get_field("urgency")
        urgency_choices = urgency_field.choices or []
        urgency_value = urgency_choices[0][0] if urgency_choices else 1

        self.req = AidRequest.objects.create(
            applicant=self.applicant,
            title="Need support",
            description="desc",
            category=category_value,
            urgency=urgency_value,
            region="Berlin",
            status=RequestStatus.ON_MODERATION,
            risk_score=10,
            is_flagged=False,
        )

        self.decision = FraudDecision.objects.create(
            aid_request=self.req,
            score=60,
            risk_level="high",
            action=FraudAction.MANUAL_REVIEW,
            reasons=[{"code": "BURST_CREATION", "weight": 20}],
            engine_version="rules-v1",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_moderator_can_get_decision(self):
        self.auth(self.moderator)
        url = f"/api/fraud/requests/{self.req.id}/decision/"
        resp = self.client.get(url)
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            getattr(resp, "data", resp.content.decode()),
        )
        self.assertEqual(resp.data["score"], 60)

    def test_non_moderator_forbidden(self):
        self.auth(self.helper)
        url = f"/api/fraud/requests/{self.req.id}/decision/"
        resp = self.client.get(url)
        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            getattr(resp, "data", resp.content.decode()),
        )

    def test_override_creates_audit_record_and_updates_action(self):
        self.auth(self.moderator)
        url = f"/api/fraud/requests/{self.req.id}/override/"
        resp = self.client.post(
            url,
            {"new_action": FraudAction.ALLOW, "comment": "Manual verification passed"},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_201_CREATED,
            getattr(resp, "data", resp.content.decode()),
        )

        self.decision.refresh_from_db()
        self.assertEqual(self.decision.action, FraudAction.ALLOW)

    def test_recheck_forbidden_for_non_moderator(self):
        self.auth(self.helper)
        resp = self.client.post(f"/api/fraud/requests/{self.req.id}/recheck/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_recheck_ok_for_moderator(self):
        self.auth(self.moderator)
        resp = self.client.post(f"/api/fraud/requests/{self.req.id}/recheck/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, getattr(resp, "data", resp.content.decode()))
        self.assertIn("score", resp.data)
        self.assertIn("action", resp.data)
