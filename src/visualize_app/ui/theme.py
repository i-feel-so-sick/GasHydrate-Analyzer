"""
Theme management for the application.
"""

import logging

import customtkinter as ctk

logger = logging.getLogger(__name__)

# Color themes
LIGHT_THEME = {
    "bg_dark": "#f8f9fa",
    "bg_secondary": "#ffffff",
    "bg_card": "#f0f4f8",
    "accent_primary": "#3b82f6",
    "accent_secondary": "#2563eb",
    "accent_success": "#10b981",
    "accent_success_hover": "#059669",
    "accent_warning": "#f59e0b",
    "accent_warning_hover": "#d97706",
    "accent_danger": "#ef4444",
    "accent_danger_hover": "#dc2626",
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
    "border": "#e2e8f0",
    "hover_light": "#f1f5f9",
    "plot_bg": "#ffffff",
    "plot_text": "#1e293b",
}

DARK_THEME = {
    "bg_dark": "#0f172a",
    "bg_secondary": "#1e293b",
    "bg_card": "#334155",
    "accent_primary": "#60a5fa",
    "accent_secondary": "#3b82f6",
    "accent_success": "#34d399",
    "accent_success_hover": "#10b981",
    "accent_warning": "#fbbf24",
    "accent_warning_hover": "#f59e0b",
    "accent_danger": "#f87171",
    "accent_danger_hover": "#ef4444",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#475569",
    "hover_light": "#1e293b",
    "plot_bg": "#1e293b",
    "plot_text": "#f1f5f9",
}

# Current theme (mutable reference)
COLORS = LIGHT_THEME.copy()


class ThemeManager:
    """Manages application theme switching."""

    _current_theme = "light"
    _callbacks = []

    @classmethod
    def get_theme(cls) -> str:
        return cls._current_theme

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current_theme == "dark"

    @classmethod
    def set_theme(cls, theme: str):
        """Set theme and notify all registered callbacks."""
        global COLORS
        cls._current_theme = theme

        if theme == "dark":
            COLORS.clear()
            COLORS.update(DARK_THEME)
            ctk.set_appearance_mode("dark")
        else:
            COLORS.clear()
            COLORS.update(LIGHT_THEME)
            ctk.set_appearance_mode("light")

        # Notify all registered windows
        for callback in cls._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in theme callback {callback}: {e}")

    @classmethod
    def toggle(cls):
        """Toggle between light and dark theme."""
        new_theme = "light" if cls._current_theme == "dark" else "dark"
        cls.set_theme(new_theme)

    @classmethod
    def register(cls, callback):
        """Register a callback to be called when theme changes."""
        cls._callbacks.append(callback)

    @classmethod
    def register_callback(cls, callback):
        """Alias for register() to maintain compatibility."""
        cls.register(callback)

    @classmethod
    def unregister(cls, callback):
        """Unregister a callback."""
        if callback in cls._callbacks:
            cls._callbacks.remove(callback)
