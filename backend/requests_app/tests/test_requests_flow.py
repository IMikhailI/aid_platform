from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from requests_app.models import AidRequest, RequestStatus, RequestStatusHistory, HelpCommitment


User = get_user_model()


class RequestsFlowAPITests(APITestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="applicant1", password="Pass12345!", role="applicant", region="Berlin"
        )
        self.helper = User.objects.create_user(
            username="helper1", password="Pass12345!", role="helper", region="Berlin"
        )
        self.other_helper = User.objects.create_user(
            username="helper2", password="Pass12345!", role="helper", region="Berlin"
        )
        self.moderator = User.objects.create_user(
            username="moderator1", password="Pass12345!", role="moderator", region="Berlin"
        )
        self.admin = User.objects.create_user(
            username="admin1", password="Pass12345!", role="admin", region="Berlin"
        )

    def auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def get_valid_commit_method(self):
        field = HelpCommitment._meta.get_field("method")
        if field.choices:
            return field.choices[0][0]

        t = field.get_internal_type()
        if t in ("IntegerField", "PositiveIntegerField", "SmallIntegerField", "PositiveSmallIntegerField"):
            return 1
        if t in ("FloatField", "DecimalField"):
            return 1
        if t == "BooleanField":
            return False
        return "default"


    def create_request(self, applicant=None, **kwargs):
        applicant = applicant or self.applicant

        category_field = AidRequest._meta.get_field("category")
        urgency_field = AidRequest._meta.get_field("urgency")

        # category: если есть choices — берем первое, иначе fallback строка
        if category_field.choices:
            category_value = category_field.choices[0][0]
        else:
            category_value = "other"

        # urgency: если есть choices — берем первое
        # если choices нет — подставляем значение по типу поля
        if urgency_field.choices:
            urgency_value = urgency_field.choices[0][0]
        else:
            internal_type = urgency_field.get_internal_type()
            if internal_type in ("IntegerField", "PositiveIntegerField", "SmallIntegerField", "PositiveSmallIntegerField"):
                urgency_value = 1
            elif internal_type in ("FloatField", "DecimalField"):
                urgency_value = 1
            elif internal_type == "BooleanField":
                urgency_value = False
            else:
                # CharField / TextField и т.п.
                urgency_value = "normal"

        payload = {
            "title": "Need medicines",
            "description": "Urgent help needed",
            "category": category_value,
            "urgency": urgency_value,
            "region": "Berlin",
            **kwargs,
        }

        self.auth(applicant)
        resp = self.client.post("/api/requests/applicant/create/", payload, format="json")
        self.assertIn(
            resp.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
            getattr(resp, "data", resp.content.decode()),
        )
        req_id = resp.data.get("id")
        self.assertIsNotNone(req_id, "Create response must return request id")
        return AidRequest.objects.get(id=req_id)



    def test_create_request_sets_on_moderation_and_history(self):
        req = self.create_request()

        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.ON_MODERATION)

        history = RequestStatusHistory.objects.filter(aid_request=req).order_by("created_at")
        self.assertTrue(history.exists(), "History must contain initial status transition")
        self.assertEqual(history.last().new_status, RequestStatus.ON_MODERATION)

    def test_create_request_persists_device_telemetry_hashes(self):
        self.auth(self.applicant)
        payload = {
            "title": "Need medicines",
            "description": "Urgent help needed",
            "category": AidRequest._meta.get_field("category").choices[0][0],
            "urgency": 3,
            "region": "Berlin",
        }
        resp = self.client.post(
            "/api/requests/applicant/create/",
            payload,
            format="json",
            HTTP_X_DEVICE_ID="device-for-test",
            HTTP_USER_AGENT="pytest-agent",
            REMOTE_ADDR="10.1.2.3",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, getattr(resp, "data", resp.content.decode()))

        req = AidRequest.objects.get(id=resp.data["id"])
        self.assertTrue(req.device_id_hash)
        self.assertTrue(req.ip_hash)
        self.assertTrue(req.user_agent_hash)

    def test_moderator_can_approve_request(self):
        req = self.create_request()

        self.auth(self.moderator)
        resp = self.client.post(
            f"/api/requests/moderation/{req.id}/",
            {"action": "approve", "comment": "Looks valid"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, getattr(resp, "data", resp.content.decode()))

        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.PUBLISHED)

        self.assertTrue(
            RequestStatusHistory.objects.filter(
                aid_request=req, new_status=RequestStatus.PUBLISHED
            ).exists()
        )

    def test_moderator_can_reject_request(self):
        req = self.create_request()

        self.auth(self.moderator)
        resp = self.client.post(
            f"/api/requests/moderation/{req.id}/",
            {"action": "reject", "comment": "Insufficient details"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, getattr(resp, "data", resp.content.decode()))

        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.REJECTED)

        self.assertTrue(
            RequestStatusHistory.objects.filter(
                aid_request=req, new_status=RequestStatus.REJECTED
            ).exists()
        )

    def test_helper_can_take_only_published_request(self):
        req = self.create_request()  # on_moderation

        # not published -> fail
        self.auth(self.helper)
        valid_method = self.get_valid_commit_method()
        resp = self.client.post(
            f"/api/requests/helper/take/{req.id}/",
            {"method": valid_method, "note": "Call first"},
            format="json",
        )
        self.assertIn(
            resp.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT],
            getattr(resp, "data", resp.content.decode()),
        )

        # publish
        self.auth(self.moderator)
        resp2 = self.client.post(
            f"/api/requests/moderation/{req.id}/",
            {"action": "approve", "comment": "ok"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, getattr(resp2, "data", resp2.content.decode()))

        # now can take
        self.auth(self.helper)
        resp3 = self.client.post(
            f"/api/requests/helper/take/{req.id}/",
            {"method": valid_method, "note": "I can help"},
            format="json",
        )
        self.assertEqual(resp3.status_code, status.HTTP_200_OK, getattr(resp3, "data", resp3.content.decode()))

        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.IN_PROGRESS)
        self.assertTrue(HelpCommitment.objects.filter(aid_request=req, helper=self.helper).exists())

    def test_helper_can_close_only_own_in_progress_request(self):
        req = self.create_request()

        self.auth(self.moderator)
        self.client.post(
            f"/api/requests/moderation/{req.id}/",
            {"action": "approve", "comment": "ok"},
            format="json",
        )

        self.auth(self.helper)
        valid_method = self.get_valid_commit_method()
        take_resp = self.client.post(
            f"/api/requests/helper/take/{req.id}/",
            {"method": valid_method, "note": "Taken"},
            format="json",
        )
        self.assertEqual(take_resp.status_code, status.HTTP_200_OK, getattr(take_resp, "data", take_resp.content.decode()))

        # other helper cannot close
        self.auth(self.other_helper)
        resp = self.client.patch(f"/api/requests/close/{req.id}/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, getattr(resp, "data", resp.content.decode()))

        # owner helper can close
        self.auth(self.helper)
        resp2 = self.client.patch(f"/api/requests/close/{req.id}/", {}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, getattr(resp2, "data", resp2.content.decode()))

        req.refresh_from_db()
        self.assertEqual(req.status, RequestStatus.CLOSED)

    def test_forbidden_by_role(self):
        req = self.create_request()

        # helper cannot moderate
        self.auth(self.helper)
        resp = self.client.post(
            f"/api/requests/moderation/{req.id}/",
            {"action": "approve", "comment": "I should not approve"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, getattr(resp, "data", resp.content.decode()))

        # applicant cannot take
        self.auth(self.applicant)
        resp2 = self.client.post(
            f"/api/requests/helper/take/{req.id}/",
            {"method": "phone", "note": "try"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN, getattr(resp2, "data", resp2.content.decode()))
