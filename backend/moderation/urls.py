from django.urls import path

from moderation.views import (
    ApplicantProfileView,
    ApplicantVerificationHistoryView,
    ApplicantVerificationSubmitView,
    ModeratorVerificationDecisionView,
    ModeratorVerificationDetailView,
    ModeratorVerificationQueueView,
)
from requests_app.views import ModeratorRequestListView


applicant_urlpatterns = [
    path("profile/", ApplicantProfileView.as_view(), name="applicant-profile"),
    path(
        "verification/submit/",
        ApplicantVerificationSubmitView.as_view(),
        name="applicant-verification-submit",
    ),
    path(
        "verification/history/",
        ApplicantVerificationHistoryView.as_view(),
        name="applicant-verification-history",
    ),
]

moderation_urlpatterns = [
    path("requests/", ModeratorRequestListView.as_view(), name="request-list"),
    path("verifications/", ModeratorVerificationQueueView.as_view(), name="verification-queue"),
    path(
        "verifications/<int:pk>/",
        ModeratorVerificationDetailView.as_view(),
        name="verification-detail",
    ),
    path(
        "verifications/<int:pk>/decision/",
        ModeratorVerificationDecisionView.as_view(),
        name="verification-decision",
    ),
]

# Default include is the applicant-scoped API.
urlpatterns = applicant_urlpatterns
