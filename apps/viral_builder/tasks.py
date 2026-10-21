from celery import shared_task
from django.utils import timezone

from apps.dashboard import youtube_utils
from apps.parents.models import JobRun

from .models import ViralBuilderRun, ViralIdea
from .services import (
    get_recent_youtube_videos,
    summarize_channel_themes,
    fetch_tiktok_signals,
    fetch_instagram_signals,
    generate_viral_ideas,
    basic_safety_filter,
    humanize_generation_error,
)


@shared_task(bind=True)
def viral_builder_generate(self, run_id: int, job_id: str | None = None):
    run = ViralBuilderRun.objects.select_related("channel_account", "user").get(id=run_id)
    job = None
    if job_id:
        job = JobRun.objects.filter(id=job_id, user=run.user).first()

    run.status = "running"
    run.error = ""
    run.save(update_fields=["status", "error"])
    if job:
        job.status = "running"
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

    try:
        channel_account = run.channel_account
        channel_id = channel_account.external_id
        channel_data = youtube_utils.fetch_youtube_channel_data(channel_id) or {}
        recent_videos = get_recent_youtube_videos(channel_id)
        themes = summarize_channel_themes(recent_videos)
        tiktok_signals = fetch_tiktok_signals(run.user)
        instagram_signals = fetch_instagram_signals(run.user)

        payload = {
            "channel": {
                "channel_id": channel_id,
                "title": channel_data.get("title"),
                "description": channel_data.get("description"),
                "stats": channel_data.get("stats"),
            },
            "recent_videos": recent_videos,
            "recent_topics": themes,
            "content_type": run.content_type,
            "goal": run.goal,
            "toggles": run.toggles,
            "tiktok_signals": tiktok_signals or {"connected": False},
            "instagram_signals": instagram_signals or {"connected": False},
        }

        run.meta = {"input": payload}
        run.save(update_fields=["meta"])

        ideas = generate_viral_ideas(payload)
        if not ideas:
            raise ValueError("OpenAI returned no ideas.")

        created = 0
        brand_safe_only = bool(run.toggles.get("brand_safe_only"))
        for idea in ideas:
            joined = " ".join([
                idea.get("headline", ""),
                idea.get("suggested_title", ""),
                idea.get("hook_structure", ""),
                idea.get("format_guidance", ""),
                idea.get("suggested_cta", ""),
            ])
            flags = set(idea.get("safety_flags", []) or [])
            flags.update(basic_safety_filter(joined))
            idea["safety_flags"] = list(flags)

            if brand_safe_only and flags:
                continue

            ViralIdea.objects.create(
                run=run,
                headline=idea.get("headline", "")[:255],
                suggested_title=idea.get("suggested_title", "")[:255],
                hook_structure=idea.get("hook_structure", ""),
                format_guidance=idea.get("format_guidance", ""),
                suggested_cta=idea.get("suggested_cta", ""),
                why_fits_channel=idea.get("why_fits_channel", ""),
                tags=idea.get("tags", []) or [],
                safety_flags=idea.get("safety_flags", []) or [],
                viral_gap=idea.get("viral_gap", {}) or {},
            )
            created += 1

        run.status = "done"
        run.finished_at = timezone.now()
        run.meta = {**(run.meta or {}), "ideas_created": created}
        run.save(update_fields=["status", "finished_at", "meta"])

        if job:
            job.status = "done"
            job.finished_at = timezone.now()
            job.meta = {**(job.meta or {}), "ideas_created": created}
            job.save(update_fields=["status", "finished_at", "meta"])

        return created

    except Exception as exc:
        friendly_error = humanize_generation_error(exc)
        run.status = "failed"
        run.error = friendly_error
        run.finished_at = timezone.now()
        run.meta = {**(run.meta or {}), "raw_error": str(exc)}
        run.save(update_fields=["status", "error", "finished_at", "meta"])

        if job:
            job.status = "failed"
            job.error = friendly_error
            job.finished_at = timezone.now()
            job.meta = {**(job.meta or {}), "raw_error": str(exc)}
            job.save(update_fields=["status", "error", "finished_at", "meta"])

        raise
