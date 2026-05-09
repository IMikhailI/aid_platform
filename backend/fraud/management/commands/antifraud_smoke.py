from __future__ import annotations

import json
from pathlib import Path
from time import time

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
        run_suffix = str(int(time()))

        report = []

        def build_applicant(case_slug: str):
            applicant, _ = User.objects.get_or_create(
                username=f"af_smoke_{case_slug}_{run_suffix}",
                defaults={"role": "applicant", "region": "Berlin"},
            )
            if not applicant.has_usable_password():
                applicant.set_password("Pass12345!")
                applicant.save()
            return applicant

        def summarize_reasons(reasons):
            ordered = sorted(reasons, key=lambda item: item.get("weight", 0), reverse=True)
            return [item.get("code") for item in ordered[:3]]

        def run_case(case_id: str, title: str, desc: str, *, applicant):
            r = make_request(applicant, title, desc)
            d = evaluate_request(r)
            row = {
                "case_id": case_id,
                "request_id": r.id,
                "score": d.score,
                "risk_level": d.risk_level,
                "base_action": d.base_action,
                "action": d.action,
                "is_overridden": d.is_overridden,
                "engine_version": d.engine_version,
                "top_signal_codes": summarize_reasons(d.reasons),
                "reasons": d.reasons,
            }
            report.append(row)
            self.stdout.write(
                f"{case_id:20} score={d.score:3} level={d.risk_level:8} "
                f"base={d.base_action:14} action={d.action:14} req={r.id}"
            )

        # AF-01 baseline
        run_case(
            "AF-01 baseline",
            "Нужна помощь",
            "Обычное описание без повторов",
            applicant=build_applicant("baseline"),
        )

        # AF-02 exact duplicates
        exact_applicant = build_applicant("exact")
        run_case("AF-02 exact #1", "Тестовая заявка", "Одинаковый текст", applicant=exact_applicant)
        run_case("AF-02 exact #2", "Тестовая заявка", "Одинаковый текст", applicant=exact_applicant)
        run_case("AF-02 exact #3", "Тестовая заявка", "Одинаковый текст", applicant=exact_applicant)

        # AF-03 loose digits
        loose_applicant = build_applicant("loose")
        run_case("AF-03 loose #1", "Тестовая заявка 1", "Описание 1", applicant=loose_applicant)
        run_case("AF-03 loose #2", "Тестовая заявка 2", "Описание 2", applicant=loose_applicant)
        run_case("AF-03 loose #3", "Тестовая заявка 3", "Описание 3", applicant=loose_applicant)

        # AF-04 high amount
        amount_applicant = build_applicant("amount")
        r = make_request(amount_applicant, "Крупная заявка", "Высокая сумма для review")
        r.requested_amount = "25000.00"
        r.urgency = 3
        r.save(update_fields=["requested_amount", "urgency"])
        d = evaluate_request(r)
        report.append(
            {
                "case_id": "AF-04 high amount",
                "request_id": r.id,
                "score": d.score,
                "risk_level": d.risk_level,
                "base_action": d.base_action,
                "action": d.action,
                "is_overridden": d.is_overridden,
                "engine_version": d.engine_version,
                "top_signal_codes": summarize_reasons(d.reasons),
                "reasons": d.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-04 high amount':20} score={d.score:3} level={d.risk_level:8} "
            f"base={d.base_action:14} action={d.action:14} req={r.id}"
        )

        # AF-05 amount + urgency combo
        combo_applicant = build_applicant("combo")
        r2 = make_request(combo_applicant, "Супер срочная заявка", "Высокая сумма и срочность")
        r2.requested_amount = "50000.00"
        r2.urgency = 5
        r2.save(update_fields=["requested_amount", "urgency"])
        d2 = evaluate_request(r2)
        report.append(
            {
                "case_id": "AF-05 amount+urgency",
                "request_id": r2.id,
                "score": d2.score,
                "risk_level": d2.risk_level,
                "base_action": d2.base_action,
                "action": d2.action,
                "is_overridden": d2.is_overridden,
                "engine_version": d2.engine_version,
                "top_signal_codes": summarize_reasons(d2.reasons),
                "reasons": d2.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-05 amount+urgency':20} score={d2.score:3} level={d2.risk_level:8} "
            f"base={d2.base_action:14} action={d2.action:14} req={r2.id}"
        )

        # AF-06 same device cross-account
        shared_device_hash = "af-smoke-shared-device"
        shared_applicant_1 = build_applicant("shared1")
        shared_applicant_2 = build_applicant("shared2")

        r3 = make_request(shared_applicant_1, "Одинаковая заявка", "Одинаковый текст для одного устройства")
        r3.device_id_hash = shared_device_hash
        r3.save(update_fields=["device_id_hash"])
        d3 = evaluate_request(r3)
        report.append(
            {
                "case_id": "AF-06 same-device #1",
                "request_id": r3.id,
                "score": d3.score,
                "risk_level": d3.risk_level,
                "base_action": d3.base_action,
                "action": d3.action,
                "is_overridden": d3.is_overridden,
                "engine_version": d3.engine_version,
                "top_signal_codes": summarize_reasons(d3.reasons),
                "reasons": d3.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-06 same-device #1':20} score={d3.score:3} level={d3.risk_level:8} "
            f"base={d3.base_action:14} action={d3.action:14} req={r3.id}"
        )

        r4 = make_request(shared_applicant_2, "Одинаковая заявка", "Одинаковый текст для одного устройства")
        r4.device_id_hash = shared_device_hash
        r4.save(update_fields=["device_id_hash"])
        d4 = evaluate_request(r4)
        report.append(
            {
                "case_id": "AF-06 same-device #2",
                "request_id": r4.id,
                "score": d4.score,
                "risk_level": d4.risk_level,
                "base_action": d4.base_action,
                "action": d4.action,
                "is_overridden": d4.is_overridden,
                "engine_version": d4.engine_version,
                "top_signal_codes": summarize_reasons(d4.reasons),
                "reasons": d4.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-06 same-device #2':20} score={d4.score:3} level={d4.risk_level:8} "
            f"base={d4.base_action:14} action={d4.action:14} req={r4.id}"
        )

        # AF-07 same IP cross-account
        shared_ip_hash = "af-smoke-shared-ip"
        shared_ip_applicant_1 = build_applicant("sharedip1")
        shared_ip_applicant_2 = build_applicant("sharedip2")

        r5 = make_request(shared_ip_applicant_1, "Одинаковая заявка по IP", "Одинаковый текст для одного IP")
        r5.ip_hash = shared_ip_hash
        r5.save(update_fields=["ip_hash"])
        d5 = evaluate_request(r5)
        report.append(
            {
                "case_id": "AF-07 same-ip #1",
                "request_id": r5.id,
                "score": d5.score,
                "risk_level": d5.risk_level,
                "base_action": d5.base_action,
                "action": d5.action,
                "is_overridden": d5.is_overridden,
                "engine_version": d5.engine_version,
                "top_signal_codes": summarize_reasons(d5.reasons),
                "reasons": d5.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-07 same-ip #1':20} score={d5.score:3} level={d5.risk_level:8} "
            f"base={d5.base_action:14} action={d5.action:14} req={r5.id}"
        )

        r6 = make_request(shared_ip_applicant_2, "Одинаковая заявка по IP", "Одинаковый текст для одного IP")
        r6.ip_hash = shared_ip_hash
        r6.save(update_fields=["ip_hash"])
        d6 = evaluate_request(r6)
        report.append(
            {
                "case_id": "AF-07 same-ip #2",
                "request_id": r6.id,
                "score": d6.score,
                "risk_level": d6.risk_level,
                "base_action": d6.base_action,
                "action": d6.action,
                "is_overridden": d6.is_overridden,
                "engine_version": d6.engine_version,
                "top_signal_codes": summarize_reasons(d6.reasons),
                "reasons": d6.reasons,
            }
        )
        self.stdout.write(
            f"{'AF-07 same-ip #2':20} score={d6.score:3} level={d6.risk_level:8} "
            f"base={d6.base_action:14} action={d6.action:14} req={r6.id}"
        )

        if out_path:
            p = Path(out_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(f"\nReport saved to {p}")
