from django.urls import path
from .views import TopListAPIView

urlpatterns = [
    path('top-list/', TopListAPIView.as_view(), name='top-list'),
]
