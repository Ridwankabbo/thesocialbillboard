import googleapiclient.discovery
import googleapiclient.errors
from django.conf import settings
from google.oauth2.credentials import Credentials
from openai import OpenAI
import logging
import json

logger = logging.getLogger(__name__)

class YouTubeService:
    """
    Service class to interact with the YouTube Data API v3.
    """
    def __init__(self, access_token=None, api_key=None):
        self.credentials = Credentials(token=access_token) if access_token else None
        if api_key:
            self.youtube = googleapiclient.discovery.build(
                "youtube",
                "v3",
                developerKey=api_key
            )
        elif self.credentials:
            self.youtube = googleapiclient.discovery.build(
                "youtube",
                "v3",
                credentials=self.credentials
            )
        else:
            raise ValueError("YouTubeService requires either an access_token or api_key.")

    def _build_public_youtube(self):
        return googleapiclient.discovery.build(
            "youtube",
            "v3",
            developerKey=getattr(settings, "YOUTUBE_API_KEY", None)
        )

    def get_channel_data(self, channel_id):
        """
        Fetches basic channel statistics (subscribers, views, video count).
        """
        try:
            request = self.youtube.channels().list(
                part="statistics,snippet",
                id=channel_id
            )
            response = request.execute()

            if not response.get('items'):
                logger.warning(f"No channel data found for ID: {channel_id}")
                return None

            channel_info = response['items'][0]
            statistics = channel_info.get('statistics', {})
            snippet = channel_info.get('snippet', {})

            return {
                "channel_id": channel_id,
                "channel_name": snippet.get('title'),
                "description": snippet.get('description'),
                "published_at": snippet.get('publishedAt'),
                "subscriber_count": statistics.get('subscriberCount'),
                "view_count": statistics.get('viewCount'),
                "video_count": statistics.get('videoCount'),
                "hidden_subscriber_count": statistics.get('hiddenSubscriberCount', False)
            }
        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error fetching channel data for {channel_id}: {e}")
            raise Exception(f"YouTube API error: {e.content.decode('utf-8')}")
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching channel data for {channel_id}: {e}")
            raise

    def get_last_10_videos(self, channel_id):
        """
        Fetches the last 10 public videos for a channel via its uploads playlist.
        Returns a list of dicts containing title, description, tags, and published_at.
        """
        videos = []
        try:
            # 1. Resolve the uploads playlist ID from channel details
            channel_resp = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute()

            if not channel_resp.get("items"):
                logger.warning(f"No channel found for ID: {channel_id}")
                return videos

            uploads_playlist_id = (
                channel_resp["items"][0]
                .get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )

            if not uploads_playlist_id:
                logger.warning(f"No uploads playlist found for channel: {channel_id}")
                return videos

            # 2. Fetch the 10 most recent playlist items (video IDs)
            playlist_resp = self.youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=10
            ).execute()

            video_ids = [
                item["contentDetails"]["videoId"]
                for item in playlist_resp.get("items", [])
            ]

            if not video_ids:
                return videos

            # 3. Fetch full snippet (title, description, tags, publishedAt) in one call
            videos_resp = self.youtube.videos().list(
                part="snippet",
                id=",".join(video_ids)
            ).execute()

            for item in videos_resp.get("items", []):
                snippet = item.get("snippet", {})
                videos.append({
                    "video_id": item["id"],
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "tags": snippet.get("tags", []),
                    "published_at": snippet.get("publishedAt", ""),
                })

        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error fetching last 10 videos for {channel_id}: {e}")
            raise Exception(f"YouTube API error: {e.content.decode('utf-8')}")
        except Exception as e:
            logger.error(f"Unexpected error fetching last 10 videos for {channel_id}: {e}")
            raise

        return videos

    def get_channel_comments(self, channel_id, max_results=50):
        """
        Fetches comments from a channel's recent videos.
        Note: YouTube API does not directly provide a 'get all channel comments' endpoint.
        You typically fetch comments per video. This is a simplified approach,
        fetching comments from the latest few videos.
        For a comprehensive audit, you'd need to iterate through many videos.
        """
        comments = []
        try:
            # Get recent videos from the channel
            videos_request = self.youtube.search().list(
                part="id",
                channelId=channel_id,
                type="video",
                order="date", # Order by most recent
                maxResults=5 # Fetch comments from the 5 most recent videos
            )
            videos_response = videos_request.execute()
            video_ids = [item['id']['videoId'] for item in videos_response.get('items', [])]

            for video_id in video_ids:
                comments_request = self.youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    textFormat="plainText",
                    maxResults=max_results // len(video_ids) if video_ids else max_results # Distribute max_results
                )
                comments_response = comments_request.execute()
                for item in comments_response.get('items', []):
                    comments.append({
                        "video_id": video_id,
                        "author": item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        "text": item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        "published_at": item['snippet']['topLevelComment']['snippet']['publishedAt'],
                        "like_count": item['snippet']['topLevelComment']['snippet']['likeCount']
                    })
                if len(comments) >= max_results:
                    break # Stop if we've collected enough comments

        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error fetching comments for {channel_id}: {e}")
            message = str(e.content or b"").lower()
            if e.resp.status == 403 and ("commentsdisabled" in message or "insufficientpermissions" in message or "insufficient authentication scopes" in message):
                logger.warning(
                    "YouTube comments API returned 403 due to insufficient scopes; falling back to public API key if available."
                )
                if getattr(settings, "YOUTUBE_API_KEY", None):
                    return self._get_channel_comments_with_api_key(channel_id, max_results)

            if e.resp.status == 403 and "commentsdisabled" in message:
                logger.warning(f"Comments are disabled for some videos on channel {channel_id}.")
                return comments

            raise Exception(f"YouTube API error: {e.content.decode('utf-8')}")
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching comments for {channel_id}: {e}")
            raise
        return comments

    def _get_channel_comments_with_api_key(self, channel_id, max_results=50):
        comments = []
        try:
            public_youtube = self._build_public_youtube()
            videos_request = public_youtube.search().list(
                part="id",
                channelId=channel_id,
                type="video",
                order="date",
                maxResults=5
            )
            videos_response = videos_request.execute()
            video_ids = [item['id']['videoId'] for item in videos_response.get('items', [])]
            for video_id in video_ids:
                comments_request = public_youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    textFormat="plainText",
                    maxResults=max_results // len(video_ids) if video_ids else max_results
                )
                comments_response = comments_request.execute()
                for item in comments_response.get('items', []):
                    comments.append({
                        "video_id": video_id,
                        "author": item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        "text": item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        "published_at": item['snippet']['topLevelComment']['snippet']['publishedAt'],
                        "like_count": item['snippet']['topLevelComment']['snippet']['likeCount']
                    })
                if len(comments) >= max_results:
                    break
        except Exception as e:
            logger.warning(f"Public API key fallback for YouTube comments failed for {channel_id}: {e}")
        return comments


