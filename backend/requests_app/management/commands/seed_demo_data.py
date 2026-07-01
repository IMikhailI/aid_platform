from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from fraud.models import FraudAction, FraudOverride
from fraud.services.engine import evaluate_request_safe
from requests_app.models import AidRequest, HelpCommitment, RequestCategory, RequestStatus
from requests_app.services.transitions import transition_request
from users.models import UserRole


User = get_user_model()


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    role: str
    email: str
    region: str
    is_staff: bool = False
    is_superuser: bool = False


DEMO_USERS = [
    DemoUserSpec("applicant_demo", UserRole.APPLICANT, "applicant_demo@example.com", "Moscow"),
    DemoUserSpec("applicant_story", UserRole.APPLICANT, "applicant_story@example.com", "Kazan"),
    DemoUserSpec("applicant_risky", UserRole.APPLICANT, "applicant_risky@example.com", "Perm"),
    DemoUserSpec("applicant_burst", UserRole.APPLICANT, "applicant_burst@example.com", "Tyumen"),
    DemoUserSpec("helper_demo", UserRole.HELPER, "helper_demo@example.com", "Moscow"),
    DemoUserSpec("moderator_demo", UserRole.MODERATOR, "moderator_demo@example.com", "Moscow"),
    DemoUserSpec("admin_demo", UserRole.ADMIN, "admin_demo@example.com", "Moscow", is_staff=True, is_superuser=True),
]


