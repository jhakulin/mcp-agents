# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum


class AgentResponseStatus(Enum):
    """Standard status codes for agent responses."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class AgentResponse:
    """Standard response format for all agents."""
    status: AgentResponseStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def success(self) -> bool:
        """Check if the response indicates success."""
        return self.status == AgentResponseStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format for backward compatibility."""
        result = {
            "success": self.success,
            "status": self.status.value
        }
        if self.data is not None:
            result.update(self.data)
        if self.error is not None:
            result["error"] = self.error
        if self.error_type is not None:
            result["error_type"] = self.error_type
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result


@runtime_checkable
class Agent(Protocol):
    """Protocol defining the interface that all agents must implement."""
    
    @property
    def name(self) -> str:
        """Return the name of the agent."""
        ...
    
    @property
    def description(self) -> str:
        """Return a description of what the agent does."""
        ...
    
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process the input and return a standardized response.
        
        Args:
            input_data: Dictionary containing the input data for the agent
            
        Returns:
            AgentResponse object with results or error information
        """
        ...


class BaseAgent(ABC):
    """Base class providing common functionality for agents."""
    
    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Must be implemented by subclasses."""
        pass
