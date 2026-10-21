from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

import os
# from dotenv import load_dotenv
from decouple import config

# load_dotenv()  # Load variables from .env
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-@qbn&@raick0x)i6d-zs)24_r5a)uoi8s#ukv@+e6!a^6624oh'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '*',
    'thesocialbillboard.com',
    'admin.thesocialbillboard.com',
    '191.101.80.144',
    'localhost',
    '127.0.0.1',
]


CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:4200",
    "http://localhost:8080",

    "http://localhost:5173",
    "http://127.0.0.1:5173",

    "http://127.0.0.1:3000",
    "http://172.16.100.58:9000",

    "https://almost-unloved-profile.ngrok-free.dev",
    "https://admin.thesocialbillboard.com",
    "https://thesocialbillboard.com",
]

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True


CSRF_TRUSTED_ORIGINS = [
    "https://admin.thesocialbillboard.com",
    "https://thesocialbillboard.com",

    "http://localhost:3000",
    "http://127.0.0.1:3000",

    "http://localhost:5173",
    "http://127.0.0.1:5173",

    "https://almost-unloved-profile.ngrok-free.dev",
]


# Application definition

INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #add by sakhawat
    'apps.users',
    'apps.spotify',
    'apps.creators_explore',
    'apps.blogs',
    'apps.viral_builder',
    'apps.tiktok',
    'apps.instagram',
    'apps.youtube',
    # 'apps.social_analysis',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'ckeditor',
    'apps.custom_playlist',
    'apps.parents',
    'apps.dashboard',
    'apps.audit',

    'apps.creator_dashboard',
    'apps.creator_dashboard_leaderboard',

    #added by riyad
    'apps.creator_product',
    'apps.trending_video',
    'apps.payment_stripe',
    'apps.your_competitor',
    'apps.dashbord_analytics',
    "apps.newsletter",
    # 'querycount',
    'django_celery_beat',
    'corsheaders',

    # Google login
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    
    # 'django_extensions',

]



# django.contrib.sites
SOCIALACCOUNT_ADAPTER = "apps.users.adapter.SocialAccountAdapter"

SITE_ID = 1



# Rest Framework


# Rest framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}



from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=60),
}




MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'querycount.middleware.QueryCountMiddleware',

    #google login
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = 'projects.urls'

AUTH_USER_MODEL = 'users.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'projects.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'myproject',
#         'USER': 'myprojectuser',
#         'PASSWORD': 'password',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

import os
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_URL = '/static/'

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# Gmail SMTP server Settings

EMAIL_BACKEND = config('EMAIL_BACKEND')
EMAIL_HOST = config('EMAIL_HOST')  # Gmail SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')  # Gmail app password


STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = config('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')








OPENAI_API_KEY = config("OPENAI_API_KEY")


# Set CELERY_TASK_ALWAYS_EAGER=true locally only if you are not running a Celery worker.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", "false").lower() in (
    "1",
    "true",
    "yes",
)
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER


GOOGLE_CLIENT_ID=config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET=config("GOOGLE_CLIENT_SECRET")
YOUTUBE_REDIRECT_URI=config("YOUTUBE_REDIRECT_URI")
TEST_YOUTUBE_REDIRECT_URI = config("TEST_YOUTUBE_REDIRECT_URI")

YOUTUBE_API_KEY = config("YOUTUBE_API_KEY")

RAPIDAPI_KEY = config("RAPIDAPI_KEY")
RAPIDAPI_HOST = config("RAPIDAPI_HOST")

SPOTIFY_CLIENT_ID = config("SPOTIFY_CLIENT_ID")

SPOTIFY_CLIENT_SECRET = config("SPOTIFY_CLIENT_SECRET")






# django-allauth and dj-rest-auth settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID'),
            'secret': config('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'offline'},
    }
}

REST_USE_JWT = True  

ACCOUNT_EMAIL_VERIFICATION = "optional"  
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
SOCIALACCOUNT_AUTO_SIGNUP = True


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}



# TikTok OAuth settings

