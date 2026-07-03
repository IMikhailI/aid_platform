from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from requests_app.models import (
    AidFulfillment, AidRequest, FulfillmentStatus, HelpCommitment,
    RequestStatus, RequestStatusHistory,
)
from requests_app.services.fulfillment import (
    FulfillmentNotFound, FulfillmentStateConflict, FulfillmentValidationError,
    confirm_certificate_received, create_mock_certificate, mark_certificate_delivered,
)
from requests_app.services.transitions import InvalidRequestTransition


User = get_user_model()


def make_request(applicant, request_status=RequestStatus.IN_PROGRESS):
    return AidRequest.objects.create(
        applicant=applicant, category="food", title="Fulfillment fixture",
        description="Targeted aid test", region="Test region",
        requested_amount="2500.00", urgency=3, status=request_status,
    )


class AidFulfillmentModelAndServiceTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="fulfill_applicant", role="applicant")
        self.helper = User.objects.create_user(username="fulfill_helper", role="helper")
        self.other_helper = User.objects.create_user(username="fulfill_other_helper", role="helper")
        self.aid_request = make_request(self.applicant)
        self.commitment = HelpCommitment.objects.create(
            aid_request=self.aid_request, helper=self.helper, method="certificate"
        )

    def create(self, **overrides):
        values = {
            "request_id": self.aid_request.id,
            "helper": self.helper,
            "provider_name": "  Mock Provider  ",
            "amount": self.aid_request.requested_amount,
            **overrides,
        }
        return create_mock_certificate(**values)

    def test_one_to_one_unique_code_and_server_fields(self):
        fulfillment = self.create()
        self.assertEqual(fulfillment.provider_name, "Mock Provider")
        self.assertTrue(fulfillment.certificate_code)
        self.assertEqual(fulfillment.created_by, self.helper)
        second_request = make_request(self.applicant)
        HelpCommitment.objects.create(
            aid_request=second_request, helper=self.helper, method="certificate"
        )
        second = create_mock_certificate(
            request_id=second_request.id, helper=self.helper,
            provider_name="Mock", amount="1.00",
        )
        self.assertNotEqual(fulfillment.certificate_code, second.certificate_code)
        with self.assertRaises(FulfillmentStateConflict):
            self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AidFulfillment.objects.create(
                commitment=self.commitment, provider_name="Other", amount="1.00",
                created_by=self.helper,
            )

    def test_database_rejects_zero_and_negative_amount(self):
        for amount in ("0.00", "-1.00"):
            with self.subTest(amount=amount), self.assertRaises(IntegrityError), transaction.atomic():
                AidFulfillment.objects.create(
                    commitment=self.commitment, provider_name="Mock", amount=amount,
                    created_by=self.helper,
                )

    def test_service_rejects_invalid_provider_and_amount(self):
        for provider in ("", "   "):
            with self.subTest(provider=repr(provider)), self.assertRaises(FulfillmentValidationError):
                self.create(provider_name=provider)
        for amount in ("0.00", "-1.00", "2500.01"):
            with self.subTest(amount=amount), self.assertRaises(FulfillmentValidationError):
                self.create(amount=amount)

    def test_create_requires_owner_and_in_progress_request(self):
        with self.assertRaises(FulfillmentNotFound):
            self.create(helper=self.other_helper)
        self.aid_request.status = RequestStatus.CLOSED
        self.aid_request.save(update_fields=["status"])
        with self.assertRaises(FulfillmentStateConflict):
            self.create()

    def test_deliver_changes_only_fulfillment(self):
        fulfillment = self.create()
        history_before = RequestStatusHistory.objects.filter(aid_request=self.aid_request).count()
        delivered = mark_certificate_delivered(
            request_id=self.aid_request.id, helper=self.helper
        )
        self.aid_request.refresh_from_db()
        self.assertEqual(delivered.status, FulfillmentStatus.DELIVERED)
        self.assertIsNotNone(delivered.delivered_at)
        self.assertEqual(self.aid_request.status, RequestStatus.IN_PROGRESS)
        self.assertEqual(RequestStatusHistory.objects.filter(aid_request=self.aid_request).count(), history_before)
        with self.assertRaises(FulfillmentStateConflict):
            mark_certificate_delivered(request_id=self.aid_request.id, helper=self.helper)

    def test_confirm_closes_once_with_applicant_actor(self):
        fulfillment = self.create()
        mark_certificate_delivered(request_id=self.aid_request.id, helper=self.helper)
        confirmed = confirm_certificate_received(
            request_id=self.aid_request.id, applicant=self.applicant
        )
        self.aid_request.refresh_from_db()
        self.assertEqual(confirmed.status, FulfillmentStatus.CONFIRMED)
        self.assertIsNotNone(confirmed.confirmed_at)
        self.assertEqual(self.aid_request.status, RequestStatus.CLOSED)
        history = RequestStatusHistory.objects.get(
            aid_request=self.aid_request, new_status=RequestStatus.CLOSED
        )
        self.assertEqual(history.changed_by, self.applicant)
        with self.assertRaises(FulfillmentStateConflict):
            confirm_certificate_received(request_id=self.aid_request.id, applicant=self.applicant)
        self.assertEqual(RequestStatusHistory.objects.filter(aid_request=self.aid_request, new_status=RequestStatus.CLOSED).count(), 1)

    def test_created_cannot_be_confirmed_and_foreign_applicant_cannot_confirm(self):
        self.create()
        other = User.objects.create_user(username="foreign_applicant", role="applicant")
        with self.assertRaises(FulfillmentStateConflict):
            confirm_certificate_received(request_id=self.aid_request.id, applicant=self.applicant)
        with self.assertRaises(FulfillmentNotFound):
            confirm_certificate_received(request_id=self.aid_request.id, applicant=other)

    def test_transition_failure_rolls_back_confirmed_status(self):
        fulfillment = self.create()
        mark_certificate_delivered(request_id=self.aid_request.id, helper=self.helper)
        with patch(
            "requests_app.services.fulfillment.transition_request",
            side_effect=InvalidRequestTransition(
                current_status=RequestStatus.IN_PROGRESS,
                target_status=RequestStatus.CLOSED,
            ),
        ), self.assertRaises(FulfillmentStateConflict):
            confirm_certificate_received(request_id=self.aid_request.id, applicant=self.applicant)
        fulfillment.refresh_from_db()
        self.aid_request.refresh_from_db()
        self.assertEqual(fulfillment.status, FulfillmentStatus.DELIVERED)
        self.assertEqual(self.aid_request.status, RequestStatus.IN_PROGRESS)


