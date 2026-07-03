from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from requests_app.models import (
    AidFulfillment,
    AidRequest,
    FulfillmentStatus,
    HelpCommitment,
    RequestStatus,
)
from requests_app.services.transitions import InvalidRequestTransition, transition_request


class FulfillmentError(Exception):
    def __init__(self, *, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


class FulfillmentNotFound(FulfillmentError):
    pass


class FulfillmentValidationError(FulfillmentError):
    pass


class FulfillmentStateConflict(FulfillmentError):
    pass


def _lock_helper_context(*, request_id: int, helper):
    try:
        aid_request = AidRequest.objects.select_for_update().get(pk=request_id)
    except AidRequest.DoesNotExist as exc:
        raise FulfillmentNotFound(
            code="fulfillment_request_not_found", detail="Заявка не найдена."
        ) from exc
    try:
        commitment = HelpCommitment.objects.select_for_update().get(
            aid_request=aid_request, helper=helper
        )
    except HelpCommitment.DoesNotExist as exc:
        raise FulfillmentNotFound(
            code="fulfillment_not_found", detail="Данные целевой помощи не найдены."
        ) from exc
    return aid_request, commitment


@transaction.atomic
def create_mock_certificate(
    *, request_id: int, helper, provider_name: str, amount: Decimal
) -> AidFulfillment:
    aid_request, commitment = _lock_helper_context(request_id=request_id, helper=helper)
    if aid_request.status != RequestStatus.IN_PROGRESS:
        raise FulfillmentStateConflict(
            code="request_not_in_progress",
            detail="Сертификат можно создать только для заявки в работе.",
        )
    provider_name = provider_name.strip()
    if not provider_name:
        raise FulfillmentValidationError(
            code="provider_name_required", detail="Необходимо указать поставщика."
        )
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise FulfillmentValidationError(
            code="fulfillment_amount_invalid", detail="Некорректная сумма сертификата."
        ) from exc
    if amount <= 0:
        raise FulfillmentValidationError(
            code="fulfillment_amount_invalid", detail="Сумма должна быть больше нуля."
        )
    if amount > aid_request.requested_amount:
        raise FulfillmentValidationError(
            code="fulfillment_amount_exceeds_request",
            detail="Сумма сертификата превышает сумму заявки.",
        )
    if AidFulfillment.objects.select_for_update().filter(commitment=commitment).exists():
        raise FulfillmentStateConflict(
            code="fulfillment_already_exists", detail="Сертификат для заявки уже создан."
        )
    return AidFulfillment.objects.create(
        commitment=commitment,
        provider_name=provider_name,
        amount=amount,
        created_by=helper,
    )


@transaction.atomic
def mark_certificate_delivered(*, request_id: int, helper) -> AidFulfillment:
    aid_request, commitment = _lock_helper_context(request_id=request_id, helper=helper)
    if aid_request.status != RequestStatus.IN_PROGRESS:
        raise FulfillmentStateConflict(
            code="request_not_in_progress", detail="Заявка не находится в работе."
        )
    try:
        fulfillment = AidFulfillment.objects.select_for_update().get(commitment=commitment)
    except AidFulfillment.DoesNotExist as exc:
        raise FulfillmentNotFound(
            code="fulfillment_not_found", detail="Сертификат не найден."
        ) from exc
    if fulfillment.status != FulfillmentStatus.CREATED:
        raise FulfillmentStateConflict(
            code="fulfillment_cannot_be_delivered",
            detail="Сертификат нельзя повторно отметить переданным.",
        )
    fulfillment.status = FulfillmentStatus.DELIVERED
    fulfillment.delivered_at = timezone.now()
    fulfillment.save(update_fields=["status", "delivered_at", "updated_at"])
    return fulfillment


@transaction.atomic
def confirm_certificate_received(*, request_id: int, applicant) -> AidFulfillment:
    try:
        aid_request = AidRequest.objects.select_for_update().get(
            pk=request_id, applicant=applicant
        )
    except AidRequest.DoesNotExist as exc:
        raise FulfillmentNotFound(
            code="fulfillment_request_not_found", detail="Заявка не найдена."
        ) from exc
    if aid_request.status != RequestStatus.IN_PROGRESS:
        raise FulfillmentStateConflict(
            code="request_not_in_progress", detail="Заявка не находится в работе."
        )
    try:
        commitment = HelpCommitment.objects.select_for_update().get(aid_request=aid_request)
        fulfillment = AidFulfillment.objects.select_for_update().get(commitment=commitment)
    except (HelpCommitment.DoesNotExist, AidFulfillment.DoesNotExist) as exc:
        raise FulfillmentNotFound(
            code="fulfillment_not_found", detail="Сертификат не найден."
        ) from exc
    if fulfillment.status != FulfillmentStatus.DELIVERED:
        raise FulfillmentStateConflict(
            code="fulfillment_not_delivered",
            detail="Подтвердить можно только переданный сертификат.",
        )

    fulfillment.status = FulfillmentStatus.CONFIRMED
    fulfillment.confirmed_at = timezone.now()
    fulfillment.save(update_fields=["status", "confirmed_at", "updated_at"])
    try:
        transition_request(
            request_id=aid_request.id,
            target_status=RequestStatus.CLOSED,
            actor=applicant,
            comment="Получение помощи подтверждено заявителем",
        )
    except InvalidRequestTransition as exc:
        raise FulfillmentStateConflict(
            code="request_cannot_be_closed",
            detail="Заявка не может быть закрыта в текущем состоянии.",
        ) from exc
    return fulfillment
