from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from requests_app.models import AidRequest, RequestStatus
from fraud.services.engine import evaluate_request


User = get_user_model()


def _field_default_value(model, field_name: str):
    field = model._meta.get_field(field_name)
    if getattr(field, "choices", None):
        return field.choices[0][0]
    t = field.get_internal_type()
    if t in ("IntegerField", "PositiveIntegerField", "SmallIntegerField", "PositiveSmallIntegerField"):
        return 1
    if t in ("FloatField", "DecimalField"):
        return 1
    if t == "BooleanField":
        return False
    return "normal"


def make_request(applicant, title: str, description: str, region="Berlin"):
    return AidRequest.objects.create(
        applicant=applicant,
        title=title,
        description=description,
        region=region,
        category=_field_default_value(AidRequest, "category"),
        urgency=_field_default_value(AidRequest, "urgency"),
        status=RequestStatus.ON_MODERATION,
    )


class Command(BaseCommand):
    help = "Run antifraud smoke scenarios and optionally write JSON report."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, default="", help="Path to write JSON report (optional).")

    def handle(self, *args, **options):
        out_path = options["out"].strip()

        applicant, _ = User.objects.get_or_create(
            username="af_smoke_applicant",
            defaults={"role": "applicant", "region": "Berlin"},
        )
        if not applicant.has_usable_password():
            applicant.set_password("Pass12345!")
            applicant.save()

        report = []

        def run_case(case_id: str, title: str, desc: str):
            r = make_request(applicant, title, desc)
            d = evaluate_request(r)
            row = {
                "case_id": case_id,
                "request_id": r.id,
                "score": d.score,
                "risk_level": d.risk_level,
                "action": d.action,
                "engine_version": d.engine_version,
                "reasons": d.reasons,
            }
            report.append(row)
            self.stdout.write(
                f"{case_id:20} score={d.score:3} level={d.risk_level:8} action={d.action:14} req={r.id}"
            )

        # AF-01 baseline
        run_case("AF-01 baseline", "Нужна помощь", "Обычное описание без повторов")

        # AF-02 exact duplicates
        run_case("AF-02 exact #1", "Тестовая заявка", "Одинаковый текст")
        run_case("AF-02 exact #2", "Тестовая заявка", "Одинаковый текст")
        run_case("AF-02 exact #3", "Тестовая заявка", "Одинаковый текст")

        # AF-03 loose digits
        run_case("AF-03 loose #1", "Тестовая заявка 1", "Описание 1")
        run_case("AF-03 loose #2", "Тестовая заявка 2", "Описание 2")
        run_case("AF-03 loose #3", "Тестовая заявка 3", "Описание 3")

        if out_path:
            p = Path(out_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(f"\nReport saved to {p}")
