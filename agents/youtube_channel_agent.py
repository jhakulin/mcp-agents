import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from azure.storage.blob import BlobServiceClient
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .protocols import BaseAgent, AgentResponse, AgentResponseStatus
from .storage import LocalFileStorage, BlobStorage, StateManager

logger = logging.getLogger(__name__)


class YouTubeChannelAgent(BaseAgent):
    """Agent that monitors YouTube channels for latest videos."""
    
    def __init__(
        self, 
        api_key: str, 
        blob_service_client: Optional[BlobServiceClient] = None,
        use_local_storage: bool = False,
        local_storage_path: Optional[str] = None
    ):
        super().__init__(
            name="YouTubeChannelAgent",
            description="Monitors YouTube channels and retrieves latest videos"
        )
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Configure storage based on parameters
        if use_local_storage or blob_service_client is None:
            storage_path = local_storage_path or os.getenv("YOUTUBE_MONITOR_STATE_FILE", ".youtube_monitor_state.json")
            storage = LocalFileStorage(storage_path)
            logger.info(f"Using local file storage: {storage_path}")
        else:
            storage = BlobStorage(blob_service_client)
            logger.info("Using Azure Blob storage")
        
        self.state_manager = StateManager(storage)
        self.state_manager.load()
    
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process YouTube channel URLs to get latest videos.
        
        Args:
            input_data: Dict with 'channels' key containing comma-separated channel URLs
                       or 'channel_urls' key containing list of channel URLs
            
        Returns:
            AgentResponse with latest videos data or error
        """
        # Validate and extract channels
        channels = self._extract_channels(input_data)
        if not channels:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="No valid channels provided",
                error_type="validation_error"
            )
        
        try:
            # Process each channel
            results = []
            new_videos = []
            errors = []
            
            for channel_url in channels:
                try:
                    channel_id = self._resolve_channel_id(channel_url)
                    if not channel_id:
                        errors.append({"channel": channel_url, "error": "Could not resolve channel ID"})
                        continue
                    
                    # Get latest video
                    video_info = self._get_latest_video(channel_id)
                    if not video_info:
                        errors.append({"channel": channel_url, "error": "No videos found"})
                        continue
                    
                    # Check if this is a new video
                    last_seen = self.state_manager.get_last_seen(channel_id)
                    is_new = last_seen != video_info["video_id"]
                    
                    # Update state
                    if is_new:
                        self.state_manager.set_last_seen(channel_id, video_info["video_id"])
                        new_videos.append(video_info)
                    
                    results.append({
                        **video_info,
                        "is_new": is_new,
                        "channel_url": channel_url
                    })
                    
                except Exception as e:
                    logger.exception(f"Error processing channel {channel_url}")
                    errors.append({"channel": channel_url, "error": str(e)})
            
            # Save state
            self.state_manager.save()
            
            # Determine response status
            if not results and errors:
                return AgentResponse(
                    status=AgentResponseStatus.FAILED,
                    error="Failed to process any channels",
                    error_type="processing_error",
                    data={"errors": errors}
                )
            elif results and errors:
                status = AgentResponseStatus.PARTIAL
            else:
                status = AgentResponseStatus.SUCCESS
            
            return AgentResponse(
                status=status,
                data={
                    "videos": results,
                    "new_videos": new_videos,
                    "errors": errors if errors else None,
                    "total_channels": len(channels),
                    "successful_channels": len(results)
                }
            )
            
        except Exception as e:
            logger.exception("Unexpected error in YouTubeChannelAgent")
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error=str(e),
                error_type="unexpected_error"
            )
    
    def _extract_channels(self, input_data: Dict[str, Any]) -> List[str]:
        """Extract channel URLs from input data."""
        if not input_data:
            return []
        
        # Try different input formats
        if "channels" in input_data:
            # Comma-separated string
            channels_str = input_data["channels"]
            if isinstance(channels_str, str):
                return [url.strip() for url in channels_str.split(",") if url.strip()]
        
        if "channel_urls" in input_data:
            # List of URLs
            urls = input_data["channel_urls"]
            if isinstance(urls, list):
                return [url.strip() for url in urls if isinstance(url, str) and url.strip()]
        
        return []
    
    def _resolve_channel_id(self, channel_url: str) -> Optional[str]:
        """Resolve channel URL to channel ID, using cache when possible."""
        # Check cache first
        cached_id = self.state_manager.get_resolved(channel_url)
        if cached_id:
            return cached_id
        
        # Extract from URL patterns
        channel_id = self._extract_channel_id_from_url(channel_url)
        
        if not channel_id:
            # Try to resolve via API using channel name
            channel_name = self._extract_channel_name_from_url(channel_url)
            if channel_name:
                channel_id = self._resolve_channel_name_to_id(channel_name)
        
        # Cache the result
        if channel_id:
            self.state_manager.set_resolved(channel_url, channel_id)
        
        return channel_id
    
    def _extract_channel_id_from_url(self, url: str) -> Optional[str]:
        """Extract channel ID from URL if it contains one."""
        # Pattern for channel ID (starts with UC and has 24 chars total)
        id_match = re.search(r'(UC[a-zA-Z0-9_-]{22})', url)
        if id_match:
            return id_match.group(1)
        return None
    
    def _extract_channel_name_from_url(self, url: str) -> Optional[str]:
        """Extract channel name from URL patterns like @channelname."""
        # Pattern for @username
        at_match = re.search(r'@([a-zA-Z0-9_-]+)', url)
        if at_match:
            return at_match.group(1)
        
        # Pattern for /c/channelname or /user/username
        path_match = re.search(r'/(?:c|user)/([a-zA-Z0-9_-]+)', url)
        if path_match:
            return path_match.group(1)
        
        return None
    
    def _resolve_channel_name_to_id(self, channel_name: str) -> Optional[str]:
        """Resolve channel name to channel ID using YouTube API."""
        try:
            # Search for channel
            request = self.youtube.search().list(
                part="snippet",
                q=channel_name,
                type="channel",
                maxResults=1
            )
            response = request.execute()
            
            if response.get("items"):
                return response["items"][0]["snippet"]["channelId"]
        except HttpError as e:
            logger.error(f"YouTube API error resolving channel name {channel_name}: {e}")
        except Exception as e:
            logger.exception(f"Error resolving channel name {channel_name}")
        
        return None
    
    def _get_latest_video(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest video from a channel."""
        try:
            # Get channel's uploads playlist
            request = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            )
            response = request.execute()
            
            if not response.get("items"):
                return None
            
            uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # Get latest video from uploads playlist
            request = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=1
            )
            response = request.execute()
            
            if not response.get("items"):
                return None
            
            video_item = response["items"][0]
            snippet = video_item["snippet"]
            
            return {
                "channel_id": channel_id,
                "channel_title": snippet["channelTitle"],
                "video_id": snippet["resourceId"]["videoId"],
                "video_title": snippet["title"],
                "video_description": snippet.get("description", "")[:200] + "...",
                "published_at": snippet["publishedAt"],
                "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                "video_url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
            }
            
        except HttpError as e:
            logger.error(f"YouTube API error getting latest video for channel {channel_id}: {e}")
        except Exception as e:
            logger.exception(f"Error getting latest video for channel {channel_id}")
        
        return None