from django.urls import path
from .views import FraudDecisionView, FraudChecksView, FraudOverrideView, FraudRecheckView

urlpatterns = [
    path("requests/<int:request_id>/decision/", FraudDecisionView.as_view(), name="fraud-decision"),
    path("requests/<int:request_id>/checks/", FraudChecksView.as_view(), name="fraud-checks"),
    path("requests/<int:request_id>/override/", FraudOverrideView.as_view(), name="fraud-override"),
    path("requests/<int:request_id>/recheck/", FraudRecheckView.as_view(), name="fraud-recheck"),
]
