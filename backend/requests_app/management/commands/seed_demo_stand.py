from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from fraud.models import FraudAction, FraudCheck, FraudDecision, FraudRiskLevel
from fraud.services.engine import evaluate_request_safe
from moderation.models import ApplicantVerification, VerificationStatus
from moderation.services import review_verification, submit_verification
from requests_app.models import (
    AidRequest,
    FulfillmentStatus,
    HelpCommitment,
    RequestCategory,
    RequestStatus,
)
from requests_app.services.fulfillment import (
    confirm_certificate_received,
    create_mock_certificate,
    mark_certificate_delivered,
)
from requests_app.services.transitions import transition_request
from users.models import ApplicantProfile, UserRole


User = get_user_model()

DEMO_REGION = "Сургут"
DEMO_MARKER = "[DEMO_STAND]"
FRONTEND_V2_URL = "http://localhost:5173"


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    password: str
    role: str
    email: str
    region: str = DEMO_REGION
    is_staff: bool = False
    is_superuser: bool = False


@dataclass(frozen=True)
class DemoRequestSpec:
    slug: str
    title: str
    description: str
    category: str
    amount: Decimal
    urgency: int
    final_status: str
    applicant_username: str = "applicant_demo"
    fraud_action: str = FraudAction.ALLOW
    fraud_level: str = FraudRiskLevel.LOW
    fraud_score: int = 0
    fulfillment_status: str | None = None
    commitment_method: str | None = None


DEMO_USERS = [
    DemoUserSpec(
        "applicant_demo",
        "applicant123",
        UserRole.APPLICANT,
        "applicant_demo@example.test",
    ),
    DemoUserSpec(
        "helper_demo",
        "helper123",
        UserRole.HELPER,
        "helper_demo@example.test",
    ),
    DemoUserSpec(
        "moderator_demo",
        "moderator123",
        UserRole.MODERATOR,
        "moderator_demo@example.test",
    ),
    DemoUserSpec(
        "admin_demo",
        "admin123",
        UserRole.ADMIN,
        "admin_demo@example.test",
        is_staff=True,
        is_superuser=True,
    ),
    DemoUserSpec(
        "applicant_pending_demo",
        "applicant123",
        UserRole.APPLICANT,
        "applicant_pending_demo@example.test",
    ),
    DemoUserSpec(
        "applicant_rejected_demo",
        "applicant123",
        UserRole.APPLICANT,
        "applicant_rejected_demo@example.test",
    ),
]

DEMO_APPLICANT_USERNAMES = [
    spec.username for spec in DEMO_USERS if spec.role == UserRole.APPLICANT
]

