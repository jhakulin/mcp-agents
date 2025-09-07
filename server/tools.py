"""Tool definitions for the MCP server."""

import os
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI

# Import agents from parent directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agents import (
    YouTubeTranscriptionAgent,
    TextSummarizerAgent,
    YouTubeChannelAgent
)

# Import the server instance
from .server import mcp

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agent instances (created on first use)
_agents = {
    "youtube_transcription": None,
    "text_summarizer": None,
    "youtube_channel": None
}


def get_youtube_transcription_agent() -> YouTubeTranscriptionAgent:
    """Get or create YouTube transcription agent."""
    if _agents["youtube_transcription"] is None:
        _agents["youtube_transcription"] = YouTubeTranscriptionAgent()
    return _agents["youtube_transcription"]


def get_text_summarizer_agent() -> TextSummarizerAgent:
    """Get or create text summarizer agent."""
    if _agents["text_summarizer"] is None:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required")
        openai_client = OpenAI(api_key=openai_api_key)
        _agents["text_summarizer"] = TextSummarizerAgent(client=openai_client)
    return _agents["text_summarizer"]


def get_youtube_channel_agent() -> YouTubeChannelAgent:
    """Get or create YouTube channel agent."""
    if _agents["youtube_channel"] is None:
        youtube_api_key = os.environ.get("YOUTUBE_API_KEY")
        if not youtube_api_key:
            raise RuntimeError("YOUTUBE_API_KEY environment variable is required")
        _agents["youtube_channel"] = YouTubeChannelAgent(
            api_key=youtube_api_key,
            use_local_storage=True
        )
    return _agents["youtube_channel"]


