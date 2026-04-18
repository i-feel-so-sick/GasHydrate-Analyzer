"""
Event bus for loose coupling between components.
"""

import logging
from typing import Any
from typing import Callable
from typing import Dict
from typing import List

logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple event bus for component communication.

    Allows components to communicate without direct dependencies,
    implementing the Observer pattern.

    Events:
        - file:selected - User selected a file
        - file:loaded - File data loaded successfully
        - file:clear - Clear all data
        - plot:switch - Switch to different plot type
        - plot:generated - Plots were generated
        - settings:changed - Plot settings changed
        - theme:changed - Theme switched
        - sidebar:toggle - Sidebar visibility toggled
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, callback: Callable[[Any], None]):
        """
        Subscribe to an event.

        Args:
            event: Event name
            callback: Function to call when event is published
        """
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
        logger.debug(f"Subscribed to event: {event}")

    def unsubscribe(self, event: str, callback: Callable):
        """
        Unsubscribe from an event.

        Args:
            event: Event name
            callback: Function to remove
        """
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)
            logger.debug(f"Unsubscribed from event: {event}")

    def publish(self, event: str, data: Any = None):
        """
        Publish an event to all subscribers.

        Args:
            event: Event name
            data: Optional data to pass to subscribers
        """
        if event in self._listeners:
            logger.debug(f"Publishing event: {event} to {len(self._listeners[event])} listeners")
            for callback in self._listeners[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}", exc_info=True)
        else:
            logger.debug(f"No listeners for event: {event}")

    def clear(self):
        """Clear all event listeners."""
        self._listeners.clear()
        logger.debug("Cleared all event listeners")
