import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import CreatorProfile
from .service import refresh_profile_data

logger = logging.getLogger(__name__)

@shared_task
def sync_all_creators_profiles(force=False):
    """
    Periodic Celery task to synchronize subscriber/follower metrics and media
    for all registered creators across TikTok, YouTube, and Instagram.
    Rate-limited to every 1 hour per profile unless force=True.
    """
    profiles = CreatorProfile.objects.all()
    success_count = 0
    skipped_count = 0
    error_count = 0

    logger.info(f"Starting scheduled synchronization for {profiles.count()} creator profiles.")

    for profile in profiles:
        try:
            if not force and profile.updated_at and timezone.now() - profile.updated_at < timedelta(hours=1):
                skipped_count += 1
                continue

            refresh_profile_data(profile)
            profile.updated_at = timezone.now()
            profile.save(update_fields=['updated_at'])
            success_count += 1
            logger.info(f"Successfully synchronized profile for user: {profile.user.email}")
        except Exception as e:
            error_count += 1
            logger.error(f"Error synchronizing profile for user {profile.user.email}: {str(e)}")

    logger.info(f"Scheduled profile sync complete. Successes: {success_count}, Skipped: {skipped_count}, Failures: {error_count}.")
    return f"Synced {success_count}, skipped {skipped_count}, failed {error_count}."


@shared_task
def sync_single_creator_profile(profile_id, force=False):
    """
    Task to synchronize a single creator profile by ID.
    Can be triggered asynchronously. Rate-limited to every 15 minutes unless force=True.
    """
    try:
        profile = CreatorProfile.objects.get(pk=profile_id)
        if not force and profile.updated_at and timezone.now() - profile.updated_at < timedelta(minutes=15):
            logger.info(f"Skipping sync for user {profile.user.email} - synchronized recently at {profile.updated_at}.")
            return f"Skipped (fresh since {profile.updated_at})"

        refresh_profile_data(profile)
        profile.updated_at = timezone.now()
        profile.save(update_fields=['updated_at'])
        logger.info(f"Successfully synchronized single profile for user: {profile.user.email}")
        return f"Successfully synchronized profile for {profile.user.email}"
    except CreatorProfile.DoesNotExist:
        logger.error(f"CreatorProfile with ID {profile_id} does not exist.")
        return f"Profile with ID {profile_id} not found."
    except Exception as e:
        logger.error(f"Error synchronizing profile {profile_id}: {str(e)}")
        return f"Error: {str(e)}"
