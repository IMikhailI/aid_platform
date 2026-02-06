from django.urls import path
from .views import (
    ApplicantCreateRequestView,
    ApplicantOwnRequestsView,
    PublicPublishedRequestsView,
    ModerationQueueView,
    ModerateRequestView,
    TakeRequestIntoWorkView,
    CloseRequestView,
    RequestHistoryView,
)

urlpatterns = [
    path("applicant/create/", ApplicantCreateRequestView.as_view()),
    path("applicant/my/", ApplicantOwnRequestsView.as_view()),
    path("published/", PublicPublishedRequestsView.as_view()),
    path("moderation/queue/", ModerationQueueView.as_view()),
    path("moderation/<int:request_id>/", ModerateRequestView.as_view()),
    path("helper/take/<int:request_id>/", TakeRequestIntoWorkView.as_view()),
    path("close/<int:request_id>/", CloseRequestView.as_view()),
    path("<int:request_id>/history/", RequestHistoryView.as_view()),
]

