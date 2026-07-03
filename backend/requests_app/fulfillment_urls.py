from django.urls import path

from requests_app.fulfillment_views import (
    ApplicantConfirmReceiptView,
    ApplicantFulfillmentView,
    HelperFulfillmentDeliverView,
    HelperFulfillmentView,
    ModeratorFulfillmentView,
)


helper_fulfillment_urlpatterns = [
    path("requests/<int:request_id>/fulfillment/", HelperFulfillmentView.as_view()),
    path("requests/<int:request_id>/fulfillment/deliver/", HelperFulfillmentDeliverView.as_view()),
]

applicant_fulfillment_urlpatterns = [
    path("requests/<int:request_id>/fulfillment/", ApplicantFulfillmentView.as_view()),
    path("requests/<int:request_id>/confirm-receipt/", ApplicantConfirmReceiptView.as_view()),
]

moderator_fulfillment_urlpatterns = [
    path("requests/<int:request_id>/fulfillment/", ModeratorFulfillmentView.as_view()),
]
