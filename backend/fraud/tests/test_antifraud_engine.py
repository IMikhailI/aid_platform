from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from requests_app.models import AidRequest, RequestStatus
from fraud.models import FraudAction
from fraud.services.engine import evaluate_request


User = get_user_model()


def _first_choice(field, fallback: str):
    return field.choices[0][0] if getattr(field, "choices", None) else fallback


def _field_default_value(model, field_name: str):
    """
    Подбираем валидное значение для обязательных полей (category/urgency) без хардкода enum.
    """
    field = model._meta.get_field(field_name)

    # если есть choices — берем первое валидное
    if getattr(field, "choices", None):
        return field.choices[0][0]

    # иначе пытаемся угадать по типу
    t = field.get_internal_type()
    if t in ("IntegerField", "PositiveIntegerField", "SmallIntegerField", "PositiveSmallIntegerField"):
        return 1
    if t in ("FloatField", "DecimalField"):
        return 1
    if t == "BooleanField":
        return False
    return "normal"


def make_request(applicant, title: str, description: str, **overrides) -> AidRequest:
    payload = {
        "applicant": applicant,
        "title": title,
        "description": description,
        "region": overrides.pop("region", "Berlin"),
        "category": overrides.pop("category", _field_default_value(AidRequest, "category")),
        "urgency": overrides.pop("urgency", _field_default_value(AidRequest, "urgency")),
        "status": overrides.pop("status", RequestStatus.ON_MODERATION),
        **overrides,
    }
    return AidRequest.objects.create(**payload)


class AntiFraudEngineTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="af_applicant",
            password="Pass12345!",
            role="applicant",
            region="Berlin",
        )

    def test_af01_baseline_allow(self):
        r1 = make_request(self.applicant, "Нужна помощь", "Обычное описание без повторов")
        d1 = evaluate_request(r1)

        self.assertEqual(d1.action, FraudAction.ALLOW, d1.reasons)
        self.assertLess(d1.score, 25, d1.reasons)

    def test_af02_exact_duplicate_same_author_escalates(self):
        # 1-я идентичная
        r1 = make_request(self.applicant, "Тестовая заявка", "Одинаковый текст")
        d1 = evaluate_request(r1)
        self.assertEqual(d1.action, FraudAction.ALLOW, d1.reasons)

        # 2-я идентичная
        r2 = make_request(self.applicant, "Тестовая заявка", "Одинаковый текст")
        d2 = evaluate_request(r2)
        self.assertGreaterEqual(d2.score, 25, d2.reasons)  # должно уже стать рискованнее

        # 3-я идентичная -> должна доходить до BLOCK (Critical) по текущей логике rules-v3
        r3 = make_request(self.applicant, "Тестовая заявка", "Одинаковый текст")
        d3 = evaluate_request(r3)
        self.assertEqual(d3.action, FraudAction.BLOCK, d3.reasons)
        self.assertGreaterEqual(d3.score, 75, d3.reasons)

        # explainability: причины должны быть
        self.assertTrue(isinstance(d3.reasons, list) and len(d3.reasons) > 0)
        codes = {x.get("code") for x in d3.reasons}
        self.assertIn("EXACT_DUPLICATE_SAME_AUTHOR", codes)

    def test_af03_loose_duplicate_digits_escalates(self):
        # Различаются только цифрами -> должно ловиться LOOSE_DUPLICATE_SAME_AUTHOR
        r1 = make_request(self.applicant, "Тестовая заявка 1", "Описание 1")
        d1 = evaluate_request(r1)
        self.assertEqual(d1.action, FraudAction.ALLOW, d1.reasons)

        r2 = make_request(self.applicant, "Тестовая заявка 2", "Описание 2")
        d2 = evaluate_request(r2)
        self.assertGreaterEqual(d2.score, 25, d2.reasons)

        r3 = make_request(self.applicant, "Тестовая заявка 3", "Описание 3")
        d3 = evaluate_request(r3)
        # минимум review/high/critical, но точно не allow
        self.assertNotEqual(d3.action, FraudAction.ALLOW, d3.reasons)

        codes = {x.get("code") for x in d3.reasons}
        self.assertIn("LOOSE_DUPLICATE_SAME_AUTHOR", codes)

    def test_af04_burst_creation_triggers(self):
        # 5 заявок подряд в пределах окна -> BURST_CREATION должен появиться
        created = []
        for i in range(5):
            r = make_request(self.applicant, f"Уникальный заголовок {i}", f"Уникальный текст {i}")
            created.append(evaluate_request(r))

        last = created[-1]
        codes = {x.get("code") for x in last.reasons}
        self.assertIn("BURST_CREATION", codes)
        self.assertGreaterEqual(last.score, 20, last.reasons)