class OpenAIService:
    """
    Service class to interact with the OpenAI GPT-4.1 Mini API.
    """
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini" # Using gpt-4o-mini as requested

    def generate_niche_alignment_report(self, channel_data: dict, videos: list, report_date: str) -> dict:
        """
        Sends a single LLM request to assess whether the channel's recent content
        matches its stated business/niche.

        Args:
            channel_data: dict with at least 'channel_name' and 'description' keys.
            videos: list of dicts with keys title, description, tags, published_at.
            report_date: ISO date string for the report header (YYYY-MM-DD).

        Returns:
            dict with key 'report_summary' containing the formatted report text.
        """
        channel_name = channel_data.get("title") or channel_data.get("channel_name", "Unknown Channel")
        channel_description = channel_data.get("description", "No description provided.")

        # Build the video list section of the prompt
        video_lines = []
        for idx, video in enumerate(videos, start=1):
            tags_str = ", ".join(video.get("tags", [])) if video.get("tags") else "N/A"
            video_lines.append(
                f"{idx}. Title: \"{video.get('title', '')}\""
                f"\n   Published: {video.get('published_at', 'N/A')}"
                f"\n   Tags: {tags_str}"
                f"\n   Description: {(video.get('description') or '')[:300]}"
            )
        video_section = "\n\n".join(video_lines) if video_lines else "No videos available."

        system_message = (""" 
        You are an experienced YouTube content strategist.

        Your task is to evaluate whether a YouTube channel's recent content aligns with its business or niche.

        Rules:
        - Use ONLY the supplied channel description and video information.
        - Do NOT invent facts.
        - Do NOT assume analytics or engagement metrics.
        - If the niche cannot be confidently identified, explicitly say so.
        - Every observation MUST reference one or more actual video titles.
        - Recommendations must be specific to the supplied videos.
        - Respond back in JSON format.
        - Follow the requested output format exactly.
"""
        )

        user_message = f"""
Analyse the following YouTube channel.

Channel Name:
{channel_name}

Channel Description:
{channel_description or "No channel description provided."}

Report Date:
{report_date}

Recent Videos:
{video_section}

Your job is to answer one question:

"Does this channel's recent content match its business or niche?"

Generate the report using EXACTLY this structure.

# YouTube Niche Alignment Report

**Channel:** {channel_name}

**Detected Niche:** [Infer from description and recent videos. If unclear, state "Unclear".]

**Report Date:** {report_date}

## Verdict

Choose ONE of ONLY these values:

- Aligned
- Drifting
- Off-niche

Write 1–2 sentences explaining the verdict.

## What Is Working

Provide 2–3 observations.

Each observation MUST reference at least one actual video title.

Do not make generic statements.

## Where the Content Drifts

Provide 2–3 observations.

Each observation MUST reference at least one actual video title.

If there is no evidence of drifting, explicitly say so.

## Actionable Recommendations

Provide exactly 3 recommendations.

Recommendations must be based on the supplied videos and should help the creator improve niche consistency.

Do NOT mention subscriber counts, views, engagement, analytics, scores, or metrics.

Do NOT invent missing information.

Return ONLY the report.
""" 

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type":"json_object"},
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.5,
                max_tokens=1200,
            )
            ai_text = response.choices[0].message.content
            response = json.loads(ai_text)
            return {"report_summary": response}
        except Exception as e:
            logger.error(f"OpenAI API error generating niche alignment report: {e}")
            raise Exception(f"OpenAI API error: {e}")

    # ---------------------------------------------------------------------------
    # Legacy method kept for backward compatibility with other views
    # ---------------------------------------------------------------------------
    def generate_audit_insights(self, data):
        """
        Generates AI-powered audit insights based on channel data and report type.
        """
        channel_data = data.get("channel_data", {})
        comments_data = data.get("comments_data", [])
        report_type = data.get("report_type", "overall")
        custom_prompt = data.get("custom_prompt", "")

        # Construct the prompt based on report type
        system_message = "You are an expert YouTube channel auditor. Provide concise, actionable insights."
        user_message_parts = [
            f"Perform a {report_type} audit for the YouTube channel '{channel_data.get('channel_name', 'N/A')}' (ID: {channel_data.get('channel_id', 'N/A')})."
        ]

        user_message_parts.append(f"\nChannel Statistics:\n"
                                  f"Subscribers: {channel_data.get('subscriber_count', 'N/A')}\n"
                                  f"Total Views: {channel_data.get('view_count', 'N/A')}\n"
                                  f"Total Videos: {channel_data.get('video_count', 'N/A')}\n"
                                  f"Description: {channel_data.get('description', 'N/A')}\n")

        if report_type == 'overall':
            user_message_parts.append("Provide an overall audit covering strengths, weaknesses, and general recommendations.")
        elif report_type == 'sentiment':
            user_message_parts.append("Analyze the sentiment of the following comments. Provide a summary of positive, negative, and neutral sentiment, and key themes. Suggest improvements based on sentiment.")
            if comments_data:
                user_message_parts.append("\nSample Comments:\n" + "\n".join([f"- {c['text']}" for c in comments_data[:10]]))
            else:
                user_message_parts.append("\nNo comments data available for sentiment analysis.")
        elif report_type == 'engagement':
            user_message_parts.append("Evaluate engagement quality based on the channel's metrics and sample comments. Focus on comment frequency, quality of interaction, and potential areas for improvement.")
            if comments_data:
                user_message_parts.append("\nSample Comments (for engagement context):\n" + "\n".join([f"- {c['text']} (Likes: {c.get('like_count', 0)})" for c in comments_data[:10]]))
            else:
                user_message_parts.append("\nNo comments data available for engagement analysis.")
        elif report_type == 'ai_score':
            user_message_parts.append("Assign an AI score (1-100) based on content consistency, growth trends, audience engagement, and overall channel health. Provide a rationale for the score.")

        if custom_prompt:
            user_message_parts.append(f"\nCustom instruction: {custom_prompt}")

        user_message = "\n".join(user_message_parts)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            ai_text = response.choices[0].message.content
            return {"report_summary": ai_text}
        except Exception as e:
            logger.error(f"OpenAI API error generating insights: {e}")
            raise Exception(f"OpenAI API error: {e}")

