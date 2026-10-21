from django.urls import path
from .views import DefaultCreatorsAPIView, SearchCreatorsAPIView, FilterCreatorsAPIView, CreatorsAPIView

urlpatterns = [
    path('creators/', DefaultCreatorsAPIView.as_view(), name='creators-default'),
    path('creators/search/', SearchCreatorsAPIView.as_view(), name='creators-search'),
    path('creators/filter/', FilterCreatorsAPIView.as_view(), name='creators-filter'),

    path("creators-explore/", CreatorsAPIView.as_view(), name="creators"),
]
