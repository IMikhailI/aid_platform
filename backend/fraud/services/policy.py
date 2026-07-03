from enum import Enum

from fraud.models import FraudAction, FraudDecision


class FraudPublicationPolicyResult(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "fraud_publication_blocked"
    DECISION_MISSING = "fraud_decision_missing"


class FraudPolicyViolation(Exception):
    def __init__(self, *, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def evaluate_publication_policy(
    decision: FraudDecision | None,
) -> FraudPublicationPolicyResult:
    """Evaluate publication using only the current effective fraud action."""
    if decision is None:
        return FraudPublicationPolicyResult.DECISION_MISSING
    if decision.action == FraudAction.BLOCK:
        return FraudPublicationPolicyResult.BLOCKED
    return FraudPublicationPolicyResult.ALLOWED


def assert_request_can_be_published(decision: FraudDecision | None) -> None:
    result = evaluate_publication_policy(decision)
    if result == FraudPublicationPolicyResult.DECISION_MISSING:
        raise FraudPolicyViolation(
            code=result.value,
            detail="Перед публикацией необходимо выполнить антифрод-проверку.",
        )
    if result == FraudPublicationPolicyResult.BLOCKED:
        raise FraudPolicyViolation(
            code=result.value,
            detail="Публикация заявки запрещена антифрод-политикой.",
        )
