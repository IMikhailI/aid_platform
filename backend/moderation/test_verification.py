from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from moderation.models import ApplicantVerification, VerificationStatus
from moderation.services import (
    VerificationStateConflict,
    VerificationValidationError,
    review_verification,
    submit_verification,
)
from requests_app.models import AidRequest, RequestStatus, RequestStatusHistory
from users.models import ApplicantProfile


User = get_user_model()


def make_profile(*, username="verification_applicant", region="Test region", consent=True):
    user = User.objects.create_user(username=username, role="applicant", region=region)
    return ApplicantProfile.objects.create(user=user, consent_to_data_processing=consent)


class ApplicantProfileModelTests(TestCase):
    def test_user_cannot_have_two_profiles(self):
        profile = make_profile()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ApplicantProfile.objects.create(user=profile.user)

    def test_household_size_must_be_positive(self):
        profile = make_profile()
        profile.household_size = 0
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_dependents_cannot_exceed_household(self):
        profile = make_profile()
        profile.household_size = 2
        profile.dependents_count = 3
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_is_only_valid_for_applicant(self):
        helper = User.objects.create_user(username="profile_helper", role="helper")
        profile = ApplicantProfile(user=helper)
        with self.assertRaises(ValidationError):
            profile.full_clean()


class VerificationServiceTests(TestCase):
    def setUp(self):
        self.profile = make_profile()
        self.moderator = User.objects.create_user(username="service_moderator", role="moderator")

    def test_submit_requires_consent(self):
        self.profile.consent_to_data_processing = False
        self.profile.save(update_fields=["consent_to_data_processing"])
        with self.assertRaises(VerificationValidationError):
            submit_verification(profile=self.profile)

    def test_submit_requires_region(self):
        self.profile.user.region = "   "
        self.profile.user.save(update_fields=["region"])
        with self.assertRaises(VerificationValidationError):
            submit_verification(profile=self.profile)

    def test_submit_creates_pending_and_prevents_second_pending(self):
        verification = submit_verification(profile=self.profile)
        self.assertEqual(verification.status, VerificationStatus.PENDING)
        with self.assertRaises(VerificationStateConflict):
            submit_verification(profile=self.profile)

    def test_database_allows_only_one_pending(self):
        ApplicantVerification.objects.create(profile=self.profile)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ApplicantVerification.objects.create(profile=self.profile)

    def test_review_can_verify_and_records_server_fields(self):
        verification = submit_verification(profile=self.profile)
        result = review_verification(
            verification_id=verification.id,
            reviewer=self.moderator,
            decision=VerificationStatus.VERIFIED,
        )
        self.assertEqual(result.status, VerificationStatus.VERIFIED)
        self.assertEqual(result.reviewed_by, self.moderator)
        self.assertIsNotNone(result.reviewed_at)

    def test_rejection_requires_nonblank_trimmed_comment(self):
        for comment in ("", "   "):
            verification = ApplicantVerification.objects.create(profile=self.profile)
            with self.subTest(comment=repr(comment)), self.assertRaises(VerificationValidationError):
                review_verification(
                    verification_id=verification.id,
                    reviewer=self.moderator,
                    decision=VerificationStatus.REJECTED,
                    comment=comment,
                )
            verification.delete()

    def test_rejected_can_resubmit_and_preserves_history(self):
        first = submit_verification(profile=self.profile)
        review_verification(
            verification_id=first.id,
            reviewer=self.moderator,
            decision=VerificationStatus.REJECTED,
            comment="More information required",
        )
        second = submit_verification(profile=self.profile)
        first.refresh_from_db()
        self.assertEqual(first.status, VerificationStatus.REJECTED)
        self.assertEqual(second.status, VerificationStatus.PENDING)
        self.assertEqual(self.profile.verification_requests.count(), 2)

    def test_verified_is_terminal_and_review_cannot_repeat(self):
        verification = submit_verification(profile=self.profile)
        review_verification(
            verification_id=verification.id,
            reviewer=self.moderator,
            decision=VerificationStatus.VERIFIED,
        )
        with self.assertRaises(VerificationStateConflict):
            review_verification(
                verification_id=verification.id,
                reviewer=self.moderator,
                decision=VerificationStatus.REJECTED,
                comment="Must not change",
            )
        with self.assertRaises(VerificationStateConflict):
            submit_verification(profile=self.profile)

    def test_review_does_not_touch_aid_request_lifecycle(self):
        aid_request = AidRequest.objects.create(
            applicant=self.profile.user,
            category="food",
            title="Lifecycle fixture",
            description="Verification must not affect this request",
            region="Test region",
            urgency=3,
            status=RequestStatus.ON_MODERATION,
        )
        verification = submit_verification(profile=self.profile)
        review_verification(
            verification_id=verification.id,
            reviewer=self.moderator,
            decision=VerificationStatus.VERIFIED,
        )
        aid_request.refresh_from_db()
        self.assertEqual(aid_request.status, RequestStatus.ON_MODERATION)
        self.assertFalse(RequestStatusHistory.objects.filter(aid_request=aid_request).exists())


