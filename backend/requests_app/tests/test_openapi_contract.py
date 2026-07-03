import re

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient
from drf_spectacular.drainage import GENERATOR_STATS
from drf_spectacular.generators import SchemaGenerator


KEY_PATHS = {
    "/api/applicant/profile/",
    "/api/applicant/verification/submit/",
    "/api/moderation/verifications/",
    "/api/fraud/requests/{request_id}/decision/",
    "/api/fraud/requests/{request_id}/recheck/",
    "/api/helper/requests/{request_id}/fulfillment/",
    "/api/helper/requests/{request_id}/fulfillment/deliver/",
    "/api/applicant/requests/{request_id}/fulfillment/",
    "/api/applicant/requests/{request_id}/confirm-receipt/",
    "/api/moderation/requests/{request_id}/fulfillment/",
    "/api/requests/close/{request_id}/",
}


class OpenApiContractTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        GENERATOR_STATS.reset()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def test_schema_endpoint_returns_200(self):
        response = APIClient().get("/api/schema/")
        self.assertEqual(response.status_code, 200)

    def test_generation_has_no_errors_or_warnings(self):
        self.assertFalse(GENERATOR_STATS._error_cache)
        self.assertFalse(GENERATOR_STATS._warn_cache)

    def test_key_paths_and_deprecated_alias_are_documented(self):
        self.assertTrue(KEY_PATHS.issubset(self.schema["paths"]))
        self.assertTrue(
            self.schema["paths"]["/api/requests/close/{request_id}/"]["patch"]["deprecated"]
        )

    def test_jwt_bearer_security_scheme_is_present(self):
        jwt = self.schema["components"]["securitySchemes"]["jwtAuth"]
        self.assertEqual(jwt["type"], "http")
        self.assertEqual(jwt["scheme"], "bearer")
        self.assertEqual(jwt["bearerFormat"], "JWT")

    def test_operation_ids_are_unique(self):
        operation_ids = []
        for path_item in self.schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation_ids.append(operation["operationId"])
        self.assertEqual(len(operation_ids), len(set(operation_ids)))

    def test_documented_api_paths_exist(self):
        document = (settings.BASE_DIR.parent / "docs" / "API_CONTRACT.md").read_text()
        documented = set(re.findall(r"`(/api/[^`]+)`", document))
        non_schema_paths = {
            "/api/health/",
            "/api/schema/",
            "/api/docs/swagger/",
            "/api/docs/redoc/",
        }
        self.assertTrue(documented - non_schema_paths)
        self.assertFalse((documented - non_schema_paths) - set(self.schema["paths"]))

    def test_helper_schemas_do_not_expose_identity_or_full_code(self):
        schemas = self.schema["components"]["schemas"]
        helper_fulfillment = schemas["HelperFulfillment"]["properties"]
        helper_request = schemas["HelperAidRequest"]["properties"]
        self.assertNotIn("certificate_code", helper_fulfillment)
        self.assertIn("masked_certificate_code", helper_fulfillment)
        for forbidden in ("applicant", "applicant_id", "applicant_username", "email"):
            self.assertNotIn(forbidden, helper_request)

    def test_applicant_schemas_do_not_expose_fraud_or_helper_identity(self):
        schemas = self.schema["components"]["schemas"]
        applicant_request = schemas["ApplicantAidRequest"]["properties"]
        applicant_fulfillment = schemas["ApplicantPreparedFulfillment"]["properties"]
        for forbidden in ("risk_score", "is_flagged", "fraud_decision", "reasons"):
            self.assertNotIn(forbidden, applicant_request)
        for forbidden in ("helper", "helper_id", "helper_username", "created_by_id"):
            self.assertNotIn(forbidden, applicant_fulfillment)
        self.assertNotIn("certificate_code", applicant_fulfillment)
        self.assertIn(
            "certificate_code",
            schemas["ApplicantDeliveredFulfillment"]["properties"],
        )

    def test_moderator_contract_contains_service_fields(self):
        schemas = self.schema["components"]["schemas"]
        self.assertIn(
            "applicant_verification_status",
            schemas["ModeratorAidRequest"]["properties"],
        )
        fraud = schemas["FraudDecision"]["properties"]
        self.assertTrue({"score", "risk_level", "base_action", "action", "reasons"}.issubset(fraud))
        moderator_fulfillment = schemas["ModeratorFulfillment"]["properties"]
        self.assertTrue({"certificate_code", "helper_username", "applicant_username"}.issubset(moderator_fulfillment))
