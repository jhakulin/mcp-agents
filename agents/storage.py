# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class StateStorage(ABC):
    """Abstract base class for state storage implementations."""
    
    @abstractmethod
    def load(self) -> Dict[str, Dict]:
        """Load state from storage."""
        pass
    
    @abstractmethod
    def save(self, state: Dict[str, Dict]) -> None:
        """Save state to storage."""
        pass


class LocalFileStorage(StateStorage):
    """Local file-based state storage for testing and development."""
    
    def __init__(self, file_path: str = ".youtube_monitor_state.json"):
        self.file_path = Path(file_path)
    
    def load(self) -> Dict[str, Dict]:
        """Load state from local file."""
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as ex:
            logger.warning(f"Error loading local state file: {ex}")
        
        logger.info("State file not found; starting fresh.")
        return {"resolved": {}, "last_seen": {}}
    
    def save(self, state: Dict[str, Dict]) -> None:
        """Save state to local file."""
        try:
            # Create directory if needed
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with pretty formatting for easier debugging
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as ex:
            logger.error(f"Error saving local state file: {ex}")
            raise


class BlobStorage(StateStorage):
    """Azure Blob Storage-based state storage."""
    
    def __init__(self, blob_service: BlobServiceClient, container: str = "youtube-monitor", blob_name: str = "last_seen.json"):
        self.blob_service = blob_service
        self.container = container
        self.blob_name = blob_name
    
    def load(self) -> Dict[str, Dict]:
        """Load state from blob storage."""
        container_client = self.blob_service.get_container_client(self.container)
        blob_client = container_client.get_blob_client(self.blob_name)
        try:
            data = blob_client.download_blob().readall()
            return json.loads(data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data)
        except ResourceNotFoundError:
            logger.info("State blob not found; starting fresh.")
            return {"resolved": {}, "last_seen": {}}
        except Exception as ex:
            logger.warning(f"Error loading state blob: {ex}")
            return {"resolved": {}, "last_seen": {}}
    
    def save(self, state: Dict[str, Dict]) -> None:
        """Save state to blob storage."""
        container_client = self.blob_service.get_container_client(self.container)
        try:
            container_client.create_container()
        except Exception:
            # ignore if already exists
            pass
        blob_client = container_client.get_blob_client(self.blob_name)
        blob_client.upload_blob(json.dumps(state), overwrite=True)


class StateManager:
    """
    Maintains state JSON with structure:
    {
        "resolved": { "input-identifier": "UC..." },
        "last_seen": { "UC...": "videoId" }
    }
    """
    def __init__(self, storage: StateStorage):
        self.storage = storage
        self._state: Dict[str, Dict] = {"resolved": {}, "last_seen": {}}

    def load(self) -> None:
        """Load state from configured storage."""
        self._state = self.storage.load()

    def save(self) -> None:
        """Save state to configured storage."""
        self.storage.save(self._state)

    # resolved cache methods
    def get_resolved(self, identifier: str) -> Optional[str]:
        return self._state.get("resolved", {}).get(identifier)

    def set_resolved(self, identifier: str, channel_id: str) -> None:
        self._state.setdefault("resolved", {})[identifier] = channel_id

    # last seen video methods
    def get_last_seen(self, channel_id: str) -> Optional[str]:
        return self._state.get("last_seen", {}).get(channel_id)

    def set_last_seen(self, channel_id: str, video_id: str) -> None:
        self._state.setdefault("last_seen", {})[channel_id] = video_id