class FulfillmentApiTests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="api_fulfill_applicant", role="applicant")
        self.other_applicant = User.objects.create_user(username="api_fulfill_other_applicant", role="applicant")
        self.helper = User.objects.create_user(username="api_fulfill_helper", role="helper")
        self.other_helper = User.objects.create_user(username="api_fulfill_other_helper", role="helper")
        self.moderator = User.objects.create_user(username="api_fulfill_moderator", role="moderator")
        self.admin = User.objects.create_user(username="api_fulfill_admin", role="admin")
        self.aid_request = make_request(self.applicant)
        self.commitment = HelpCommitment.objects.create(
            aid_request=self.aid_request, helper=self.helper, method="certificate"
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def create_fulfillment(self, extra=None):
        self.auth(self.helper)
        return self.client.post(
            f"/api/helper/requests/{self.aid_request.id}/fulfillment/",
            {"provider_name": "Mock Provider", "amount": "2500.00", **(extra or {})},
            format="json",
        )

    def deliver(self, user=None):
        self.auth(user or self.helper)
        return self.client.post(
            f"/api/helper/requests/{self.aid_request.id}/fulfillment/deliver/", {}, format="json"
        )

    def test_helper_create_get_masks_code_and_ignores_client_controlled_fields(self):
        response = self.create_fulfillment(
            {"certificate_code": "00000000-0000-0000-0000-000000000000", "status": "confirmed"}
        )
        get_response = self.client.get(f"/api/helper/requests/{self.aid_request.id}/fulfillment/")
        fulfillment = AidFulfillment.objects.get(commitment=self.commitment)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(get_response.status_code, 200)
        self.assertNotIn("certificate_code", response.data)
        self.assertTrue(response.data["masked_certificate_code"].endswith(str(fulfillment.certificate_code)[-4:]))
        self.assertNotEqual(str(fulfillment.certificate_code), "00000000-0000-0000-0000-000000000000")
        self.assertEqual(fulfillment.status, FulfillmentStatus.CREATED)

    def test_create_before_take_foreign_closed_and_duplicate_are_rejected(self):
        no_take = make_request(self.applicant)
        self.auth(self.helper)
        self.assertEqual(self.client.post(
            f"/api/helper/requests/{no_take.id}/fulfillment/",
            {"provider_name": "Mock", "amount": "1.00"}, format="json"
        ).status_code, 404)
        self.auth(self.other_helper)
        self.assertEqual(self.client.post(
            f"/api/helper/requests/{self.aid_request.id}/fulfillment/",
            {"provider_name": "Mock", "amount": "1.00"}, format="json"
        ).status_code, 404)
        self.aid_request.status = RequestStatus.CLOSED
        self.aid_request.save(update_fields=["status"])
        self.assertEqual(self.create_fulfillment().status_code, 409)
        self.aid_request.status = RequestStatus.IN_PROGRESS
        self.aid_request.save(update_fields=["status"])
        self.assertEqual(self.create_fulfillment().status_code, 201)
        self.assertEqual(self.create_fulfillment().status_code, 409)

    def test_deliver_permissions_repeat_and_lifecycle(self):
        self.create_fulfillment()
        history_before = RequestStatusHistory.objects.filter(aid_request=self.aid_request).count()
        self.assertEqual(self.deliver(user=self.other_helper).status_code, 404)
        self.auth(self.applicant)
        self.assertEqual(self.client.post(
            f"/api/helper/requests/{self.aid_request.id}/fulfillment/deliver/"
        ).status_code, 403)
        delivered = self.deliver()
        repeated = self.deliver()
        self.aid_request.refresh_from_db()
        self.assertEqual(delivered.status_code, 200)
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(self.aid_request.status, RequestStatus.IN_PROGRESS)
        self.assertEqual(RequestStatusHistory.objects.filter(aid_request=self.aid_request).count(), history_before)

    def test_applicant_code_visibility_and_ownership(self):
        self.create_fulfillment()
        self.auth(self.applicant)
        created_response = self.client.get(f"/api/applicant/requests/{self.aid_request.id}/fulfillment/")
        self.assertNotIn("certificate_code", created_response.data)
        self.assertNotIn("helper_username", created_response.data)
        self.auth(self.other_applicant)
        self.assertEqual(self.client.get(f"/api/applicant/requests/{self.aid_request.id}/fulfillment/").status_code, 404)
        self.deliver()
        self.auth(self.applicant)
        delivered_response = self.client.get(f"/api/applicant/requests/{self.aid_request.id}/fulfillment/")
        self.assertIn("certificate_code", delivered_response.data)
        self.assertEqual(delivered_response.data["certificate_code"], str(self.commitment.fulfillment.certificate_code))

    def test_confirm_receipt_and_deprecated_alias(self):
        self.create_fulfillment()
        self.deliver()
        self.auth(self.helper)
        self.assertEqual(self.client.post(f"/api/applicant/requests/{self.aid_request.id}/confirm-receipt/").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/requests/close/{self.aid_request.id}/", {}).status_code, 403)
        self.auth(self.applicant)
        response = self.client.post(f"/api/applicant/requests/{self.aid_request.id}/confirm-receipt/", {}, format="json")
        repeated = self.client.post(f"/api/applicant/requests/{self.aid_request.id}/confirm-receipt/", {}, format="json")
        self.aid_request.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"request_status": "closed", "fulfillment_status": "confirmed"})
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(self.aid_request.status, RequestStatus.CLOSED)

    def test_deprecated_alias_uses_same_confirmation_service(self):
        self.create_fulfillment()
        self.deliver()
        self.auth(self.applicant)
        response = self.client.patch(f"/api/requests/close/{self.aid_request.id}/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.aid_request.refresh_from_db()
        self.assertEqual(self.aid_request.status, RequestStatus.CLOSED)

    def test_moderator_and_admin_read_full_contract_but_cannot_mutate(self):
        self.create_fulfillment()
        for user in (self.moderator, self.admin):
            with self.subTest(role=user.role):
                self.auth(user)
                response = self.client.get(f"/api/moderation/requests/{self.aid_request.id}/fulfillment/")
                self.assertEqual(response.status_code, 200)
                self.assertIn("certificate_code", response.data)
                self.assertIn("helper_username", response.data)
                self.assertIn("applicant_username", response.data)
        for user in (self.helper, self.applicant):
            self.auth(user)
            self.assertEqual(self.client.get(f"/api/moderation/requests/{self.aid_request.id}/fulfillment/").status_code, 403)

    def test_foreign_helper_anonymous_and_role_specific_privacy(self):
        self.create_fulfillment()
        self.auth(self.other_helper)
        self.assertEqual(self.client.get(f"/api/helper/requests/{self.aid_request.id}/fulfillment/").status_code, 404)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(f"/api/helper/requests/{self.aid_request.id}/fulfillment/").status_code, 401)

    def test_existing_request_responses_do_not_leak_fulfillment(self):
        published = make_request(self.applicant, RequestStatus.PUBLISHED)
        self.auth(self.helper)
        published_response = self.client.get("/api/requests/published/")
        take_target = make_request(self.applicant, RequestStatus.PUBLISHED)
        take_response = self.client.post(
            f"/api/requests/helper/take/{take_target.id}/",
            {"method": "certificate"}, format="json",
        )
        self.auth(self.applicant)
        own_response = self.client.get("/api/requests/applicant/my/")
        forbidden = {"certificate_code", "fulfillment", "created_by", "helper", "helper_username"}
        for payload in (published_response.data, take_response.data, own_response.data):
            self.assertNotIn("certificate_code", str(payload))
            if isinstance(payload, dict) and "results" not in payload:
                self.assertFalse(forbidden.intersection(payload))
