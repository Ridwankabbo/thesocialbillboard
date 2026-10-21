from django.urls import path
from .views import *

urlpatterns = [
    path("subscribe/", CreateCheckoutView.as_view()),
    path("subscription/cancel/", CancelSubscriptionView.as_view()),
    path("subscription/upgrade/", UpgradeSubscriptionView.as_view()),
    path("subscription/my/", MySubscriptionView.as_view()),
    path("subscription/plans/", SubscriptionPlanListView.as_view()),
    path("subscription/invoices/", InvoiceHistoryView.as_view()),
    path("webhook/stripe/", stripe_webhook),
    # path("cards/save/", SaveCardView.as_view()),
    path("cards/list/", ListSavedCardsView.as_view()),
    path("payment/success/", StripePaymentSuccessView.as_view()),
]