class VerificationApiTests(APITestCase):
    def setUp(self):
        self.profile = make_profile(username="api_verification_applicant")
        self.other_profile = make_profile(username="api_other_applicant")
        self.helper = User.objects.create_user(username="api_verification_helper", role="helper")
        self.moderator = User.objects.create_user(username="api_verification_moderator", role="moderator")
        self.admin = User.objects.create_user(username="api_verification_admin", role="admin")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def submit(self, user=None, payload=None):
        self.auth(user or self.profile.user)
        return self.client.post("/api/applicant/verification/submit/", payload or {}, format="json")

    def decide(self, verification, decision, comment="", user=None, extra=None):
        self.auth(user or self.moderator)
        payload = {"decision": decision, "comment": comment, **(extra or {})}
        return self.client.post(
            f"/api/moderation/verifications/{verification.id}/decision/",
            payload,
            format="json",
        )

    def test_applicant_gets_and_patches_only_own_profile(self):
        self.auth(self.profile.user)
        get_response = self.client.get("/api/applicant/profile/")
        patch_response = self.client.patch(
            "/api/applicant/profile/",
            {
                "household_size": 4,
                "dependents_count": 2,
                "consent_to_data_processing": True,
                "region": "Must not change",
                "role": "admin",
            },
            format="json",
        )
        self.profile.refresh_from_db()
        self.profile.user.refresh_from_db()
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["verification_status"], "not_submitted")
        self.assertNotIn("username", get_response.data)
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(self.profile.household_size, 4)
        self.assertEqual(self.profile.dependents_count, 2)
        self.assertEqual(self.profile.user.region, "Test region")
        self.assertEqual(self.profile.user.role, "applicant")
        self.assertNotEqual(self.profile.id, self.other_profile.id)

    def test_non_applicants_cannot_use_profile_or_history(self):
        for user in (self.helper, self.moderator, self.admin):
            with self.subTest(role=user.role):
                self.auth(user)
                self.assertEqual(self.client.get("/api/applicant/profile/").status_code, 403)
                self.assertEqual(
                    self.client.get("/api/applicant/verification/history/").status_code,
                    403,
                )

    def test_submit_returns_pending_and_ignores_review_actor_payload(self):
        response = self.submit(payload={"reviewed_by": self.admin.id, "status": "verified"})
        verification = ApplicantVerification.objects.get(profile=self.profile)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(verification.status, VerificationStatus.PENDING)
        self.assertIsNone(verification.reviewed_by)

    def test_pending_and_verified_submit_conflicts_are_409(self):
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.submit().status_code, 409)
        verification = self.profile.verification_requests.get()
        review_verification(
            verification_id=verification.id,
            reviewer=self.moderator,
            decision=VerificationStatus.VERIFIED,
        )
        self.assertEqual(self.submit().status_code, 409)

    def test_history_is_own_newest_first_and_hides_reviewer_identity(self):
        first = submit_verification(profile=self.profile)
        review_verification(
            verification_id=first.id,
            reviewer=self.moderator,
            decision=VerificationStatus.REJECTED,
            comment="Applicant-safe explanation",
        )
        second = submit_verification(profile=self.profile)
        ApplicantVerification.objects.create(profile=self.other_profile, status=VerificationStatus.REJECTED)
        self.auth(self.profile.user)
        response = self.client.get("/api/applicant/verification/history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [second.id, first.id])
        for item in response.data:
            self.assertNotIn("reviewed_by", item)
            self.assertNotIn("applicant_username", item)

    def test_moderator_queue_defaults_pending_and_supports_region_filter(self):
        pending = submit_verification(profile=self.profile)
        rejected = ApplicantVerification.objects.create(
            profile=self.other_profile,
            status=VerificationStatus.REJECTED,
            review_comment="Previous rejection",
        )
        self.auth(self.moderator)
        response = self.client.get("/api/moderation/verifications/", {"region": "test region"})
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", response.data)
        self.assertEqual([item["id"] for item in results], [pending.id])
        self.assertIn("applicant_username", results[0])
        self.assertIn("household_size", results[0])
        self.assertNotEqual(results[0]["id"], rejected.id)
        detail = self.client.get(f"/api/moderation/verifications/{pending.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["applicant_user_id"], self.profile.user_id)

    def test_applicant_and_helper_cannot_access_moderation_api(self):
        verification = submit_verification(profile=self.profile)
        for user in (self.profile.user, self.helper):
            with self.subTest(role=user.role):
                self.auth(user)
                self.assertEqual(self.client.get("/api/moderation/verifications/").status_code, 403)
                self.assertEqual(
                    self.client.post(
                        f"/api/moderation/verifications/{verification.id}/decision/",
                        {"decision": "verified"},
                    ).status_code,
                    403,
                )

    def test_moderator_and_admin_can_decide_and_actor_is_server_owned(self):
        for reviewer in (self.moderator, self.admin):
            with self.subTest(role=reviewer.role):
                profile = self.profile if reviewer == self.moderator else self.other_profile
                verification = submit_verification(profile=profile)
                response = self.decide(
                    verification,
                    VerificationStatus.VERIFIED,
                    user=reviewer,
                    extra={"reviewed_by": self.helper.id},
                )
                verification.refresh_from_db()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(verification.reviewed_by, reviewer)
                self.assertIsNotNone(verification.reviewed_at)

    def test_rejected_comment_validation_and_repeat_decision(self):
        for comment in ("", "   "):
            verification = submit_verification(profile=self.profile)
            response = self.decide(verification, VerificationStatus.REJECTED, comment)
            self.assertEqual(response.status_code, 400)
            verification.delete()

        verification = submit_verification(profile=self.profile)
        first = self.decide(verification, VerificationStatus.REJECTED, "  Need clarification  ")
        second = self.decide(verification, VerificationStatus.VERIFIED)
        verification.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(verification.review_comment, "Need clarification")
        self.assertEqual(second.status_code, 409)

    def test_missing_decision_target_is_404(self):
        self.auth(self.moderator)
        response = self.client.post(
            "/api/moderation/verifications/999999/decision/",
            {"decision": "verified"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_aid_request_role_serializers_keep_verification_private(self):
        verification = submit_verification(profile=self.profile)
        review_verification(
            verification_id=verification.id,
            reviewer=self.moderator,
            decision=VerificationStatus.VERIFIED,
        )
        moderation_request = AidRequest.objects.create(
            applicant=self.profile.user,
            category="food",
            title="Moderation serialization fixture",
            description="Internal fixture",
            region="Test region",
            urgency=3,
            status=RequestStatus.ON_MODERATION,
        )
        published_request = AidRequest.objects.create(
            applicant=self.profile.user,
            category="food",
            title="Helper serialization fixture",
            description="Private description",
            region="Test region",
            urgency=3,
            status=RequestStatus.PUBLISHED,
        )

        self.auth(self.moderator)
        moderator_response = self.client.get("/api/requests/moderation/queue/")
        moderator_results = moderator_response.data.get("results", moderator_response.data)
        moderator_item = next(item for item in moderator_results if item["id"] == moderation_request.id)
        self.assertEqual(moderator_item["applicant_verification_status"], "verified")

        self.auth(self.helper)
        helper_response = self.client.get("/api/requests/published/")
        helper_results = helper_response.data.get("results", helper_response.data)
        helper_item = next(item for item in helper_results if item["id"] == published_request.id)
        forbidden = {
            "verification",
            "verification_status",
            "applicant_verification_status",
            "household_size",
            "dependents_count",
            "consent_to_data_processing",
            "reviewed_by",
            "review_comment",
        }
        self.assertFalse(forbidden.intersection(helper_item))

        self.auth(self.profile.user)
        applicant_response = self.client.get("/api/requests/applicant/my/")
        applicant_results = applicant_response.data.get("results", applicant_response.data)
        self.assertTrue(applicant_results)
        self.assertNotIn("applicant_verification_status", applicant_results[0])
