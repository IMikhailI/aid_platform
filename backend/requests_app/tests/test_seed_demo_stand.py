from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from fraud.models import FraudAction
from moderation.models import ApplicantVerification, VerificationStatus
from requests_app.management.commands.seed_demo_stand import DEMO_MARKER
from requests_app.models import (
    AidFulfillment,
    AidRequest,
    FulfillmentStatus,
    RequestStatus,
    RequestStatusHistory,
)
from users.models import ApplicantProfile, UserRole


User = get_user_model()


def run_seed(*args):
    out = StringIO()
    call_command("seed_demo_stand", *args, stdout=out)
    return out.getvalue()


def demo_request(slug):
    return AidRequest.objects.get(title__startswith=f"{DEMO_MARKER} {slug}:")


class SeedDemoStandCommandTests(TestCase):
    def test_seed_demo_stand_creates_users_profiles_verifications_and_requests(self):
        output = run_seed()

        self.assertIn("Demo stand data is ready", output)
        expected_roles = {
            "applicant_demo": UserRole.APPLICANT,
            "helper_demo": UserRole.HELPER,
            "moderator_demo": UserRole.MODERATOR,
            "admin_demo": UserRole.ADMIN,
            "applicant_pending_demo": UserRole.APPLICANT,
            "applicant_rejected_demo": UserRole.APPLICANT,
        }
        for username, role in expected_roles.items():
            with self.subTest(username=username):
                user = User.objects.get(username=username)
                self.assertEqual(user.role, role)
                self.assertEqual(user.region, "Сургут")

        admin = User.objects.get(username="admin_demo")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

        profile = ApplicantProfile.objects.get(user__username="applicant_demo")
        self.assertEqual(profile.household_size, 3)
        self.assertEqual(profile.dependents_count, 1)
        self.assertTrue(profile.consent_to_data_processing)

        self.assertTrue(
            ApplicantVerification.objects.filter(
                profile__user__username="applicant_demo",
                status=VerificationStatus.VERIFIED,
                reviewed_by__username="moderator_demo",
            ).exists()
        )
        self.assertTrue(
            ApplicantVerification.objects.filter(
                profile__user__username="applicant_pending_demo",
                status=VerificationStatus.PENDING,
            ).exists()
        )
        self.assertTrue(
            ApplicantVerification.objects.filter(
                profile__user__username="applicant_rejected_demo",
                status=VerificationStatus.REJECTED,
                reviewed_by__username="moderator_demo",
            ).exists()
        )

        expected_statuses = {
            "request_pending_allow": RequestStatus.ON_MODERATION,
            "request_pending_manual_review": RequestStatus.ON_MODERATION,
            "request_pending_block": RequestStatus.ON_MODERATION,
            "request_published": RequestStatus.PUBLISHED,
            "request_in_progress": RequestStatus.IN_PROGRESS,
            "request_fulfillment_created": RequestStatus.IN_PROGRESS,
            "request_fulfillment_delivered": RequestStatus.IN_PROGRESS,
            "request_closed": RequestStatus.CLOSED,
            "request_rejected": RequestStatus.REJECTED,
        }
        for slug, request_status in expected_statuses.items():
            with self.subTest(slug=slug):
                self.assertEqual(demo_request(slug).status, request_status)

        block_decision = demo_request("request_pending_block").fraud_decision
        self.assertEqual(block_decision.action, FraudAction.BLOCK)
        self.assertTrue(block_decision.reasons)
        self.assertTrue(block_decision.aid_request.fraud_checks.exists())

        self.assertEqual(
            demo_request("request_pending_allow").fraud_decision.action,
            FraudAction.ALLOW,
        )
        self.assertEqual(
            demo_request("request_pending_manual_review").fraud_decision.action,
            FraudAction.MANUAL_REVIEW,
        )

        self.assertTrue(hasattr(demo_request("request_in_progress"), "commitment"))
        self.assertFalse(
            AidFulfillment.objects.filter(
                commitment__aid_request=demo_request("request_in_progress")
            ).exists()
        )
        self.assertEqual(
            demo_request("request_fulfillment_created").commitment.fulfillment.status,
            FulfillmentStatus.CREATED,
        )
        self.assertEqual(
            demo_request("request_fulfillment_delivered").commitment.fulfillment.status,
            FulfillmentStatus.DELIVERED,
        )
        closed_request = demo_request("request_closed")
        self.assertEqual(closed_request.commitment.fulfillment.status, FulfillmentStatus.CONFIRMED)
        self.assertTrue(
            RequestStatusHistory.objects.filter(
                aid_request=closed_request,
                old_status=RequestStatus.IN_PROGRESS,
                new_status=RequestStatus.CLOSED,
            ).exists()
        )

    def test_repeated_seed_does_not_create_duplicate_users_or_requests(self):
        run_seed()
        first_user_count = User.objects.filter(username__endswith="_demo").count()
        first_request_count = AidRequest.objects.filter(title__startswith=DEMO_MARKER).count()
        first_verification_count = ApplicantVerification.objects.count()

        run_seed()

        self.assertEqual(User.objects.filter(username__endswith="_demo").count(), first_user_count)
        self.assertEqual(
            AidRequest.objects.filter(title__startswith=DEMO_MARKER).count(),
            first_request_count,
        )
        self.assertEqual(ApplicantVerification.objects.count(), first_verification_count)

    def test_reset_demo_passwords_updates_existing_demo_passwords(self):
        User.objects.create_user(
            username="applicant_demo",
            password="custom-password",
            role=UserRole.APPLICANT,
            region="Custom",
        )

        run_seed()
        user = User.objects.get(username="applicant_demo")
        self.assertTrue(user.check_password("custom-password"))
        self.assertFalse(user.check_password("applicant123"))

        run_seed("--reset-demo-passwords")
        user.refresh_from_db()
        self.assertTrue(user.check_password("applicant123"))

    def test_reset_demo_data_deletes_only_marked_demo_records(self):
        non_demo_applicant = User.objects.create_user(
            username="regular_applicant",
            role=UserRole.APPLICANT,
            region="Сургут",
        )
        non_demo_request = AidRequest.objects.create(
            applicant=non_demo_applicant,
            category="food",
            title="Non-demo request",
            description="Must survive demo reset",
            region="Сургут",
            requested_amount="100.00",
            urgency=1,
            status=RequestStatus.ON_MODERATION,
        )

        run_seed()
        first_ids = set(
            AidRequest.objects.filter(title__startswith=DEMO_MARKER).values_list("id", flat=True)
        )
        run_seed("--reset-demo-data")
        second_ids = set(
            AidRequest.objects.filter(title__startswith=DEMO_MARKER).values_list("id", flat=True)
        )

        self.assertEqual(len(second_ids), 9)
        self.assertNotEqual(first_ids, second_ids)
        self.assertTrue(AidRequest.objects.filter(id=non_demo_request.id).exists())


class SeedDemoStandApiSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        run_seed()

    def auth(self, username):
        self.client.force_authenticate(user=User.objects.get(username=username))

    def results(self, response):
        return response.data.get("results", response.data)

    def test_helper_my_help_sees_owned_demo_in_progress_and_fulfillment_requests(self):
        self.auth("helper_demo")
        response = self.client.get("/api/helper/my-help/", {"page_size": 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = self.results(response)
        titles = {item["title"] for item in items}
        self.assertTrue(any("request_in_progress" in title for title in titles))
        self.assertTrue(any("request_fulfillment_created" in title for title in titles))
        self.assertTrue(any("request_fulfillment_delivered" in title for title in titles))
        self.assertIn("created", {item["fulfillment_status"] for item in items})
        self.assertIn("delivered", {item["fulfillment_status"] for item in items})
        self.assertIn("confirmed", {item["fulfillment_status"] for item in items})

    def test_helper_published_feed_sees_published_demo_request(self):
        self.auth("helper_demo")
        response = self.client.get("/api/requests/published/", {"page_size": 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["title"] for item in self.results(response)}
        self.assertTrue(any("request_published" in title for title in titles))

    def test_moderator_queue_sees_pending_and_block_demo_requests(self):
        self.auth("moderator_demo")
        response = self.client.get("/api/requests/moderation/queue/", {"page_size": 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["title"] for item in self.results(response)}
        self.assertTrue(any("request_pending_allow" in title for title in titles))
        self.assertTrue(any("request_pending_block" in title for title in titles))

        block = demo_request("request_pending_block")
        approve = self.client.post(
            f"/api/requests/moderation/{block.id}/",
            {"action": "approve", "comment": "Demo approve should be blocked"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_409_CONFLICT)

    def test_applicant_own_list_and_history_include_closed_request(self):
        self.auth("applicant_demo")
        closed = demo_request("request_closed")

        own_response = self.client.get("/api/requests/applicant/my/")
        history_response = self.client.get(f"/api/requests/{closed.id}/history/")

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertIn(closed.id, {item["id"] for item in self.results(own_response)})
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(
                item["from_status"] == RequestStatus.IN_PROGRESS
                and item["to_status"] == RequestStatus.CLOSED
                for item in history_response.data
            )
        )

    def test_helper_responses_do_not_leak_private_fields_or_full_certificate_code(self):
        self.auth("helper_demo")
        response = self.client.get("/api/helper/my-help/", {"page_size": 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        forbidden = {
            "applicant",
            "applicant_id",
            "applicant_username",
            "email",
            "risk_score",
            "is_flagged",
            "fraud_decision",
            "verification_status",
            "certificate_code",
            "device_id_hash",
            "ip_hash",
            "user_agent_hash",
        }
        for item in self.results(response):
            self.assertFalse(forbidden.intersection(item))

        fulfillment = AidFulfillment.objects.get(
            commitment__aid_request=demo_request("request_fulfillment_delivered")
        )
        self.assertNotIn(str(fulfillment.certificate_code), str(response.data))

    def test_applicant_can_confirm_delivered_fulfillment(self):
        self.auth("applicant_demo")
        delivered = demo_request("request_fulfillment_delivered")

        response = self.client.post(
            f"/api/applicant/requests/{delivered.id}/confirm-receipt/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivered.refresh_from_db()
        self.assertEqual(delivered.status, RequestStatus.CLOSED)
        self.assertEqual(delivered.commitment.fulfillment.status, FulfillmentStatus.CONFIRMED)