import os
TIKTOK_CLIENT_KEY = config("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = config("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = config("TIKTOK_REDIRECT_URI")
TEST_TIKTOK_REDIRECT_URI = config("TEST_TIKTOK_REDIRECT_URI")


# Youtube credentials
YOUTUBE_API_KEY=config('YOUTUBE_API_KEY')


# FACEBOOK OAUTH SETTINGS
FACEBOOK_APP_ID = config('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET')


INSTAGRAM_APP_ID=config('INSTAGRAM_APP_ID')
INSTAGRAM_APP_SECRET=config('INSTAGRAM_APP_SECRET')
INSTAGRAM_REDIRECT_URI=config('INSTAGRAM_REDIRECT_URI')
TEST_INSTAGRAM_REDIRECT_URI = config('TEST_INSTAGRAM_REDIRECT_URI')


SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# If you are using HTTPS (Required for TikTok production/hosted)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True



# Celery Settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'




# from django.urls import reverse_lazy
# from django.utils.translation import gettext_lazy as _

# UNFOLD = {
#     "SITE_TITLE": "Admin Dashboard",
#     "SITE_HEADER": "Admin Panel",
#     "DARK_MODE": True,

#     "SIDEBAR": {
#         "show_search": False,
#         "command_search": False,
#         "show_all_applications": False,

#         "navigation": [
#             # ================= MAIN =================
#             {
#                 "title": _("Navigation"),
#                 "separator": True,
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Dashboard"), "icon": "dashboard", "link": reverse_lazy("admin:index")},
#                 ],
#             },

#             # ================= USERS =================
#             {
#                 "title": _("Users"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Users"), "icon": "people", "link": reverse_lazy("admin:users_user_changelist")},
#                     {"title": _("TikTok OAuth Tokens"), "icon": "key", "link": reverse_lazy("admin:users_tiktokoauthtoken_changelist")},
#                     {"title": _("Instagram OAuth Tokens"), "icon": "key", "link": reverse_lazy("admin:users_instagramoauthtoken_changelist")},
#                 ],
#             },

#             # ================= SPOTIFY =================
#             {
#                 "title": _("Spotify"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Spotify Data"), "icon": "library_music", "link": reverse_lazy("admin:spotify_spotifydata_changelist")},
#                 ],
#             },

#             # ================= CREATORS EXPLORE =================
#             {
#                 "title": _("Creators Explore"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Creators"), "icon": "travel_explore", "link": reverse_lazy("admin:creators_explore_creator_changelist")},
#                 ],
#             },

#             # ================= BLOGS =================
#             {
#                 "title": _("Blogs"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Blog Posts"), "icon": "article", "link": reverse_lazy("admin:blogs_blogpost_changelist")},
#                 ],
#             },

#             # ================= VIRAL BUILDER =================
#             {
#                 "title": _("Viral Builder"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Videos"), "icon": "video_library", "link": reverse_lazy("admin:viral_builder_video_changelist")},
#                 ],
#             },

#             # ================= PARENTS =================
#             {
#                 "title": _("Parents"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Playlists"), "icon": "queue_music", "link": reverse_lazy("admin:parents_playlist_changelist")},
#                 ],
#             },

#             # ================= AUDIT =================
#             {
#                 "title": _("Audit"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Channel Audit Reports"), "icon": "fact_check", "link": reverse_lazy("admin:audit_channelauditreport_changelist")},
#                 ],
#             },

#             # ================= CREATOR PRODUCT =================
#             {
#                 "title": _("Creator Product"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Creator Products"), "icon": "inventory_2", "link": reverse_lazy("admin:creator_product_creatorproduct_changelist")},
#                 ],
#             },

#             # ================= TRENDING VIDEO =================
#             {
#                 "title": _("Trending Video (AI)"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("SmartMatch AI Data"), "icon": "smart_toy", "link": reverse_lazy("admin:trending_video_smartmatchaidata_changelist")},
#                     {"title": _("Top 10 UK Creators AI Data"), "icon": "leaderboard", "link": reverse_lazy("admin:trending_video_toptenukcreatorsaidata_changelist")},
#                     {"title": _("Safe Channels Curated"), "icon": "verified_user", "link": reverse_lazy("admin:trending_video_safechannelcurratedforchild_changelist")},
#                     {"title": _("Climbing The Chart"), "icon": "trending_up", "link": reverse_lazy("admin:trending_video_climbingthechart_changelist")},
#                 ],
#             },

#             # ================= YOUR COMPETITOR =================
#             {
#                 "title": _("Your Competitor"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Competitor Data"), "icon": "compare", "link": reverse_lazy("admin:your_competitor_competitordata_changelist")},
#                 ],
#             },

#             # ================= PAYMENT STRIPE =================
#             {
#                 "title": _("Payments (Stripe)"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Subscriptions"), "icon": "payments", "link": reverse_lazy("admin:payment_stripe_subscription_changelist")},
#                 ],
#             },

#             # ================= CELERY BEAT =================
#             {
#                 "title": _("Celery Beat"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Periodic Tasks"), "icon": "schedule", "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist")},
#                     {"title": _("Clocked Schedules"), "icon": "alarm", "link": reverse_lazy("admin:django_celery_beat_clockedschedule_changelist")},
#                     {"title": _("Crontab Schedules"), "icon": "event_repeat", "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist")},
#                     {"title": _("Solar Schedules"), "icon": "wb_sunny", "link": reverse_lazy("admin:django_celery_beat_solarschedule_changelist")},
#                     {"title": _("Interval Schedules"), "icon": "timer", "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist")},
#                 ],
#             },

#             # ================= AUTH & SECURITY =================
#             {
#                 "title": _("Auth & Security"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Groups"), "icon": "group", "link": reverse_lazy("admin:auth_group_changelist")},
#                     {"title": _("Outstanding Tokens"), "icon": "vpn_key", "link": reverse_lazy("admin:token_blacklist_outstandingtoken_changelist")},
#                     {"title": _("Blacklisted Tokens"), "icon": "block", "link": reverse_lazy("admin:token_blacklist_blacklistedtoken_changelist")},
#                 ],
#             },

#             # ================= DJANGO CORE =================
#             {
#                 "title": _("Django"),
#                 "collapsible": True,
#                 "items": [
#                     {"title": _("Sites"), "icon": "language", "link": reverse_lazy("admin:sites_site_changelist")},
#                     {"title": _("Email Addresses"), "icon": "email", "link": reverse_lazy("admin:account_emailaddress_changelist")},
#                     {"title": _("Social Apps"), "icon": "apps", "link": reverse_lazy("admin:socialaccount_socialapp_changelist")},
#                     {"title": _("Social Tokens"), "icon": "token", "link": reverse_lazy("admin:socialaccount_socialtoken_changelist")},
#                     {"title": _("Social Accounts"), "icon": "account_circle", "link": reverse_lazy("admin:socialaccount_socialaccount_changelist")},
#                     {"title": _("Auth Tokens"), "icon": "key", "link": reverse_lazy("admin:authtoken_tokenproxy_changelist")},
#                 ],
#             },
#         ],
#     },
# }





from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Admin Dashboard",
    "SITE_HEADER": "Admin Panel",
    "DARK_MODE": True,

    "SIDEBAR": {
        "show_search": False,
        "command_search": False,
        "show_all_applications": False,
        "navigation": [

            # ================= MAIN =================
            {
                "title": _("Navigation"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": _("Dashboard"), "icon": "dashboard", "link": reverse_lazy("admin:index")},
                ],
            },

            # ================= USERS =================
            {
                "title": _("Users"),
                "collapsible": True,
                "items": [
                    {"title": _("Users"), "icon": "people", "link": reverse_lazy("admin:users_user_changelist")},
                    {"title": _("TikTok OAuth Tokens"), "icon": "key", "link": reverse_lazy("admin:users_tiktokoauthtoken_changelist")},
                    {"title": _("Instagram OAuth Tokens"), "icon": "key", "link": reverse_lazy("admin:users_instagramoauthtoken_changelist")},
                    {"title": _("YouTube OAuth Tokens"), "icon": "key", "link": reverse_lazy("admin:users_youtubeoauthtoken_changelist")},
                ],
            },

            # ================= SPOTIFY =================
            {
                "title": _("Spotify"),
                "collapsible": True,
                "items": [
                    {"title": _("Spotify Data"), "icon": "library_music", "link": reverse_lazy("admin:spotify_spotifydata_changelist")},
                ],
            },

            # ================= CREATORS EXPLORE =================
            {
                "title": _("Creators Explore"),
                "collapsible": True,
                "items": [
                    {"title": _("Creators"), "icon": "travel_explore", "link": reverse_lazy("admin:creators_explore_creator_changelist")},
                ],
            },

            # ================= BLOGS =================
            {
                "title": _("Blogs"),
                "collapsible": True,
                "items": [
                    {"title": _("Blog Posts"), "icon": "article", "link": reverse_lazy("admin:blogs_blogpost_changelist")},
                ],
            },

            # ================= VIRAL BUILDER =================
            {
                "title": _("Viral Builder"),
                "collapsible": True,
                "items": [
                    {"title": _("Platform Accounts"), "icon": "account_circle", "link": reverse_lazy("admin:viral_builder_platformaccount_changelist")},
                    {"title": _("Viral Builder Runs"), "icon": "play_circle", "link": reverse_lazy("admin:viral_builder_viralbuilderrun_changelist")},
                    {"title": _("Viral Ideas"), "icon": "lightbulb", "link": reverse_lazy("admin:viral_builder_viralidea_changelist")},
                ],
            },

            # ================= PARENTS / SAFE PLAYLISTS =================
            {
                "title": _("Parents / Safe Playlists"),
                "collapsible": True,
                "items": [
                    {"title": _("Child Profiles"), "icon": "child_care", "link": reverse_lazy("admin:parents_childprofile_changelist")},
                    {"title": _("Playlists"), "icon": "queue_music", "link": reverse_lazy("admin:parents_playlist_changelist")},
                    {"title": _("Playlist Items"), "icon": "format_list_bulleted", "link": reverse_lazy("admin:parents_playlistitem_changelist")},
                    {"title": _("Playlist Explanations"), "icon": "info", "link": reverse_lazy("admin:parents_playlistexplanation_changelist")},
                    {"title": _("YouTube Video Cache"), "icon": "storage", "link": reverse_lazy("admin:parents_youtubevideocache_changelist")},
                    {"title": _("Job Runs"), "icon": "schedule", "link": reverse_lazy("admin:parents_jobrun_changelist")},
                    {"title": _("Follow Playlists"), "icon": "bookmark_add", "link": reverse_lazy("admin:parents_followplaylist_changelist")},
                    {"title": _("Playlist Channels"), "icon": "subscriptions", "link": reverse_lazy("admin:parents_playlistchannel_changelist")},
                    {"title": _("Reviews"), "icon": "rate_review", "link": reverse_lazy("admin:parents_review_changelist")},
                    {"title": _("Feedback"), "icon": "feedback", "link": reverse_lazy("admin:parents_feedback_changelist")},
                ],
            },

            # ================= AUDIT =================
            {
                "title": _("Audit"),
                "collapsible": True,
                "items": [
                    {"title": _("Channel Audit Reports"), "icon": "fact_check", "link": reverse_lazy("admin:audit_channelauditreport_changelist")},
                ],
            },

            # ================= CREATOR PRODUCT =================
            {
                "title": _("Creator Product"),
                "collapsible": True,
                "items": [
                    {"title": _("Creator Products"), "icon": "inventory_2", "link": reverse_lazy("admin:creator_product_creatorproduct_changelist")},
                ],
            },

            # ================= TRENDING VIDEO (AI) =================
            {
                "title": _("Trending Video (AI)"),
                "collapsible": True,
                "items": [
                    {"title": _("SmartMatch AI Data"), "icon": "smart_toy", "link": reverse_lazy("admin:trending_video_smartmatchaidata_changelist")},
                    {"title": _("Top 10 UK Creators AI Data"), "icon": "leaderboard", "link": reverse_lazy("admin:trending_video_toptenukcreatorsaidata_changelist")},
                    {"title": _("Safe Channels Curated"), "icon": "verified_user", "link": reverse_lazy("admin:trending_video_safechannelcurratedforchild_changelist")},
                    {"title": _("Climbing The Chart"), "icon": "trending_up", "link": reverse_lazy("admin:trending_video_climbingthechart_changelist")},
                ],
            },

            # ================= YOUR COMPETITOR =================
            {
                "title": _("Your Competitor"),
                "collapsible": True,
                "items": [
                    {"title": _("Competitor Data"), "icon": "compare", "link": reverse_lazy("admin:your_competitor_competitordata_changelist")},
                ],
            },

            # ================= PAYMENTS =================
            {
                "title": _("Payments (Stripe)"),
                "collapsible": True,
                "items": [
                    {"title": _("Subscriptions"), "icon": "payments", "link": reverse_lazy("admin:payment_stripe_subscription_changelist")},
                    {"title": _("Subscription Plans"), "icon": "loyalty", "link": reverse_lazy("admin:payment_stripe_subscriptionplan_changelist")},
                ],
            },

            # ================= CELERY BEAT =================
            {
                "title": _("Celery Beat"),
                "collapsible": True,
                "items": [
                    {"title": _("Periodic Tasks"), "icon": "schedule", "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist")},
                    {"title": _("Clocked Schedules"), "icon": "alarm", "link": reverse_lazy("admin:django_celery_beat_clockedschedule_changelist")},
                    {"title": _("Crontab Schedules"), "icon": "event_repeat", "link": reverse_lazy("admin:django_celery_beat_crontabschedule_changelist")},
                    {"title": _("Solar Schedules"), "icon": "wb_sunny", "link": reverse_lazy("admin:django_celery_beat_solarschedule_changelist")},
                    {"title": _("Interval Schedules"), "icon": "timer", "link": reverse_lazy("admin:django_celery_beat_intervalschedule_changelist")},
                ],
            },

            # ================= AUTH & SECURITY =================
            {
                "title": _("Auth & Security"),
                "collapsible": True,
                "items": [
                    {"title": _("Groups"), "icon": "group", "link": reverse_lazy("admin:auth_group_changelist")},
                    {"title": _("Outstanding Tokens"), "icon": "vpn_key", "link": reverse_lazy("admin:token_blacklist_outstandingtoken_changelist")},
                    {"title": _("Blacklisted Tokens"), "icon": "block", "link": reverse_lazy("admin:token_blacklist_blacklistedtoken_changelist")},
                ],
            },

            # ================= DJANGO CORE =================
            {
                "title": _("Django"),
                "collapsible": True,
                "items": [
                    {"title": _("Sites"), "icon": "language", "link": reverse_lazy("admin:sites_site_changelist")},
                    {"title": _("Email Addresses"), "icon": "email", "link": reverse_lazy("admin:account_emailaddress_changelist")},
                    {"title": _("Social Apps"), "icon": "apps", "link": reverse_lazy("admin:socialaccount_socialapp_changelist")},
                    {"title": _("Social Tokens"), "icon": "token", "link": reverse_lazy("admin:socialaccount_socialtoken_changelist")},
                    {"title": _("Social Accounts"), "icon": "account_circle", "link": reverse_lazy("admin:socialaccount_socialaccount_changelist")},
                    {"title": _("Auth Tokens"), "icon": "key", "link": reverse_lazy("admin:authtoken_tokenproxy_changelist")},
                ],
            },
            {
                "title": _("Custom Playlist"),  # Fixed spelling: palylist -> Playlist
                "collapsible": True,
                "items": [
                    {
                    "title": _("Playlist"), 
                    # FIX: Changed customplaylist__changelist to customplaylist_changelist
                    "link": reverse_lazy("admin:custom_playlist_customplaylist_changelist")
                    }
                ]
            } 
        ],
    },
}