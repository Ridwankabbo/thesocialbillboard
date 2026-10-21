from apps.creator_dashboard.models import CreatorProfile, TiktokProfileMedia, YoutubeProfileMedia, InstagramProfileMedia
from .models import LeaderboardEntry
from django.db.models import Case, Sum, Avg, Count, When, Subquery, OuterRef, Q
from django.utils import timezone
from datetime import timedelta


from django.db.models import (
    Sum, F, ExpressionWrapper, FloatField,
    Window, IntegerField, Case, When, Value, BigIntegerField
)
from django.db.models.functions import RowNumber, Cast, Coalesce
from django.db.models.fields.json import KeyTextTransform


def get_leaderboard_data(platform=None, time=None):
    queryset = CreatorProfile.objects.filter(
        Q(tiktok_profile__isnull=False) |
        Q(youtube_profile__isnull=False) |
        Q(instagram_profile__isnull=False) 
    )
    # queryset = CreatorProfile.objects.all()

    # Time threshold for 30-day growth rate
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Subqueries for YouTube
    yt_views = Subquery(
        YoutubeProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    yt_likes = Subquery(
        YoutubeProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('likes_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    yt_comments = Subquery(
        YoutubeProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('comment_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    yt_views_recent = Subquery(
        YoutubeProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__gte=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    yt_views_older = Subquery(
        YoutubeProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__lt=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )

    # Subqueries for TikTok
    tt_views = Subquery(
        TiktokProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    tt_likes = Subquery(
        TiktokProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('likes_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    tt_comments = Subquery(
        TiktokProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('comment_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    tt_views_recent = Subquery(
        TiktokProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__gte=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    tt_views_older = Subquery(
        TiktokProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__lt=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )

    # Subqueries for Instagram
    ig_views = Subquery(
        InstagramProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    ig_likes = Subquery(
        InstagramProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('likes_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    ig_comments = Subquery(
        InstagramProfileMedia.objects.filter(profile=OuterRef('pk'))
        .values('profile')
        .annotate(total=Sum('comment_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    ig_views_recent = Subquery(
        InstagramProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__gte=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )
    ig_views_older = Subquery(
        InstagramProfileMedia.objects.filter(profile=OuterRef('pk'), created_at__lt=thirty_days_ago)
        .values('profile')
        .annotate(total=Sum('view_count'))
        .values('total')[:1],
        output_field=IntegerField()
    )

    if platform:
        plat = platform.upper()
        if plat == 'YOUTUBE':
            queryset = queryset.annotate(
                total_subscribers=Coalesce('youtube_profile__subscribers_count', 0),
                total_views=Coalesce(yt_views, 0),
                total_likes=Coalesce(yt_likes, 0),
                total_comments=Coalesce(yt_comments, 0),
                platform=Value('YOUTUBE'),
                recent_views=Coalesce(yt_views_recent, 0),
                older_views=Coalesce(yt_views_older, 0),
            )
        elif plat == 'TIKTOK':
            queryset = queryset.annotate(
                total_subscribers=Coalesce('tiktok_profile__followers_count', 0),
                total_views=Coalesce(tt_views, 0),
                total_likes=Coalesce(tt_likes, 0),
                total_comments=Coalesce(tt_comments, 0),
                platform=Value('TIKTOK'),
                recent_views=Coalesce(tt_views_recent, 0),
                older_views=Coalesce(tt_views_older, 0),
            )
        elif plat == 'INSTAGRAM':
            queryset = queryset.annotate(
                total_subscribers=Coalesce('instagram_profile__followers_count', 0),
                total_views=Coalesce(ig_views, 0),
                total_likes=Coalesce(ig_likes, 0),
                total_comments=Coalesce(ig_comments, 0),
                platform=Value('INSTAGRAM'),
                recent_views=Coalesce(ig_views_recent, 0),
                older_views=Coalesce(ig_views_older, 0),
            )
        else:
            queryset = queryset.annotate(
                total_subscribers=Value(0, output_field=IntegerField()),
                total_views=Value(0, output_field=IntegerField()),
                total_likes=Value(0, output_field=IntegerField()),
                total_comments=Value(0, output_field=IntegerField()),
                platform=Value('NONE'),
                recent_views=Value(0, output_field=IntegerField()),
                older_views=Value(0, output_field=IntegerField()),
            )
    else:
        # Pre-calculate counts of subscribers/followers
        queryset = queryset.annotate(
            yt_subs=Coalesce('youtube_profile__subscribers_count', 0),
            tt_subs=Coalesce('tiktok_profile__followers_count', 0),
            ig_subs=Coalesce('instagram_profile__followers_count', 0),
        )

        # Determine which platform has the most subscribers/followers
        queryset = queryset.annotate(
            chosen_platform=Case(
                When(Q(yt_subs__gte=F('tt_subs')) & Q(yt_subs__gte=F('ig_subs')), then=Value('YOUTUBE')),
                When(Q(tt_subs__gte=F('yt_subs')) & Q(tt_subs__gte=F('ig_subs')), then=Value('TIKTOK')),
                When(Q(ig_subs__gte=F('yt_subs')) & Q(ig_subs__gte=F('tt_subs')), then=Value('INSTAGRAM')),
                default=Value('YOUTUBE')
            )
        )

        # Retrieve stats only for that specific platform
        queryset = queryset.annotate(
            total_subscribers=Case(
                When(chosen_platform='YOUTUBE', then=F('yt_subs')),
                When(chosen_platform='TIKTOK', then=F('tt_subs')),
                When(chosen_platform='INSTAGRAM', then=F('ig_subs')),
                default=Value(0),
                output_field=BigIntegerField()
            ),
            total_views=Case(
                When(chosen_platform='YOUTUBE', then=Coalesce(yt_views, 0)),
                When(chosen_platform='TIKTOK', then=Coalesce(tt_views, 0)),
                When(chosen_platform='INSTAGRAM', then=Coalesce(ig_views, 0)),
                default=Value(0),
                output_field=IntegerField()
            ),
            total_likes=Case(
                When(chosen_platform='YOUTUBE', then=Coalesce(yt_likes, 0)),
                When(chosen_platform='TIKTOK', then=Coalesce(tt_likes, 0)),
                When(chosen_platform='INSTAGRAM', then=Coalesce(ig_likes, 0)),
                default=Value(0),
                output_field=IntegerField()
            ),
            total_comments=Case(
                When(chosen_platform='YOUTUBE', then=Coalesce(yt_comments, 0)),
                When(chosen_platform='TIKTOK', then=Coalesce(tt_comments, 0)),
                When(chosen_platform='INSTAGRAM', then=Coalesce(ig_comments, 0)),
                default=Value(0),
                output_field=IntegerField()
            ),
            recent_views=Case(
                When(chosen_platform='YOUTUBE', then=Coalesce(yt_views_recent, 0)),
                When(chosen_platform='TIKTOK', then=Coalesce(tt_views_recent, 0)),
                When(chosen_platform='INSTAGRAM', then=Coalesce(ig_views_recent, 0)),
                default=Value(0),
                output_field=IntegerField()
            ),
            older_views=Case(
                When(chosen_platform='YOUTUBE', then=Coalesce(yt_views_older, 0)),
                When(chosen_platform='TIKTOK', then=Coalesce(tt_views_older, 0)),
                When(chosen_platform='INSTAGRAM', then=Coalesce(ig_views_older, 0)),
                default=Value(0),
                output_field=IntegerField()
            ),
            platform=F('chosen_platform')
        )

    queryset = queryset.annotate(
        engagement_rate=Case(
            When(total_views=0, then=Value(0.0)),
            default=ExpressionWrapper(
                (F('total_likes') + F('total_comments')) * 100.0 / Cast(F('total_views'), FloatField()),
                output_field=FloatField()
            ),
            output_field=FloatField()
        ),
        growth_rate=Case(
            When(older_views=0, recent_views=0, then=Value(0.0)),
            When(older_views=0, then=Value(100.0)),
            default=ExpressionWrapper(
                (Cast(F('recent_views'), FloatField()) - Cast(F('older_views'), FloatField())) * 100.0 / Cast(F('older_views'), FloatField()),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    )

    queryset = queryset.annotate(
        rank=Window(
            expression=RowNumber(),
            order_by=[
                F('engagement_rate').desc(),
                F('total_subscribers').desc(),
                F('total_views').desc(),
                F('growth_rate').desc(),
                F('pk').asc(),
            ],
        )
    ).order_by('rank')
    return queryset