@mcp.tool()
def youtube_transcribe(url: Optional[str] = None, video_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract transcript from YouTube video.
    
    Args:
        url: YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID)
        video_id: YouTube video ID (11 characters)
        
    Returns:
        Dictionary containing transcript text and metadata
    """
    if not url and not video_id:
        return {"error": "Either 'url' or 'video_id' must be provided"}
    
    try:
        agent = get_youtube_transcription_agent()
        
        input_data = {}
        if url:
            input_data["url"] = url
        if video_id:
            input_data["video_id"] = video_id
        
        logger.info(f"Extracting transcript for: {url or video_id}")
        response = agent.process(input_data)
        
        if response.success and response.data:
            return {
                "transcript": response.data.get("transcript", ""),
                "video_id": response.data.get("video_id", ""),
                "metadata": response.metadata
            }
        else:
            return {"error": response.error or "Failed to extract transcript"}
    except Exception as e:
        logger.error(f"Error in youtube_transcribe: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def summarize_text(
    text: str,
    max_length: int = 500,
    style: str = "concise",
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Summarize text using OpenAI.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of summary (default: 500)
        style: Summary style - 'concise', 'detailed', or 'bullet_points' (default: 'concise')
        model: OpenAI model to use (default: 'gpt-4o-mini')
        
    Returns:
        Dictionary containing the summary
    """
    if not text:
        return {"error": "Text is required"}
    
    try:
        agent = get_text_summarizer_agent()
        agent.model = model  # Update model if specified
        
        logger.info(f"Summarizing text ({len(text)} chars) with style: {style}")
        response = agent.process({
            "text": text,
            "max_length": max_length,
            "style": style
        })
        
        if response.success and response.data:
            return {
                "summary": response.data.get("summary", response.data.get("article", "")),
                "style": style,
                "model": model,
                "metadata": response.metadata
            }
        else:
            return {"error": response.error or "Failed to summarize text"}
    except Exception as e:
        logger.error(f"Error in summarize_text: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def youtube_channels_monitor(channels: List[str]) -> Dict[str, Any]:
    """
    Monitor YouTube channels for new videos.
    
    Args:
        channels: List of YouTube channel URLs or IDs
        
    Returns:
        Dictionary containing channel updates and new videos
    """
    if not channels:
        return {"error": "At least one channel is required"}
    
    try:
        agent = get_youtube_channel_agent()
        
        # Convert list to comma-separated string if needed
        channels_str = ", ".join(channels) if isinstance(channels, list) else channels
        
        logger.info(f"Monitoring {len(channels)} YouTube channels")
        response = agent.process({"channels": channels_str})
        
        if response.success and response.data:
            data = response.data
            return {
                "successful_channels": data.get("successful_channels", 0),
                "total_channels": data.get("total_channels", 0),
                "new_videos": data.get("new_videos", []),
                "all_videos": data.get("videos", []),
                "errors": data.get("errors", []),
                "metadata": response.metadata
            }
        else:
            return {"error": response.error or "Failed to monitor channels"}
    except Exception as e:
        logger.error(f"Error in youtube_channels_monitor: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def youtube_channel_latest(channel_id: str) -> Dict[str, Any]:
    """
    Get the latest video from a specific YouTube channel.
    
    Args:
        channel_id: YouTube channel ID or URL
        
    Returns:
        Dictionary containing latest video information
    """
    if not channel_id:
        return {"error": "Channel ID is required"}
    
    try:
        agent = get_youtube_channel_agent()
        
        logger.info(f"Getting latest video from channel: {channel_id}")
        response = agent.process({"channels": channel_id})
        
        if response.success and response.data:
            videos = response.data.get("videos", [])
            if videos:
                latest_video = videos[0]
                return {
                    "channel_title": latest_video.get("channel_title", ""),
                    "video_title": latest_video.get("video_title", ""),
                    "video_url": latest_video.get("video_url", ""),
                    "video_id": latest_video.get("video_id", ""),
                    "published_at": latest_video.get("published_at", ""),
                    "is_new": latest_video.get("is_new", False)
                }
            else:
                return {"error": "No videos found for this channel"}
        else:
            return {"error": response.error or "Failed to get channel videos"}
    except Exception as e:
        logger.error(f"Error in youtube_channel_latest: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def youtube_summarize_latest(
    channels: List[str],
    max_videos: int = 5,
    summary_style: str = "concise"
) -> Dict[str, Any]:
    """
    Get and summarize the latest videos from YouTube channels.
    
    Args:
        channels: List of YouTube channel URLs or IDs
        max_videos: Maximum number of videos to process (default: 5)
        summary_style: Summary style for video transcripts (default: 'concise')
        
    Returns:
        Dictionary containing summaries of latest videos
    """
    try:
        # First, get latest videos from channels
        channel_result = youtube_channels_monitor(channels)
        
        if "error" in channel_result:
            return channel_result
        
        summaries = []
        videos_to_process = channel_result.get("new_videos", [])[:max_videos]
        
        if not videos_to_process:
            videos_to_process = channel_result.get("all_videos", [])[:max_videos]
        
        for video in videos_to_process:
            try:
                # Get transcript
                transcript_result = youtube_transcribe(video_id=video.get("video_id"))
                
                if "error" not in transcript_result:
                    transcript = transcript_result.get("transcript", "")
                    
                    # Summarize transcript
                    summary_result = summarize_text(
                        text=transcript,
                        max_length=500,
                        style=summary_style
                    )
                    
                    if "error" not in summary_result:
                        summaries.append({
                            "channel": video.get("channel_title", ""),
                            "title": video.get("video_title", ""),
                            "url": video.get("video_url", ""),
                            "published": video.get("published_at", ""),
                            "summary": summary_result.get("summary", "")
                        })
                        
            except Exception as e:
                logger.error(f"Error processing video {video.get('video_title', 'Unknown')}: {e}")
        
        return {
            "channels_processed": channel_result.get("successful_channels", 0),
            "videos_found": len(videos_to_process),
            "summaries_generated": len(summaries),
            "summaries": summaries
        }
    except Exception as e:
        logger.error(f"Error in youtube_summarize_latest: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
def health_check() -> Dict[str, Any]:
    """
    Check the health status of the YouTube tools server.
    
    Returns:
        Dictionary containing health status and API key availability
    """
    return {
        "status": "healthy",
        "server_name": "YouTubeTools",
        "server_version": "0.1.0",
        "apis_configured": {
            "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
            "youtube_api_key": bool(os.environ.get("YOUTUBE_API_KEY"))
        }
    }