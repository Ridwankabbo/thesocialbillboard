import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from apps.users.views import refresh_youtube_access_token
from .models import JobRun, Playlist, PlaylistExplanation, PlaylistItem, YouTubeVideoCache
from .services import (
    analyze_video_for_age_safety,
    build_playlist,
    describe_playlist_generation_failure,
    fetch_transcript,
    fetch_video_details,
    generate_suitability_explanation,
    is_video_suitable,
    select_suitable_playlist_items,
    youtube_search_candidates,
)

logger = logging.getLogger(__name__)

MAX_CANDIDATES_TO_EVALUATE = int(
    getattr(settings, "PARENTS_PLAYLIST_MAX_CANDIDATE_EVALUATIONS", 20)
)
EVALUATION_WORKERS = int(getattr(settings, "PARENTS_PLAYLIST_EVALUATION_WORKERS", 5))


def _evaluate_candidate(
    cand: Dict,
    filters: Dict,
    access_token: Optional[str],
) -> Optional[Dict]:
    close_old_connections()
    try:
        cache = YouTubeVideoCache.objects.filter(video_id=cand["video_id"]).first()
        if not cache:
            return None

        if not cache.transcript_text:
            transcript_text, _source = fetch_transcript(
                cache.video_id,
                language=filters.get("language"),
                youtube_access_token=access_token,
            )
            if transcript_text:
                cache.transcript_text = transcript_text
                cache.save(update_fields=["transcript_text", "updated_at"])

        analysis = analyze_video_for_age_safety(
            cache,
            child_age_band=filters.get("age_band", ""),
            filters=filters,
        )
        cache.analysis_json = analysis
        cache.save(update_fields=["analysis_json", "updated_at"])

        item = {
            "video_id": cache.video_id,
            "title": cache.title,
            "duration": cache.duration,
            "channel_id": cache.channel_id,
            "thumbnail_url": cand.get("thumbnail_url", ""),
            "video_url": f"https://www.youtube.com/watch?v={cache.video_id}",
            "has_transcript": bool(cache.transcript_text),
        }
        return {"item": item, "analysis": analysis}
    except Exception as exc:
        logger.warning("Candidate evaluation failed for %s: %s", cand.get("video_id"), exc)
        return None
    finally:
        close_old_connections()


