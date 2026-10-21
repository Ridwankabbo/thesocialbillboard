from django.urls import path
from .views import *
urlpatterns = [
    path('test/',test, name='test'),
    path('competitors/', competitor_channels),
    path('competitor/',MyCompetitorDataAPIView.as_view(), name='competitor-channels'),
]
