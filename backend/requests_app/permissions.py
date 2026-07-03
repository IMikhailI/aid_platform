from rest_framework.permissions import BasePermission


class IsApplicant(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "applicant")


class IsModerator(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("moderator", "admin"))


class IsHelper(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("helper", "admin"))

class IsHelperOnly(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "helper")


class CanCloseRequest(BasePermission):
    """
    Deprecated close alias доступен только applicant.
    """
    message = "Недостаточно прав для закрытия заявки."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "applicant")
