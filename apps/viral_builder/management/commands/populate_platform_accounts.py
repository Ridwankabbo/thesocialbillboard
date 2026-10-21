from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.viral_builder.models import PlatformAccount
from apps.creator_dashboard.models import CreatorProfile, YoutubeCredentials, TiktokCredentials, InstagramCredentials, PlatformChoices

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate PlatformAccount for existing users with connected accounts'

    def handle(self, *args, **options):
        # For YouTube
        youtube_creds = YoutubeCredentials.objects.select_related('profile__user', 'profile__youtube_profile').filter(platform=PlatformChoices.YOUTUBE)
        for cred in youtube_creds:
            user = cred.profile.user
            yt_profile = getattr(cred.profile, 'youtube_profile', None)
            if yt_profile and yt_profile.youtube_channel_id:
                PlatformAccount.objects.update_or_create(
                    user=user,
                    platform="youtube",
                    external_id=yt_profile.youtube_channel_id,
                    defaults={
                        "display_name": yt_profile.channel_title or yt_profile.youtube_channel_id,
                        "profile_url": f"https://www.youtube.com/channel/{yt_profile.youtube_channel_id}",
                        "meta": {},
                    }
                )
                self.stdout.write(f'Created YouTube PlatformAccount for {user.email}')
            else:
                self.stdout.write(f'Skipped YouTube for {user.email} - no channel_id')

        # For TikTok
        tiktok_creds = TiktokCredentials.objects.select_related('profile__user', 'profile__tiktok_profile').filter(platform=PlatformChoices.TIKTOK)
        for cred in tiktok_creds:
            user = cred.profile.user
            tt_profile = getattr(cred.profile, 'tiktok_profile', None)
            if tt_profile and tt_profile.tiktok_user_id:
                PlatformAccount.objects.update_or_create(
                    user=user,
                    platform="tiktok",
                    external_id=tt_profile.tiktok_user_id,
                    defaults={
                        "display_name": tt_profile.username or tt_profile.tiktok_user_id,
                        "profile_url": f"https://www.tiktok.com/@{tt_profile.username}" if tt_profile.username else "",
                        "meta": {},
                    }
                )
                self.stdout.write(f'Created TikTok PlatformAccount for {user.email}')
            else:
                self.stdout.write(f'Skipped TikTok for {user.email}')

        # For Instagram
        instagram_creds = InstagramCredentials.objects.select_related('profile__user', 'profile__instagram_profile').filter(platform=PlatformChoices.INSTAGRAM)
        for cred in instagram_creds:
            user = cred.profile.user
            ig_profile = getattr(cred.profile, 'instagram_profile', None)
            if ig_profile and ig_profile.instagram_user_id:
                PlatformAccount.objects.update_or_create(
                    user=user,
                    platform="instagram",
                    external_id=ig_profile.instagram_user_id,
                    defaults={
                        "display_name": ig_profile.username or ig_profile.instagram_user_id,
                        "profile_url": f"https://www.instagram.com/{ig_profile.username}" if ig_profile.username else "",
                        "meta": {},
                    }
                )
                self.stdout.write(f'Created Instagram PlatformAccount for {user.email}')
            else:
                self.stdout.write(f'Skipped Instagram for {user.email}')

        self.stdout.write('Population complete')