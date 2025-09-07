import logging
import re
from typing import Any, Dict, List, Sequence
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .protocols import BaseAgent, AgentResponse, AgentResponseStatus

logger = logging.getLogger(__name__)


class YouTubeTranscriptionAgent(BaseAgent):
    """Agent responsible for extracting transcripts from YouTube videos.
    
        Accepts either a YouTube URL or a direct video ID as input.
    """
    
    def __init__(self):
        super().__init__(
            name="YouTubeTranscriptionAgent",
            description="Extracts transcripts from YouTube videos using their URLs or video IDs"
        )
    
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process YouTube URL or video ID to extract transcript.
        
        Args:
            input_data: Dict with either:
                - 'url' key containing YouTube URL
                - 'video_id' key containing YouTube video ID
            
        Returns:
            AgentResponse with transcript data or error
        """
        # Validate input
        if not input_data:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="Input data is required",
                error_type="validation_error"
            )
        
        # Check for video_id first (more direct)
        video_id = None
        if "video_id" in input_data:
            video_id = input_data["video_id"]
            if not isinstance(video_id, str):
                return AgentResponse(
                    status=AgentResponseStatus.FAILED,
                    error="Video ID must be a string",
                    error_type="validation_error"
                )
            if not video_id or len(video_id) != 11:
                return AgentResponse(
                    status=AgentResponseStatus.FAILED,
                    error="Invalid video ID format. Video ID must be exactly 11 characters",
                    error_type="validation_error"
                )
        
        # If no video_id, check for URL
        elif "url" in input_data:
            url = input_data["url"]
            if not isinstance(url, str):
                return AgentResponse(
                    status=AgentResponseStatus.FAILED,
                    error="URL must be a string",
                    error_type="validation_error"
                )
            
            # Extract video ID from URL
            try:
                video_id = self._extract_video_id(url)
            except Exception as exc:
                logger.debug("extract_video_id error", exc_info=exc)
                return AgentResponse(
                    status=AgentResponseStatus.FAILED,
                    error=str(exc),
                    error_type="invalid_url"
                )
        
        else:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="Either 'url' or 'video_id' is required in input data",
                error_type="validation_error"
            )
        
        # Fetch transcript
        try:
            raw_segments = self._fetch_raw(video_id)
        except TranscriptsDisabled as exc:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error=str(exc),
                error_type="transcripts_disabled"
            )
        except NoTranscriptFound as exc:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error=str(exc),
                error_type="no_transcript"
            )
        except VideoUnavailable as exc:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error=str(exc),
                error_type="video_unavailable"
            )
        except Exception as exc:
            logger.exception("Unexpected error fetching transcript for %s", video_id)
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error=str(exc),
                error_type="fetch_error"
            )
        
        # Convert segments to text
        transcript = self._segments_to_text(raw_segments)
        if not transcript:
            return AgentResponse(
                status=AgentResponseStatus.FAILED,
                error="No captions found for video",
                error_type="empty_transcript"
            )
        
        return AgentResponse(
            status=AgentResponseStatus.SUCCESS,
            data={
                "video_id": video_id,
                "transcript": transcript
            }
        )
    
    @staticmethod
    def _extract_video_id(url: str) -> str:
        """Extract YouTube video ID from various URL formats."""
        if not url:
            raise ValueError("Empty URL provided")

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        # Standard watch?v=VIDEOID
        if "youtube.com" in hostname:
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                vid = qs["v"][0]
                if len(vid) == 11:
                    return vid
            # /embed/VIDEOID, /v/VIDEOID
            parts = parsed.path.split("/")
            for idx, part in enumerate(parts):
                if part in ("embed", "v") and idx + 1 < len(parts):
                    candidate = parts[idx + 1]
                    if len(candidate) == 11:
                        return candidate

        # Short URL youtu.be/VIDEOID
        if "youtu.be" in hostname:
            candidate = parsed.path.lstrip("/")
            if candidate:
                candidate = candidate.split("?")[0].split("/")[0]
                if re.match(r"^[0-9A-Za-z_-]{11}", candidate):
                    return candidate[:11]

        # Fallback: first 11-char ID found anywhere
        m = re.search(r"([0-9A-Za-z_-]{11})", url)
        if m:
            return m.group(1)

        raise ValueError(f"Could not extract YouTube video ID from URL: {url}")
    
    def _fetch_raw(self, video_id: str) -> List[Dict[str, Any]]:
        """Fetch raw transcript segments using YouTubeTranscriptApi."""
        if not video_id:
            raise ValueError("video_id is required")

        yt = YouTubeTranscriptApi()
        data = yt.fetch(video_id=video_id)
        
        try:
            raw = data.to_raw_data()
        except Exception:
            # In case the fetch result is already a raw list/dict
            if isinstance(data, list):
                return data
            raise
        return raw
    
    @staticmethod
    def _segments_to_text(segments: Sequence[Dict[str, Any]]) -> str:
        """Join segment texts into a single normalized string."""
        return " ".join(
            seg.get("text", "").strip() 
            for seg in segments 
            if seg.get("text")
        ).strip()