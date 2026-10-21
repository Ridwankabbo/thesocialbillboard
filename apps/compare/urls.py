from django.urls import path
from .views import ChannelComparisonView

urlpatterns = [
    path('compare-channels/', ChannelComparisonView.as_view(), name='compare_channels'),
]