class Command(BaseCommand):
    help = "Seed demo users and requests, including anti-fraud showcase scenarios."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="StrongPass123")
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded demo requests before seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        reset = options["reset"]

        users = {spec.username: self._upsert_user(spec, password) for spec in DEMO_USERS}
        demo_applicants = [
            users["applicant_demo"],
            users["applicant_story"],
            users["applicant_risky"],
            users["applicant_burst"],
        ]

        if reset:
            AidRequest.objects.filter(applicant__in=demo_applicants).delete()

        self._seed_core_flow(
            applicant_demo=users["applicant_demo"],
            applicant_story=users["applicant_story"],
            helper_demo=users["helper_demo"],
            moderator_demo=users["moderator_demo"],
        )
        self._seed_fraud_duplicates(
            risky_applicant=users["applicant_risky"],
            moderator_demo=users["moderator_demo"],
        )
        self._seed_burst_pattern(
            burst_applicant=users["applicant_burst"],
        )

        self.stdout.write(self.style.SUCCESS("Demo users and requests are ready."))
        self.stdout.write("Credentials:")
        for spec in DEMO_USERS:
            self.stdout.write(f"  {spec.username} / {password} ({spec.role})")

    def _upsert_user(self, spec: DemoUserSpec, password: str):
        user, _created = User.objects.get_or_create(username=spec.username)
        user.email = spec.email
        user.region = spec.region
        user.role = spec.role
        user.is_active = True
        user.is_staff = spec.is_staff
        user.is_superuser = spec.is_superuser
        user.set_password(password)
        user.save()
        return user

    def _create_request(self, applicant, *, title: str, description: str, region: str, amount: str, urgency: int):
        request_obj = AidRequest.objects.create(
            applicant=applicant,
            category=RequestCategory.FOOD,
            title=title,
            description=description,
            region=region,
            requested_amount=amount,
            urgency=urgency,
            status=RequestStatus.DRAFT,
        )
        return transition_request(
            request_id=request_obj.id,
            target_status=RequestStatus.ON_MODERATION,
            actor=applicant,
            comment="Seeded request created",
        ).aid_request

    def _transition(self, request_obj, *, new_status: str, changed_by, comment: str):
        return transition_request(
            request_id=request_obj.id,
            target_status=new_status,
            actor=changed_by,
            comment=comment,
        ).aid_request

    def _seed_core_flow(self, *, applicant_demo, applicant_story, helper_demo, moderator_demo):
        published_request = self._create_request(
            applicant_demo,
            title="Продуктовая помощь на 5 дней",
            description="Семья с ребенком, нужна базовая корзина до конца недели.",
            region=applicant_demo.region,
            amount="3200.00",
            urgency=3,
        )
        self._transition(
            published_request,
            new_status=RequestStatus.PUBLISHED,
            changed_by=moderator_demo,
            comment="Проверено модератором",
        )

        in_progress_request = self._create_request(
            applicant_story,
            title="Подгузники и детское питание",
            description="Мама с младенцем, нужна срочная помощь товарами.",
            region=applicant_story.region,
            amount="5400.00",
            urgency=4,
        )
        self._transition(
            in_progress_request,
            new_status=RequestStatus.PUBLISHED,
            changed_by=moderator_demo,
            comment="Проверено модератором",
        )
        HelpCommitment.objects.update_or_create(
            aid_request=in_progress_request,
            defaults={
                "helper": helper_demo,
                "method": "certificate",
                "note": "Demo commitment",
            },
        )
        self._transition(
            in_progress_request,
            new_status=RequestStatus.IN_PROGRESS,
            changed_by=helper_demo,
            comment="Взята в работу",
        )

        closed_request = self._create_request(
            applicant_demo,
            title="Лекарства по рецепту",
            description="Нужна оплата заказа в аптеке по готовому счету.",
            region=applicant_demo.region,
            amount="2700.00",
            urgency=4,
        )
        self._transition(
            closed_request,
            new_status=RequestStatus.PUBLISHED,
            changed_by=moderator_demo,
            comment="Проверено модератором",
        )
        HelpCommitment.objects.update_or_create(
            aid_request=closed_request,
            defaults={
                "helper": helper_demo,
                "method": "invoice",
                "note": "Demo invoice payment",
            },
        )
        self._transition(
            closed_request,
            new_status=RequestStatus.IN_PROGRESS,
            changed_by=helper_demo,
            comment="Оплата подтверждена",
        )
        self._transition(
            closed_request,
            new_status=RequestStatus.CLOSED,
            changed_by=helper_demo,
            comment="Кейс закрыт",
        )

        rejected_request = self._create_request(
            applicant_story,
            title="Неполная заявка",
            description="Недостаточно данных для подтверждения кейса.",
            region=applicant_story.region,
            amount="1000.00",
            urgency=2,
        )
        self._transition(
            rejected_request,
            new_status=RequestStatus.REJECTED,
            changed_by=moderator_demo,
            comment="Запрос отклонен: нужны подтверждающие детали",
        )

    def _seed_fraud_duplicates(self, *, risky_applicant, moderator_demo):
        duplicate_payload = {
            "title": "Срочно нужна продуктовая помощь",
            "description": "Одинаковый текст для демонстрации duplicate anti-fraud сигнала.",
            "region": risky_applicant.region,
            "amount": "1800.00",
            "urgency": 3,
        }

        duplicate_requests = []
        for idx in range(4):
            request_obj = self._create_request(
                risky_applicant,
                title=duplicate_payload["title"],
                description=duplicate_payload["description"],
                region=duplicate_payload["region"],
                amount=duplicate_payload["amount"],
                urgency=duplicate_payload["urgency"],
            )
            evaluate_request_safe(request_obj)
            duplicate_requests.append(request_obj)

        override_request = duplicate_requests[-1]
        override_decision = override_request.fraud_decision
        old_action = override_decision.action
        override_decision.action = FraudAction.ALLOW
        override_decision.save(update_fields=["action", "decided_at"])

        FraudOverride.objects.update_or_create(
            aid_request=override_request,
            old_action=old_action,
            new_action=FraudAction.ALLOW,
            changed_by=moderator_demo,
            defaults={"comment": "Demo override for thesis presentation"},
        )

    def _seed_burst_pattern(self, *, burst_applicant):
        for idx in range(5):
            request_obj = self._create_request(
                burst_applicant,
                title=f"Повторяющаяся заявка #{idx + 1}",
                description=f"Уникальный текст {idx + 1} для burst-демонстрации.",
                region=burst_applicant.region,
                amount="900.00",
                urgency=2,
            )
            evaluate_request_safe(request_obj)
