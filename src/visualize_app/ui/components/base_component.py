"""
Base class for all UI components.
"""

import logging
from abc import ABC
from abc import abstractmethod
from typing import Optional

import customtkinter as ctk

from visualize_app.core import AppState
from visualize_app.core import EventBus

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """
    Base class for all UI components.

    Provides common functionality:
    - Access to app state
    - Event bus for communication
    - Theme update support
    - Lifecycle management
    """

    def __init__(self, parent: ctk.CTk, app_state: AppState, event_bus: EventBus):
        """
        Initialize component.

        Args:
            parent: Parent tkinter widget
            app_state: Shared application state
            event_bus: Event bus for component communication
        """
        self.parent = parent
        self.app_state = app_state
        self.event_bus = event_bus
        self.widget: Optional[ctk.CTkFrame] = None

        logger.debug(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def build(self) -> ctk.CTkFrame:
        """
        Build and return the component's root widget.

        Returns:
            Root widget for this component
        """
        pass

    @abstractmethod
    def update_theme(self):
        """Update component colors for current theme."""
        pass

    def destroy(self):
        """Clean up component resources."""
        if self.widget:
            self.widget.destroy()
            self.widget = None
        logger.debug(f"Destroyed {self.__class__.__name__}")

    def is_built(self) -> bool:
        """Check if component is built."""
        return self.widget is not None
