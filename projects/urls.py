from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.permissions import AllowAny
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = [
    path('admin/', admin.site.urls),
    # add by sakhawat
    path('api/', include('apps.users.urls')),

    path('api/', include('apps.compare.urls')),

    path('api/', include('apps.tiktok.urls')),

    path('api/', include('apps.instagram.urls')),
    path('api/', include('apps.youtube.urls')),
    # path('api/', include('apps.social_analysis.urls')),

    # added by riyad
    path('api/', include('apps.creator_product.urls')),
    path('api/', include('apps.trending_video.urls')),
    path('api/', include('apps.payment_stripe.urls')),
    path('api/', include('apps.your_competitor.urls')),
    path('api/', include('apps.parents.urls')),
    path('api/', include('apps.spotify.urls')),
    path('api/', include('apps.filters.urls')),
    path('api/', include('apps.creators_explore.urls')),
    path('api/', include('apps.viral_builder.urls')),
    path('api/', include('apps.dashboard.urls')),
    path('api/', include('apps.audit.urls')),
    path('api/', include('apps.blogs.urls')),
    path('api/', include('apps.newsletter.urls')),
    # path('api/', include('apps.dashbord_analytics.urls')),
    path('api/', include('apps.custom_playlist.urls')),

    path('api/', include('apps.creator_dashboard.urls')),
    path('api/', include('apps.creator_dashboard_leaderboard.urls')),

    path("accounts/", include("allauth.urls")),                      # <--- adds socialaccount_signup name
    path("dj-rest-auth/", include("dj_rest_auth.urls")),
    path("dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),

]


   
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
