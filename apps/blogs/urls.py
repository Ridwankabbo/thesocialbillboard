from django.urls import path
from .views import BlogListAPIView, BlogDetailAPIView, RecentBlogsAPIView

urlpatterns = [
    path('blogs/all/', BlogListAPIView.as_view(), name='blog-list'),
    path('blogs/recent/', RecentBlogsAPIView.as_view(), name='recent-blogs'),
    path('blogs/<slug:slug>/', BlogDetailAPIView.as_view(), name='blog-detail'),
]
