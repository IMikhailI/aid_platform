from rest_framework import status
from rest_framework.test import APITestCase


class RegisterViewTests(APITestCase):
    def test_public_registration_allows_applicant(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "public_applicant",
                "email": "public_applicant@example.com",
                "password": "Pass12345!",
                "role": "applicant",
                "region": "Moscow",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["role"], "applicant")

    def test_public_registration_allows_helper(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "public_helper",
                "email": "public_helper@example.com",
                "password": "Pass12345!",
                "role": "helper",
                "region": "Moscow",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["role"], "helper")

    def test_public_registration_denies_moderator(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "public_moderator",
                "email": "public_moderator@example.com",
                "password": "Pass12345!",
                "role": "moderator",
                "region": "Moscow",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertIn("role", resp.data)

    def test_public_registration_defaults_to_applicant(self):
        resp = self.client.post(
            "/api/auth/register/",
            {
                "username": "default_role_user",
                "email": "default_role_user@example.com",
                "password": "Pass12345!",
                "region": "Moscow",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["role"], "applicant")
