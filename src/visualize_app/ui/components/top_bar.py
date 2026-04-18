"""
Top bar component with menus and thumbnails.
"""

import logging
from typing import Callable

import customtkinter as ctk

from visualize_app.core import AppState
from visualize_app.core import EventBus
from visualize_app.ui.components.base_component import BaseComponent
from visualize_app.ui.theme import COLORS

logger = logging.getLogger(__name__)


class TopBar(BaseComponent):
    """
    Top bar with toggle button, menus, file label, and plot thumbnails.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        app_state: AppState,
        event_bus: EventBus,
        on_toggle_sidebar: Callable,
        on_file_open: Callable,
        on_file_save: Callable,
        on_file_clear: Callable,
        on_recent_files: Callable,
        on_reset_zoom: Callable,
        on_zoom_in: Callable,
        on_zoom_out: Callable,
        on_theme_toggle: Callable,
    ):
        super().__init__(parent, app_state, event_bus)

        # Callbacks
        self.on_toggle_sidebar = on_toggle_sidebar
        self.on_file_open = on_file_open
        self.on_file_save = on_file_save
        self.on_file_clear = on_file_clear
        self.on_recent_files = on_recent_files
        self.on_reset_zoom = on_reset_zoom
        self.on_zoom_in = on_zoom_in
        self.on_zoom_out = on_zoom_out
        self.on_theme_toggle = on_theme_toggle

        # UI elements
        self.top_bar = None
        self.toggle_btn = None
        self.menu_file_btn = None
        self.menu_view_btn = None
        # Dropdown menus
        self.file_menu = None
        self.view_menu = None
        self.file_menu_visible = False
        self.view_menu_visible = False
        self.theme_btn = None  # Reference to theme toggle button
        self.top_bar_border = None  # Bottom border line

    def build(self) -> ctk.CTkFrame:
        """Build top bar."""
        # Main top bar - full width
        self.top_bar = ctk.CTkFrame(
            self.parent, height=56, corner_radius=0, fg_color=COLORS["bg_secondary"], border_width=0
        )
        self.top_bar.grid_propagate(False)
        self.top_bar.pack_propagate(False)

        # Bottom border
        self.top_bar_border = ctk.CTkFrame(self.top_bar, height=1, fg_color=COLORS["border"])
        self.top_bar_border.pack(side="bottom", fill="x")

        # Left section - menu buttons
        left_section = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        left_section.pack(side="left", padx=12, pady=10)

        # Toggle sidebar button
        self.toggle_btn = ctk.CTkButton(
            left_section,
            text="☰",
            width=40,
            height=36,
            font=ctk.CTkFont(size=18),
            command=self.on_toggle_sidebar,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
        )
        self.toggle_btn.pack(side="left", padx=(0, 10))

        # Menu buttons
        self.menu_file_btn = ctk.CTkButton(
            left_section,
            text="Файл",
            width=70,
            height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=self._show_file_menu,
        )
        self.menu_file_btn.pack(side="left", padx=2)

        self.menu_view_btn = ctk.CTkButton(
            left_section,
            text="Вид",
            width=60,
            height=36,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=self._show_view_menu,
        )
        self.menu_view_btn.pack(side="left", padx=2)

        # Create dropdown menus
        self._create_dropdown_menus()

        self.widget = self.top_bar
        return self.top_bar

    def _create_dropdown_menus(self):
        """Create dropdown menu frames."""
        from visualize_app.ui.theme import ThemeManager

        # File menu dropdown
        self.file_menu = self._create_menu(
            [
                ("Открыть...", self.on_file_open, "Ctrl+O"),
                ("Сохранить график...", self.on_file_save, "Ctrl+S"),
                ("separator", None, None),
                ("Недавние файлы", self.on_recent_files, ""),
                ("separator", None, None),
                ("Очистить", self.on_file_clear, ""),
            ]
        )

        # View menu dropdown - create with theme button placeholder
        theme_text = "Светлая тема" if ThemeManager.is_dark() else "Тёмная тема"
        self.view_menu, self.theme_btn = self._create_menu_with_theme_btn(
            [
                ("Боковая панель", self.on_toggle_sidebar, "Ctrl+B"),
                ("separator", None, None),
                ("Сбросить масштаб", self.on_reset_zoom, "Ctrl+0"),
                ("Увеличить", self.on_zoom_in, "Ctrl++"),
                ("Уменьшить", self.on_zoom_out, "Ctrl+-"),
                ("separator", None, None),
                (theme_text, self.on_theme_toggle, "Ctrl+D", "theme"),
            ]
        )

        # Click outside to close menus
        self.parent.bind("<Button-1>", self._on_click_outside)

    def _create_menu(self, items):
        """Create a dropdown menu."""
        menu = ctk.CTkFrame(
            self.parent,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )

        for item in items:
            if item[0] == "separator":
                sep = ctk.CTkFrame(menu, height=1, fg_color=COLORS["border"])
                sep.pack(fill="x", padx=10, pady=6)
            else:
                item_frame = ctk.CTkFrame(menu, fg_color="transparent")
                item_frame.pack(fill="x", padx=6, pady=2)

                btn = ctk.CTkButton(
                    item_frame,
                    text=item[0],
                    anchor="w",
                    height=36,
                    font=ctk.CTkFont(size=13),
                    fg_color="transparent",
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    corner_radius=6,
                    command=lambda cmd=item[1]: self._menu_action(cmd),
                )
                btn.pack(side="left", fill="x", expand=True, padx=2)

                if item[2]:
                    shortcut = ctk.CTkLabel(
                        item_frame,
                        text=item[2],
                        font=ctk.CTkFont(size=12),
                        text_color=COLORS["text_secondary"],
                    )
                    shortcut.pack(side="right", padx=10)

        return menu

    def _create_menu_with_theme_btn(self, items):
        """Create a dropdown menu and return reference to theme button."""
        menu = ctk.CTkFrame(
            self.parent,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )

        theme_btn = None

        for item in items:
            if item[0] == "separator":
                sep = ctk.CTkFrame(menu, height=1, fg_color=COLORS["border"])
                sep.pack(fill="x", padx=10, pady=6)
            else:
                item_frame = ctk.CTkFrame(menu, fg_color="transparent")
                item_frame.pack(fill="x", padx=6, pady=2)

                btn = ctk.CTkButton(
                    item_frame,
                    text=item[0],
                    anchor="w",
                    height=36,
                    font=ctk.CTkFont(size=13),
                    fg_color="transparent",
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    corner_radius=6,
                    command=lambda cmd=item[1]: self._menu_action(cmd),
                )
                btn.pack(side="left", fill="x", expand=True, padx=2)

                # Check if this is the theme button (4th element = "theme")
                if len(item) > 3 and item[3] == "theme":
                    theme_btn = btn

                if item[2]:
                    shortcut = ctk.CTkLabel(
                        item_frame,
                        text=item[2],
                        font=ctk.CTkFont(size=12),
                        text_color=COLORS["text_secondary"],
                    )
                    shortcut.pack(side="right", padx=10)

        return menu, theme_btn

    def _show_file_menu(self):
        """Show file dropdown menu."""
        if self.file_menu_visible:
            self._hide_all_menus()
            return
        self._hide_all_menus()
        self.parent.update_idletasks()
        x = self.menu_file_btn.winfo_rootx() - self.parent.winfo_rootx()
        y = (
            self.menu_file_btn.winfo_rooty()
            - self.parent.winfo_rooty()
            + self.menu_file_btn.winfo_height()
        )
        self.file_menu.place(x=x, y=y)
        self.file_menu.lift()
        self.file_menu_visible = True

    def _show_view_menu(self):
        """Show view dropdown menu."""
        if self.view_menu_visible:
            self._hide_all_menus()
            return
        self._hide_all_menus()
        self.parent.update_idletasks()
        x = self.menu_view_btn.winfo_rootx() - self.parent.winfo_rootx()
        y = (
            self.menu_view_btn.winfo_rooty()
            - self.parent.winfo_rooty()
            + self.menu_view_btn.winfo_height()
        )
        self.view_menu.place(x=x, y=y)
        self.view_menu.lift()
        self.view_menu_visible = True

    def _hide_all_menus(self):
        """Hide all dropdown menus."""
        self.file_menu.place_forget()
        self.view_menu.place_forget()
        self.file_menu_visible = False
        self.view_menu_visible = False

    def _menu_action(self, cmd):
        """Execute menu action and hide menu."""
        self._hide_all_menus()
        if cmd:
            cmd()

    def _on_click_outside(self, event):
        """Hide menus when clicking outside."""
        if not (self.file_menu_visible or self.view_menu_visible):
            return

        widget = event.widget
        check_widgets = [self.file_menu, self.view_menu, self.menu_file_btn, self.menu_view_btn]

        current = widget
        while current:
            if current in check_widgets:
                return
            try:
                current = current.master
            except (AttributeError, Exception):
                break

        # Schedule hide to avoid race condition
        self.parent.after(10, self._hide_all_menus)

    def update_theme(self):
        """Update theme colors."""
        from visualize_app.ui.theme import ThemeManager

        self.top_bar.configure(fg_color=COLORS["bg_secondary"])
        if self.top_bar_border:
            self.top_bar_border.configure(fg_color=COLORS["border"])
        self.toggle_btn.configure(
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
        )
        self.menu_file_btn.configure(
            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
        )
        self.menu_view_btn.configure(
            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
        )
        # Update menus
        self.file_menu.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])
        self.view_menu.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])
        self._update_menu_items(self.file_menu)
        self._update_menu_items(self.view_menu)

        # Update theme button text
        if self.theme_btn:
            theme_text = "Светлая тема" if ThemeManager.is_dark() else "Тёмная тема"
            self.theme_btn.configure(text=theme_text)

    def _update_menu_items(self, menu_frame):
        """Update menu item colors."""
        for child in menu_frame.winfo_children():
            widget_class = child.__class__.__name__
            if widget_class == "CTkFrame":
                # Check if it's a separator (has height=1 and no children)
                is_separator = False
                try:
                    height = child.cget("height")
                    # Separator frames have height=1 and no children
                    if height == 1 and len(child.winfo_children()) == 0:
                        is_separator = True
                        child.configure(fg_color=COLORS["border"])
                except Exception as e:
                    logger.debug(f"Could not update menu item: {e}")

                if not is_separator:
                    for subchild in child.winfo_children():
                        subclass = subchild.__class__.__name__
                        if subclass == "CTkButton":
                            subchild.configure(
                                hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
                            )
                        elif subclass == "CTkLabel":
                            subchild.configure(text_color=COLORS["text_secondary"])
