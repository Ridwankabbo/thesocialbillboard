from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

urlpatterns = [
    path('creator-products/', CreatorProductListView.as_view(), name='creator-product-list'),
]