DEMO_REQUESTS = [
    DemoRequestSpec(
        slug="request_pending_allow",
        title="Продукты на два дня",
        description="Демонстрационная заявка с низким fraud risk для очереди модератора.",
        category=RequestCategory.FOOD,
        amount=Decimal("1800.00"),
        urgency=2,
        final_status=RequestStatus.ON_MODERATION,
        fraud_action=FraudAction.ALLOW,
        fraud_level=FraudRiskLevel.LOW,
        fraud_score=0,
    ),
    DemoRequestSpec(
        slug="request_pending_manual_review",
        title="Крупная покупка лекарств",
        description="Демонстрационная заявка с medium/manual_review fraud decision.",
        category=RequestCategory.MEDICINE,
        amount=Decimal("25000.00"),
        urgency=3,
        final_status=RequestStatus.ON_MODERATION,
        fraud_action=FraudAction.MANUAL_REVIEW,
        fraud_level=FraudRiskLevel.MEDIUM,
        fraud_score=30,
    ),
    DemoRequestSpec(
        slug="request_pending_block",
        title="Повторная заявка с подозрительным паттерном",
        description="Демонстрационная block-заявка для показа 409 approve и override.",
        category=RequestCategory.OTHER,
        amount=Decimal("5000.00"),
        urgency=4,
        final_status=RequestStatus.ON_MODERATION,
        fraud_action=FraudAction.BLOCK,
        fraud_level=FraudRiskLevel.HIGH,
        fraud_score=70,
    ),
    DemoRequestSpec(
        slug="request_published",
        title="Набор продуктов для семьи",
        description="Опубликованная заявка, которую helper видит в общей ленте.",
        category=RequestCategory.FOOD,
        amount=Decimal("3200.00"),
        urgency=3,
        final_status=RequestStatus.PUBLISHED,
    ),
    DemoRequestSpec(
        slug="request_in_progress",
        title="Детское питание на неделю",
        description="Заявка уже взята helper_demo в работу, fulfillment ещё не создан.",
        category=RequestCategory.CHILDREN,
        amount=Decimal("5400.00"),
        urgency=4,
        final_status=RequestStatus.IN_PROGRESS,
        commitment_method="certificate",
    ),
    DemoRequestSpec(
        slug="request_fulfillment_created",
        title="Сертификат на продукты создан",
        description="Заявка в работе с демонстрационным сертификатом в status=created.",
        category=RequestCategory.FOOD,
        amount=Decimal("4100.00"),
        urgency=3,
        final_status=RequestStatus.IN_PROGRESS,
        fulfillment_status=FulfillmentStatus.CREATED,
        commitment_method="certificate",
    ),
    DemoRequestSpec(
        slug="request_fulfillment_delivered",
        title="Сертификат передан заявителю",
        description="Applicant может увидеть полный код и подтвердить получение.",
        category=RequestCategory.CLOTHES,
        amount=Decimal("3600.00"),
        urgency=4,
        final_status=RequestStatus.IN_PROGRESS,
        fulfillment_status=FulfillmentStatus.DELIVERED,
        commitment_method="certificate",
    ),
    DemoRequestSpec(
        slug="request_closed",
        title="Получение помощи подтверждено",
        description="Закрытый кейс с confirmed fulfillment и историей in_progress -> closed.",
        category=RequestCategory.MEDICINE,
        amount=Decimal("2700.00"),
        urgency=4,
        final_status=RequestStatus.CLOSED,
        fulfillment_status=FulfillmentStatus.CONFIRMED,
        commitment_method="certificate",
    ),
    DemoRequestSpec(
        slug="request_rejected",
        title="Отклоненная демонстрационная заявка",
        description="Заявка отклонена модератором из-за неполного описания.",
        category=RequestCategory.OTHER,
        amount=Decimal("1000.00"),
        urgency=2,
        final_status=RequestStatus.REJECTED,
        applicant_username="applicant_rejected_demo",
    ),
]


