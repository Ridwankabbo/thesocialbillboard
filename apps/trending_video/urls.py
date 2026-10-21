from django.urls import path
from .views import *
from apps.parents.views import ChannelOverviewAPIView
urlpatterns = [
    # path('trending-channels/', TrendingChannelsView.as_view(), name='trending-channels'),
    path("climbing-charts/", TrendingChannelsAPIView.as_view()),
    path("safe-channels/", SafeChannelListView.as_view()),
    path('top-uk-creators/', TopTenUkCreatorsAiDatas.as_view(), name='top-uk-creators'),
    path('uk-profile-view/<str:channel_id>/',ChannelOverviewAPIView.as_view()),
    path('ai-recombined-creators/', SmartMatchDataView.as_view(), name='ai-recombined-creators'),

]
