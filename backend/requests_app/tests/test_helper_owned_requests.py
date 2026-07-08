from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from requests_app.fulfillment_serializers import mask_certificate_code
from requests_app.models import (
    AidFulfillment, AidRequest, FulfillmentStatus, HelpCommitment, RequestStatus,
)


User = get_user_model()
URL = "/api/helper/my-help/"


class HelperOwnedRequestsApiTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="owned_applicant", email="applicant@example.test",
            role="applicant", region="Test region",
        )
        self.helper = User.objects.create_user(username="owned_helper", role="helper")
        self.other_helper = User.objects.create_user(username="owned_other_helper", role="helper")
        self.moderator = User.objects.create_user(username="owned_moderator", role="moderator")
        self.admin = User.objects.create_user(username="owned_admin", role="admin")
        self.aid_request = self.make_request("Own request")
        self.commitment = HelpCommitment.objects.create(
            aid_request=self.aid_request, helper=self.helper,
            method="certificate", note="Safe helper note",
        )
        foreign_request = self.make_request("Foreign request")
        self.foreign_commitment = HelpCommitment.objects.create(
            aid_request=foreign_request, helper=self.other_helper, method="cart",
        )

    def make_request(self, title):
        return AidRequest.objects.create(
            applicant=self.applicant, category="food", title=title,
            description="Private applicant description", region="Test region",
            requested_amount="2500.00", urgency=3,
            status=RequestStatus.IN_PROGRESS, risk_score=88, is_flagged=True,
            device_id_hash="device-secret", ip_hash="ip-secret",
            user_agent_hash="agent-secret",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def own_item(self):
        self.auth(self.helper)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response, response.data["results"][0]

    def create_fulfillment(self, fulfillment_status=FulfillmentStatus.CREATED):
        return AidFulfillment.objects.create(
            commitment=self.commitment, provider_name="Mock Provider",
            amount="2000.00", status=fulfillment_status, created_by=self.helper,
        )

    def test_helper_sees_only_own_commitment_with_explicit_safe_fields(self):
        response, item = self.own_item()
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(item["request_id"], self.aid_request.id)
        self.assertEqual(item["title"], "Own request")
        self.assertEqual(item["commitment_method"], "certificate")
        self.assertEqual(item["commitment_note"], "Safe helper note")
        self.assertNotEqual(item["request_id"], self.foreign_commitment.aid_request_id)
        self.assertEqual(
            set(item),
            {
                "request_id", "title", "category", "region", "requested_amount",
                "urgency", "request_status", "created_at", "taken_at",
                "commitment_method", "commitment_note", "fulfillment_status",
                "fulfillment_type", "provider_name", "fulfillment_amount",
                "masked_certificate_code", "delivered_at", "confirmed_at",
            },
        )

    def test_response_excludes_identity_fraud_verification_and_telemetry(self):
        _, item = self.own_item()
        forbidden = {
            "applicant", "applicant_id", "applicant_username", "email",
            "helper_email", "risk_score", "risk_level", "is_flagged", "fraud",
            "fraud_reasons", "verification_status", "household_size",
            "dependents_count", "review_comment", "certificate_code",
            "device_hash", "device_id_hash", "ip_hash", "user_agent_hash",
        }
        self.assertFalse(forbidden.intersection(item))
        serialized = str(item)
        for secret in ("owned_applicant", "applicant@example.test", "device-secret", "ip-secret", "agent-secret"):
            self.assertNotIn(secret, serialized)

    def test_endpoint_is_helper_only(self):
        for user in (self.applicant, self.moderator, self.admin):
            with self.subTest(role=user.role):
                self.auth(user)
                self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_without_fulfillment_returns_none_and_null_summary(self):
        _, item = self.own_item()
        self.assertEqual(item["fulfillment_status"], "none")
        for field in (
            "fulfillment_type", "provider_name", "fulfillment_amount",
            "masked_certificate_code", "delivered_at", "confirmed_at",
        ):
            self.assertIsNone(item[field])

    def test_created_fulfillment_returns_masked_code_and_safe_summary(self):
        fulfillment = self.create_fulfillment()
        _, item = self.own_item()
        self.assertEqual(item["fulfillment_status"], "created")
        self.assertEqual(item["provider_name"], "Mock Provider")
        self.assertEqual(item["fulfillment_amount"], "2000.00")
        self.assertEqual(item["masked_certificate_code"], mask_certificate_code(fulfillment.certificate_code))
        self.assertNotIn(str(fulfillment.certificate_code), str(item))
        self.assertNotIn("certificate_code", item)

    def test_delivered_and_confirmed_statuses_are_returned(self):
        fulfillment = self.create_fulfillment(FulfillmentStatus.DELIVERED)
        _, item = self.own_item()
        self.assertEqual(item["fulfillment_status"], "delivered")
        fulfillment.status = FulfillmentStatus.CONFIRMED
        fulfillment.save(update_fields=["status"])
        _, item = self.own_item()
        self.assertEqual(item["fulfillment_status"], "confirmed")

    def test_pagination_uses_project_page_shape_and_page_size(self):
        for index in range(11):
            request = self.make_request(f"Pagination request {index}")
            HelpCommitment.objects.create(
                aid_request=request, helper=self.helper, method="certificate"
            )
        self.auth(self.helper)
        response = self.client.get(URL, {"page": 1, "page_size": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 12)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_select_related_keeps_list_query_count_constant(self):
        for index in range(3):
            request = self.make_request(f"Query request {index}")
            commitment = HelpCommitment.objects.create(
                aid_request=request, helper=self.helper, method="certificate"
            )
            AidFulfillment.objects.create(
                commitment=commitment, provider_name="Provider", amount="10.00",
                created_by=self.helper,
            )
        self.auth(self.helper)
        with self.assertNumQueries(2):
            response = self.client.get(URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data["results"]), 4)
