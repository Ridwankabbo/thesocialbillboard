from django.urls import path
from .views import (
    NewsLetterAPIView
)

urlpatterns =[
    path('newsletter-subscribe/', NewsLetterAPIView.as_view(), name='newsletter-subscribe'),
]