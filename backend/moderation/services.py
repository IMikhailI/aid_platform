from django.db import transaction
from django.utils import timezone

from moderation.models import ApplicantVerification, VerificationStatus
from users.models import ApplicantProfile


class VerificationError(Exception):
    def __init__(self, *, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class VerificationValidationError(VerificationError):
    pass


class VerificationStateConflict(VerificationError):
    pass


@transaction.atomic
def submit_verification(*, profile: ApplicantProfile) -> ApplicantVerification:
    profile = ApplicantProfile.objects.select_for_update().select_related("user").get(pk=profile.pk)

    if not profile.consent_to_data_processing:
        raise VerificationValidationError(
            code="verification_consent_required",
            detail="Для отправки верификации необходимо согласие на обработку данных.",
        )
    if not profile.user.region.strip():
        raise VerificationValidationError(
            code="verification_region_required",
            detail="Для отправки верификации необходимо указать регион.",
        )
    if profile.verification_requests.filter(status=VerificationStatus.PENDING).exists():
        raise VerificationStateConflict(
            code="verification_already_pending",
            detail="Заявка на верификацию уже находится на рассмотрении.",
        )
    if profile.verification_requests.filter(status=VerificationStatus.VERIFIED).exists():
        raise VerificationStateConflict(
            code="verification_already_verified",
            detail="Профиль уже верифицирован.",
        )

    return ApplicantVerification.objects.create(profile=profile)


@transaction.atomic
def review_verification(
    *, verification_id: int, reviewer, decision: str, comment: str = ""
) -> ApplicantVerification:
    verification = (
        ApplicantVerification.objects.select_for_update()
        .select_related("profile", "profile__user")
        .get(pk=verification_id)
    )
    if verification.status != VerificationStatus.PENDING:
        raise VerificationStateConflict(
            code="verification_already_reviewed",
            detail="Решение по этой заявке уже принято.",
        )
    if decision not in {VerificationStatus.VERIFIED, VerificationStatus.REJECTED}:
        raise VerificationValidationError(
            code="invalid_verification_decision",
            detail="Недопустимое решение по верификации.",
        )

    comment = comment.strip()
    if decision == VerificationStatus.REJECTED and not comment:
        raise VerificationValidationError(
            code="verification_rejection_comment_required",
            detail="Для отклонения необходимо указать комментарий.",
        )

    verification.status = decision
    verification.review_comment = comment
    verification.reviewed_by = reviewer
    verification.reviewed_at = timezone.now()
    verification.save(
        update_fields=["status", "review_comment", "reviewed_by", "reviewed_at", "updated_at"]
    )
    return verification
