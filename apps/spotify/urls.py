from django.urls import path
from .views import PodcastCategoryAPIView

urlpatterns = [
    path('podcasts/category/', PodcastCategoryAPIView.as_view(), name='podcast-category'),
]