def _run_playlist_generation(playlist: Playlist, job: Optional[JobRun]) -> None:
    playlist.status = "generating"
    playlist.save(update_fields=["status"])

    if job:
        job.status = "running"
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

    filters = playlist.filters_json or {}
    candidates = youtube_search_candidates(filters)
    candidates = candidates[:MAX_CANDIDATES_TO_EVALUATE]
    video_ids = [c["video_id"] for c in candidates]
    fetch_video_details(video_ids)

    access_token = None
    user = playlist.user or (playlist.child_profile.parent if playlist.child_profile else None)
    if user and getattr(user, "youtube_oauth", None):
        try:
            access_token = refresh_youtube_access_token(user.youtube_oauth).access_token
        except Exception:
            access_token = None

    evaluations: List[Dict] = []
    workers = min(EVALUATION_WORKERS, max(len(candidates), 1))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_evaluate_candidate, cand, filters, access_token): cand
            for cand in candidates
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                evaluations.append(result)

    suitable_strict = sum(
        1 for entry in evaluations if is_video_suitable(entry["analysis"], filters)
    )
    suitable_relaxed = sum(
        1 for entry in evaluations if is_video_suitable(entry["analysis"], filters, relaxed=True)
    )
    enriched = select_suitable_playlist_items(evaluations, filters)

    selected = build_playlist(enriched, playlist.session_length or 10)

    PlaylistItem.objects.filter(playlist=playlist).delete()
    PlaylistExplanation.objects.filter(playlist=playlist).delete()

    items_to_create = []
    for idx, item in enumerate(selected, start=1):
        items_to_create.append(
            PlaylistItem(
                playlist=playlist,
                youtube_video_id=item["video_id"],
                position=idx,
                title=item["title"],
                duration=item["duration"],
                channel_id=item["channel_id"],
                thumbnail_url=item["thumbnail_url"],
                video_url=item["video_url"],
            )
        )

    if items_to_create:
        PlaylistItem.objects.bulk_create(items_to_create)

    explanation_text = generate_suitability_explanation(
        playlist=playlist,
        items=selected,
        child_age_band=filters.get("age_band", ""),
        filters=filters,
    )
    PlaylistExplanation.objects.create(
        playlist=playlist,
        why_suitable_text=explanation_text,
    )

    failure_message = ""
    if items_to_create:
        playlist.status = "ready"
    else:
        playlist.status = "failed"
        failure_message = describe_playlist_generation_failure(
            candidates=len(candidates),
            evaluated=len(evaluations),
            suitable_strict=suitable_strict,
            suitable_relaxed=suitable_relaxed,
            selected=len(selected),
        )

    playlist.save(update_fields=["status"])

    if job:
        job.status = "done" if items_to_create else "failed"
        job.finished_at = timezone.now()
        if failure_message:
            job.error = failure_message
            job.meta = {
                **(job.meta or {}),
                "generation_stats": {
                    "candidates": len(candidates),
                    "evaluated": len(evaluations),
                    "suitable_strict": suitable_strict,
                    "suitable_relaxed": suitable_relaxed,
                    "selected": len(selected),
                },
            }
            job.save(update_fields=["status", "finished_at", "error", "meta"])
        else:
            job.save(update_fields=["status", "finished_at"])


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def generate_parent_playlist(self, playlist_id: int, job_id: Optional[str] = None) -> None:
    playlist = Playlist.objects.filter(id=playlist_id).first()
    if not playlist:
        return

    job = JobRun.objects.filter(id=job_id).first() if job_id else None
    if playlist.status == "canceled" or (job and job.status == "canceled"):
        if playlist.status != "canceled":
            playlist.status = "canceled"
            playlist.save(update_fields=["status"])
        if job and not job.finished_at:
            job.finished_at = timezone.now()
            job.save(update_fields=["finished_at"])
        return

    try:
        _run_playlist_generation(playlist, job)
    except Exception as exc:
        logger.error("Playlist generation failed: %s", exc)
        playlist.status = "failed"
        playlist.save(update_fields=["status"])
        if job:
            job.status = "failed"
            job.error = str(exc) or exc.__class__.__name__
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error", "finished_at"])
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def regenerate_parent_playlist(self, playlist_id: int, job_id: Optional[str] = None) -> None:
    generate_parent_playlist.run(playlist_id, job_id)

from .services import get_transcript
from .ai_logic import analyze_transcript
@shared_task
def process_playlist_task(job_id):

    job = JobRun.objects.get(id=job_id)
    job.status = "running"
    job.started_at = timezone.now()
    job.save()

    try:
        playlist_id = job.meta["playlist_id"]
        playlist = Playlist.objects.get(id=playlist_id)

        videos = PlaylistItem.objects.filter(playlist=playlist)

        results = []

        for item in videos:

            video, created = YouTubeVideoCache.objects.get_or_create(
                video_id=item.youtube_video_id,
                defaults={
                    "title": item.title,
                    "duration": item.duration,
                    "channel_id": item.channel_id
                }
            )

            # STEP 1: TRANSCRIPT
            transcript_data = get_transcript(video.video_id)

            video.transcript_text = transcript_data["full_text"]
            video.transcript_word_count = transcript_data["word_count"]
            video.transcript_coverage_score = transcript_data["coverage"]
            video.save()

            # STEP 2: AI ANALYSIS
            analysis = analyze_transcript(
                transcript_data["full_text"],
                video.title,
                playlist.age_range(),
                playlist.session_length,
                
            )

            video.analysis_json = analysis
            video.save()

            results.append({
                "video_id": video.video_id,
                "analysis": analysis
            })

        job.status = "done"
        job.finished_at = timezone.now()
        job.meta["results"] = results
        job.save()

    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.finished_at = timezone.now()
        job.save()