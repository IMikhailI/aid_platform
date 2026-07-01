from dataclasses import dataclass

from django.db import transaction

from requests_app.models import AidRequest, RequestStatus, RequestStatusHistory


ALLOWED_TRANSITIONS = {
    RequestStatus.DRAFT: frozenset({RequestStatus.ON_MODERATION}),
    RequestStatus.ON_MODERATION: frozenset({RequestStatus.PUBLISHED, RequestStatus.REJECTED}),
    RequestStatus.PUBLISHED: frozenset({RequestStatus.IN_PROGRESS}),
    RequestStatus.IN_PROGRESS: frozenset({RequestStatus.CLOSED}),
    RequestStatus.CLOSED: frozenset(),
    RequestStatus.REJECTED: frozenset(),
}


class InvalidRequestTransition(Exception):
    def __init__(self, *, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Transition {current_status!r} -> {target_status!r} is not allowed")


@dataclass(frozen=True)
class TransitionResult:
    aid_request: AidRequest
    changed: bool


@transaction.atomic
def transition_request(*, request_id: int, target_status: str, actor, comment: str = "") -> TransitionResult:
    aid_request = AidRequest.objects.select_for_update().get(pk=request_id)
    current_status = aid_request.status

    if current_status == target_status:
        return TransitionResult(aid_request=aid_request, changed=False)

    allowed_targets = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if target_status not in allowed_targets:
        raise InvalidRequestTransition(
            current_status=current_status,
            target_status=target_status,
        )

    aid_request.status = target_status
    aid_request.save(update_fields=["status", "updated_at"])
    RequestStatusHistory.objects.create(
        aid_request=aid_request,
        old_status=current_status,
        new_status=target_status,
        changed_by=actor,
        comment=comment or "",
    )

    return TransitionResult(aid_request=aid_request, changed=True)
