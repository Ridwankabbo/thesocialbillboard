import os
import random
import googleapiclient.discovery
import googleapiclient.errors
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import openai
import logging
import json
from rest_framework import permissions
# Set up logging
logger = logging.getLogger(__name__)

class BaseAPIView(APIView):
    """
    Base API View providing standardized success and error response formats.
    """
    def success_response(self, message="Thank you for your request", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {
                "success": True,
                "message": message,
                "status_code": status_code,
                "data": data or {}
            },
            status=status_code
        )

    def error_response(self, message="I am sorry for your request", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {
                "success": False,
                "message": message,
                "status_code": status_code,
                "data": data or {}
            },
            status=status_code
        )

class ChannelComparisonView(BaseAPIView): # Inherit from BaseAPIView
    permission_classes = [permissions.IsAuthenticated]  
    """
    API View to compare two YouTube channels.
    """

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to compare two YouTube channels.
        Accepts 'channel_name_1' and 'channel_name_2' from query parameters or request body.
        Optionally 'days' for day-wise comparison (7, 15, or 30 days).
        If channel_name_1 is not provided, uses the authenticated user's youtube_link.
        """
        # Get channel names from query params or request body
        channel_name_1 = (
            request.query_params.get('channel_name_1') or
            request.data.get('channel_name_1') or
            request.user.youtube_link
        )
        channel_name_2 = (
            request.query_params.get('channel_name_2') or
            request.data.get('channel_name_2')
        )
        days = request.data.get('days') or request.query_params.get('days')

        # Validate both channels are provided
        if not channel_name_1:
            return self.error_response(
                message="Please provide 'channel_name_1' via query params, request body, or set your YouTube link in your profile.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not channel_name_2:
            return self.error_response(
                message="Please provide 'channel_name_2' via query params or request body.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if days is not None:
            try:
                days = int(days)
                if days not in [7, 15, 30]:
                    return self.error_response(
                        message="Invalid 'days' parameter. Must be 7, 15, or 30.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return self.error_response(
                    message="Invalid 'days' parameter. Must be an integer.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        youtube_api_key = config('YOUTUBE_API_KEY')
        openai_api_key = config('OPENAI_API_KEY')

        if not youtube_api_key:
            logger.error("YOUTUBE_API_KEY not found in environment variables.")
            return self.error_response(
                message="YouTube API key is not configured.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            return self.error_response(
                message="OpenAI API key is not configured.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Initialize YouTube API client
        try:
            youtube = googleapiclient.discovery.build(
                "youtube", "v3", developerKey=youtube_api_key
            )
        except Exception as e:
            logger.error(f"Error initializing YouTube API: {e}")
            return self.error_response(
                message="Failed to initialize YouTube API client.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        channel_data = {}
        errors = []

        # --- Fetch data for Channel 1 ---
        data_1, error_1 = self._get_youtube_data(youtube, channel_name_1, days)
        if error_1:
            errors.append(f"Channel 1 ({channel_name_1}): {error_1}")
        else:
            channel_data['channel_1'] = data_1

        # --- Fetch data for Channel 2 ---
        data_2, error_2 = self._get_youtube_data(youtube, channel_name_2, days)
        if error_2:
            errors.append(f"Channel 2 ({channel_name_2}): {error_2}")
        else:
            channel_data['channel_2'] = data_2

        if errors:
            return self.error_response(
                message="Youtube token reached its limit or other errors occurred while fetching channel data.",
                data={"errors": errors},    
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Generate AI scores
        if 'channel_1' in channel_data:
            ai_score_1, ai_explanation_1 = self._get_ai_score(channel_data['channel_1'])
            channel_data['channel_1']['ai_score'] = ai_score_1
            channel_data['channel_1']['ai_explanation'] = ai_explanation_1

        if 'channel_2' in channel_data:
            ai_score_2, ai_explanation_2 = self._get_ai_score(channel_data['channel_2'])
            channel_data['channel_2']['ai_score'] = ai_score_2
            channel_data['channel_2']['ai_explanation'] = ai_explanation_2

        return self.success_response(
            message="Comparison data for YouTube channels fetched successfully.",
            data=channel_data,
            status_code=status.HTTP_200_OK
        )

    def _get_youtube_data(self, youtube_client, channel_name, days):
        """
        Fetches comprehensive data for a given YouTube channel name.
        First resolves name to ID, then fetches channel stats.
        Includes simulated day-wise growth.
        """
        try:
            # Resolve channel ID from name
            # channel_id, id_error = self._get_youtube_channel_id_from_name(youtube_client, channel_name)
            # print("channel id: ",channel_name)
            channel_id = channel_name
            # if id_error:
            #     return None, id_error

            # Get channel statistics and snippet (description)
            channel_response = youtube_client.channels().list(
                part="statistics,snippet,contentDetails",
                id=channel_id
            ).execute()

            if not channel_response.get('items'):
                return None, f"YouTube channel '{channel_name}' not found or invalid ID."

            channel_info = channel_response['items'][0]
            statistics = channel_info.get('statistics', {})
            snippet = channel_info.get('snippet', {})
            content_details = channel_info.get('contentDetails', {})

            total_subscribers = int(statistics.get('subscriberCount', 0))
            total_views = int(statistics.get('viewCount', 0))
            channel_description = snippet.get('description', '')
            uploads_playlist_id = content_details.get('relatedPlaylists', {}).get('uploads')
            # if not uploads_playlist_id:
            #     logger.warning(
            #         f"No uploads playlist found for channel {channel_id}"
            #     )

            # Calculate view-to-subscriber ratio
            view_to_subscriber_ratio = total_views / total_subscribers if total_subscribers > 0 else 0

            # Simulate engagement insight (as requested)
            engagement_insight = f"Simulated engagement: {random.randint(5, 15)}% average view duration."

            highest_viewed_video = {"title": "N/A", "view_count": 0}

            if uploads_playlist_id:
                # Get videos from the uploads playlist
                try:
                    playlist_items_response = youtube_client.playlistItems().list(
                        part="snippet",
                        playlistId=uploads_playlist_id,
                        maxResults=50 # Fetch up to 50 videos to find the highest viewed
                    ).execute()
                except googleapiclient.errors.HttpError as e:
                    playlist_items_response = {"items": []}
                
                video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_items_response.get('items', [])]

                if video_ids:
                    # Get statistics for these videos
                    videos_response = youtube_client.videos().list(
                        part="statistics,snippet",
                        id=",".join(video_ids)
                    ).execute()
                    
                    if not videos_response:
                        videos_response = {"items": []}
                    max_views = 0
                    for video_item in videos_response.get('items', []):
                        video_title = video_item['snippet']['title']
                        video_views = int(video_item['statistics'].get('viewCount', 0))
                        if video_views > max_views:
                            max_views = video_views
                            highest_viewed_video = {"title": video_title, "view_count": max_views}
            else:
                logger.warning(f"No uploads playlist found for YouTube channel: {channel_name}")

            # Simulate day-wise growth if 'days' parameter is provided
            growth_data = {}
            if days:
                # Simulate growth as a small percentage of total
                sub_growth_rate = random.uniform(0.001, 0.01) * days # 0.1% to 1% growth per day
                view_growth_rate = random.uniform(0.005, 0.02) * days # 0.5% to 2% growth per day
                
                growth_data[f'subscribers_growth_last_{days}_days'] = int(total_subscribers * sub_growth_rate)
                growth_data[f'views_growth_last_{days}_days'] = int(total_views * view_growth_rate)

            return {
                "platform": "youtube",
                "identifier": channel_name,
                "total_subscribers": total_subscribers,
                "total_views": total_views,
                "highest_engagement_post": highest_viewed_video,
                "view_to_subscriber_ratio": round(view_to_subscriber_ratio, 2),
                "engagement_insight": engagement_insight,
                "description": channel_description,
                **growth_data # Add growth data to the dictionary
            }, None

        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error for channel {channel_name}: {e}")
            return None, f"YouTube API error: {e.resp.status} - {e.content.decode('utf-8')}"
        except Exception as e:
            logger.error(f"An unexpected error occurred for YouTube channel {channel_name}: {e}")
            return None, f"An unexpected error occurred: {e}"

    def _get_youtube_channel_id_from_name(self, youtube_client, channel_name):
        """
        Searches for a YouTube channel by name and returns its ID.
        """
        try:
            search_response = youtube_client.search().list(
                q=channel_name,
                type="channel",
                part="id,snippet",
                maxResults=1
            ).execute()

            items = search_response.get('items', [])
            if not items:
                return None, f"No YouTube channel found for name '{channel_name}'."

            channel_id = items[0]['id']['channelId']
            return channel_id, None

        except googleapiclient.errors.HttpError as e:
            logger.error(f"YouTube API error searching for channel '{channel_name}': {e}")
            return None, f"YouTube API error searching for channel '{channel_name}': {e.resp.status} - {e.content.decode('utf-8')}"
        except Exception as e:
            logger.error(f"An unexpected error occurred while searching for YouTube channel '{channel_name}': {e}")
            return None, f"An unexpected error occurred: {e}"

    def _get_ai_score(self, account_info):
        """
        Generates an AI score and extended insights for an account using OpenAI's gpt-4o-mini.
        Returns AI score, explanation, growth comparison, platform performance,
        engagement metrics, and key insights.
        """
        try:
            client = openai.OpenAI(api_key=config('OPENAI_API_KEY'))

            # Platform-based terminology
            platform_name = account_info.get('platform', 'account').capitalize()
            subscriber_term = "Subscribers"
            view_term = "Views"
            post_term = "Video"

            # Add growth info dynamically
            growth_info = ""
            for key, value in account_info.items():
                if "growth_last_" in key and isinstance(value, int):
                    growth_info += f"- {key.replace('_', ' ').title()}: {value}\n"

            # Prompt for GPT
            prompt = (
                f"Analyze the following {platform_name} account data and provide insights. "
                f"Return a JSON with ONLY these keys:\n"
                f"- score (0-100)\n"
                f"- explanation (string)\n"
                f"- growth_comparison (array of 4 objects: week, value)\n"
                f"- platform_performance (array of objects: each has platform + stats)\n"
                f"- engagement_metrics (array of objects: each has metric, value)\n"
                f"- key_insights (object with engagement_gap, growth_opportunity, audience_insight)\n\n"
                f"Account Data for {account_info['identifier']}:\n"
                f"- Total {subscriber_term}: {account_info['total_subscribers']}\n"
                f"- Total {view_term}: {account_info['total_views']}\n"
                f"- {view_term}-to-{subscriber_term} ratio: {account_info['view_to_subscriber_ratio']}\n"
                f"- Engagement insight (simulated): {account_info['engagement_insight']}\n"
                f"- Highest Engagement {post_term}: '{account_info['highest_engagement_post']['title']}' "
                f"with {account_info['highest_engagement_post']['view_count']} views.\n"
                f"{growth_info}"
                f"- Description: '{account_info['description']}'\n\n"
                f"⚠️ IMPORTANT: Return only clean JSON with the above structure. "
                f"No text, no explanation outside JSON."
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output JSON only."},
                    {"role": "user", "content": prompt}
                ]
            )

            json_response_text = response.choices[0].message.content
            try:
                ai_data = json.loads(json_response_text)

                # Ensure defaults if missing
                result = {
                    "score": max(0, min(100, ai_data.get("score", 0))),
                    "explanation": ai_data.get("explanation", "No explanation provided."),
                    "growth_comparison": ai_data.get("growth_comparison", [
                        {"week": "Week 1", "value": 0},
                        {"week": "Week 2", "value": 0},
                        {"week": "Week 3", "value": 0},
                        {"week": "Week 4", "value": 0}
                    ]),
                    "platform_performance": ai_data.get("platform_performance", [
                        {"platform": "YouTube", "subscribers": 0, "views": 0},
                        {"platform": "Instagram", "followers": 0, "engagement": "0%"},
                        {"platform": "TikTok", "followers": 0, "engagement": "0%"}
                    ]),
                    "engagement_metrics": ai_data.get("engagement_metrics", [
                        {"metric": "Engagement", "value": "0%"},
                        {"metric": "Growth", "value": 0},
                        {"metric": "Views", "value": 0},
                        {"metric": "Followers", "value": {"youtube": 0, "instagram": 0, "tiktok": 0}},
                        {"metric": "Retention", "value": "No data"},
                        {"metric": "Quality", "value": "Unknown"}
                    ]),
                    "key_insights": ai_data.get("key_insights", {
                        "engagement_gap": "No data",
                        "growth_opportunity": "No data",
                        "audience_insight": "No data"
                    })
                }
                return result["score"], result

            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from OpenAI: {json_response_text}")
                return 0, {"explanation": "Failed to generate AI score due to malformed response."}
            except AttributeError:
                logger.error(f"Unexpected OpenAI response structure: {response}")
                return 0, {"explanation": "Failed to generate AI score due to unexpected response structure."}

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return 0, {"explanation": f"OpenAI API error: {e}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred during AI score generation: {e}")
            return 0, {"explanation": f"An unexpected error occurred: {e}"}