class Command(BaseCommand):
    help = "Seed a safe, idempotent local demo stand for diploma presentation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo-passwords",
            action="store_true",
            help="Reset existing demo users to documented local demo passwords.",
        )
        parser.add_argument(
            "--reset-demo-data",
            action="store_true",
            help="Delete only data marked as DEMO_STAND and recreate it.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset_passwords = options["reset_demo_passwords"]
        reset_demo_data = options["reset_demo_data"]

        stats = {
            "users_created": 0,
            "users_existing": 0,
            "profiles_created": 0,
            "profiles_existing": 0,
            "verifications_created": 0,
            "verifications_existing": 0,
            "requests_created": 0,
            "requests_existing": 0,
        }

        users = {}
        for spec in DEMO_USERS:
            user, created = self._upsert_user(spec, reset_password=reset_passwords)
            users[spec.username] = user
            stats["users_created" if created else "users_existing"] += 1

        profiles = {}
        for username in DEMO_APPLICANT_USERNAMES:
            profile, created = self._ensure_applicant_profile(users[username])
            profiles[username] = profile
            stats["profiles_created" if created else "profiles_existing"] += 1

        if reset_demo_data:
            self._reset_demo_data()

        for username, target_status in {
            "applicant_demo": VerificationStatus.VERIFIED,
            "applicant_pending_demo": VerificationStatus.PENDING,
            "applicant_rejected_demo": VerificationStatus.REJECTED,
        }.items():
            created = self._ensure_verification(
                profile=profiles[username],
                target_status=target_status,
                reviewer=users["moderator_demo"],
            )
            stats["verifications_created" if created else "verifications_existing"] += 1

        for spec in DEMO_REQUESTS:
            request_obj, created = self._ensure_demo_request(
                spec=spec,
                applicant=users[spec.applicant_username],
                helper=users["helper_demo"],
                moderator=users["moderator_demo"],
            )
            stats["requests_created" if created else "requests_existing"] += 1

        self._print_summary(stats, reset_passwords=reset_passwords, reset_demo_data=reset_demo_data)

    def _upsert_user(self, spec: DemoUserSpec, *, reset_password: bool):
        user, created = User.objects.get_or_create(
            username=spec.username,
            defaults={
                "email": spec.email,
                "role": spec.role,
                "region": spec.region,
                "is_staff": spec.is_staff,
                "is_superuser": spec.is_superuser,
                "is_active": True,
            },
        )
        user.email = spec.email
        user.role = spec.role
        user.region = spec.region
        user.is_staff = spec.is_staff
        user.is_superuser = spec.is_superuser
        user.is_active = True
        if created or reset_password or not user.has_usable_password():
            user.set_password(spec.password)
        user.save()
        return user, created

    def _ensure_applicant_profile(self, user):
        profile, created = ApplicantProfile.objects.get_or_create(user=user)
        profile.household_size = 3
        profile.dependents_count = 1
        profile.consent_to_data_processing = True
        profile.full_clean()
        profile.save()
        return profile, created

    def _reset_demo_data(self):
        AidRequest.objects.filter(title__startswith=DEMO_MARKER).delete()
        ApplicantVerification.objects.filter(
            profile__user__username__in=DEMO_APPLICANT_USERNAMES
        ).delete()

    def _ensure_verification(self, *, profile, target_status: str, reviewer):
        if profile.verification_requests.filter(status=target_status).exists():
            return False

        pending = profile.verification_requests.filter(status=VerificationStatus.PENDING).first()
        if pending is None:
            pending = submit_verification(profile=profile)

        if target_status == VerificationStatus.PENDING:
            return True

        comment = (
            "Demo verification approved for local stand."
            if target_status == VerificationStatus.VERIFIED
            else "Demo verification rejected for local stand."
        )
        review_verification(
            verification_id=pending.id,
            reviewer=reviewer,
            decision=target_status,
            comment=comment,
        )
        return True

    def _ensure_demo_request(self, *, spec: DemoRequestSpec, applicant, helper, moderator):
        existing = AidRequest.objects.filter(title__startswith=self._title_prefix(spec.slug)).first()
        if existing:
            return existing, False

        request_obj = AidRequest.objects.create(
            applicant=applicant,
            category=spec.category,
            title=f"{self._title_prefix(spec.slug)} {spec.title}",
            description=spec.description,
            region=DEMO_REGION,
            requested_amount=spec.amount,
            urgency=spec.urgency,
            status=RequestStatus.DRAFT,
            device_id_hash=f"demo-device-{spec.slug}",
            ip_hash=f"demo-ip-{spec.slug}",
            user_agent_hash=f"demo-agent-{spec.slug}",
        )
        request_obj = transition_request(
            request_id=request_obj.id,
            target_status=RequestStatus.ON_MODERATION,
            actor=applicant,
            comment=f"{DEMO_MARKER} created by seed_demo_stand",
        ).aid_request
        self._ensure_fraud_decision(request_obj, spec)

        if spec.final_status in {
            RequestStatus.PUBLISHED,
            RequestStatus.IN_PROGRESS,
            RequestStatus.CLOSED,
        }:
            request_obj = transition_request(
                request_id=request_obj.id,
                target_status=RequestStatus.PUBLISHED,
                actor=moderator,
                comment=f"{DEMO_MARKER} approved for demo stand",
            ).aid_request

        if spec.final_status in {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED}:
            HelpCommitment.objects.create(
                aid_request=request_obj,
                helper=helper,
                method=spec.commitment_method or "certificate",
                note=f"{DEMO_MARKER} helper_demo commitment",
            )
            request_obj = transition_request(
                request_id=request_obj.id,
                target_status=RequestStatus.IN_PROGRESS,
                actor=helper,
                comment=f"{DEMO_MARKER} taken by helper_demo",
            ).aid_request
            self._ensure_fulfillment(request_obj, spec, helper)

        if spec.final_status == RequestStatus.REJECTED:
            request_obj = transition_request(
                request_id=request_obj.id,
                target_status=RequestStatus.REJECTED,
                actor=moderator,
                comment=f"{DEMO_MARKER} rejected demo request",
            ).aid_request

        return request_obj, True

    def _ensure_fraud_decision(self, request_obj: AidRequest, spec: DemoRequestSpec):
        if spec.fraud_action in {FraudAction.ALLOW, FraudAction.MANUAL_REVIEW}:
            decision = evaluate_request_safe(request_obj)
            if decision and decision.action == spec.fraud_action:
                return decision

        reasons = self._fraud_reasons(spec)
        FraudCheck.objects.filter(aid_request=request_obj).delete()
        FraudCheck.objects.bulk_create(
            [
                FraudCheck(
                    aid_request=request_obj,
                    signal_code=reason["code"],
                    weight=reason["weight"],
                    value=reason["details"],
                )
                for reason in reasons
            ]
        )
        decision, _ = FraudDecision.objects.update_or_create(
            aid_request=request_obj,
            defaults={
                "score": spec.fraud_score,
                "risk_level": spec.fraud_level,
                "base_action": spec.fraud_action,
                "action": spec.fraud_action,
                "is_overridden": False,
                "reasons": reasons,
                "engine_version": "demo-stand",
            },
        )
        request_obj.risk_score = spec.fraud_score
        request_obj.is_flagged = spec.fraud_level in {
            FraudRiskLevel.HIGH,
            FraudRiskLevel.CRITICAL,
        }
        request_obj.save(update_fields=["risk_score", "is_flagged", "updated_at"])
        return decision

    def _fraud_reasons(self, spec: DemoRequestSpec):
        if spec.fraud_action == FraudAction.ALLOW:
            return []
        if spec.fraud_action == FraudAction.MANUAL_REVIEW:
            return [
                {
                    "code": "HIGH_REQUESTED_AMOUNT",
                    "weight": spec.fraud_score,
                    "details": {"requested_amount": str(spec.amount), "demo": True},
                }
            ]
        return [
            {
                "code": "DEMO_BLOCK_PATTERN",
                "weight": spec.fraud_score,
                "details": {
                    "demo": True,
                    "note": "Synthetic block decision for local moderator scenario.",
                },
            }
        ]

    def _ensure_fulfillment(self, request_obj: AidRequest, spec: DemoRequestSpec, helper):
        if spec.fulfillment_status is None:
            return None

        fulfillment = create_mock_certificate(
            request_id=request_obj.id,
            helper=helper,
            provider_name="Demo Mock Provider",
            amount=min(spec.amount, Decimal("3000.00")),
        )
        if spec.fulfillment_status in {FulfillmentStatus.DELIVERED, FulfillmentStatus.CONFIRMED}:
            fulfillment = mark_certificate_delivered(request_id=request_obj.id, helper=helper)
        if spec.fulfillment_status == FulfillmentStatus.CONFIRMED:
            fulfillment = confirm_certificate_received(request_id=request_obj.id, applicant=request_obj.applicant)
        return fulfillment

    def _title_prefix(self, slug: str) -> str:
        return f"{DEMO_MARKER} {slug}:"

    def _print_summary(self, stats, *, reset_passwords: bool, reset_demo_data: bool):
        self.stdout.write(self.style.SUCCESS("Demo stand data is ready."))
        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(
            f"  users: created={stats['users_created']}, existing={stats['users_existing']}"
        )
        self.stdout.write(
            f"  profiles: created={stats['profiles_created']}, existing={stats['profiles_existing']}"
        )
        self.stdout.write(
            "  verifications: "
            f"created={stats['verifications_created']}, existing={stats['verifications_existing']}"
        )
        self.stdout.write(
            f"  requests: created={stats['requests_created']}, existing={stats['requests_existing']}"
        )
        self.stdout.write("")
        self.stdout.write("Demo credentials for local stand only:")
        for spec in DEMO_USERS:
            self.stdout.write(f"  {spec.username} / {spec.password} ({spec.role})")
        self.stdout.write("")
        self.stdout.write(f"frontend-v2: {FRONTEND_V2_URL}")
        self.stdout.write("")
        self.stdout.write("Demo order:")
        self.stdout.write("  1. Login as moderator_demo and inspect moderation queue.")
        self.stdout.write("  2. Approve the block request to show 409, then use fraud override.")
        self.stdout.write("  3. Login as helper_demo and open published requests plus /helper/my-help.")
        self.stdout.write("  4. Login as applicant_demo and confirm the delivered fulfillment.")
        self.stdout.write("Flags:")
        self.stdout.write(f"  --reset-demo-passwords used: {reset_passwords}")
        self.stdout.write(f"  --reset-demo-data used: {reset_demo_data}")
