"""
Recent files dialog for showing file history.
"""

import logging
from pathlib import Path
from tkinter import messagebox
from typing import Callable
from typing import List

import customtkinter as ctk

from visualize_app.ui.theme import COLORS

logger = logging.getLogger(__name__)


class RecentFilesDialog(ctk.CTkToplevel):
    """
    Dialog showing recently opened files.
    """

    def __init__(
        self, parent: ctk.CTk, recent_files: List[str], on_select_callback: Callable[[Path], None]
    ):
        """
        Initialize recent files dialog.

        Args:
            parent: Parent window
            recent_files: List of recent file paths
            on_select_callback: Callback when file is selected
        """
        super().__init__(parent)
        self.withdraw()

        self.parent_window = parent
        self.recent_files = recent_files
        self.on_select_callback = on_select_callback

        self._build_ui()
        self.deiconify()
        self.lift()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        """Build dialog UI."""
        self.title("Недавние файлы")
        self.transient(self.parent_window)
        self.configure(fg_color=COLORS["bg_dark"])

        # Center dialog
        self.update_idletasks()
        x = self.parent_window.winfo_x() + (self.parent_window.winfo_width() // 2) - (700 // 2)
        y = self.parent_window.winfo_y() + (self.parent_window.winfo_height() // 2) - (520 // 2)
        self.geometry(f"700x520+{x}+{y}")

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(28, 18))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Недавние файлы",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", padx=28, pady=(0, 18))

        # Scrollable frame for files
        scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        scroll_frame.pack(fill="both", expand=True, padx=28, pady=(0, 18))

        # Add file cards
        for i, file_path_str in enumerate(self.recent_files):
            file_path_obj = Path(file_path_str)
            file_name = file_path_obj.name

            file_card = ctk.CTkFrame(
                scroll_frame,
                fg_color=COLORS["bg_card"],
                corner_radius=12,
                border_width=1,
                border_color=COLORS["border"],
            )
            file_card.pack(fill="x", pady=8, padx=10)

            file_inner = ctk.CTkFrame(file_card, fg_color="transparent")
            file_inner.pack(fill="x", padx=16, pady=14)

            file_info = ctk.CTkFrame(file_inner, fg_color="transparent")
            file_info.pack(side="left", fill="x", expand=True)

            file_name_label = ctk.CTkLabel(
                file_info,
                text=file_name if len(file_name) <= 45 else file_name[:42] + "...",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLORS["text_primary"],
                anchor="w",
            )
            file_name_label.pack(anchor="w")

            file_path_short = (
                file_path_str if len(file_path_str) <= 55 else "..." + file_path_str[-52:]
            )
            file_path_label = ctk.CTkLabel(
                file_info,
                text=file_path_short,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                anchor="w",
            )
            file_path_label.pack(anchor="w", pady=(4, 0))

            open_btn = ctk.CTkButton(
                file_inner,
                text="Открыть",
                width=100,
                height=38,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color=COLORS["accent_primary"],
                hover_color=COLORS["accent_secondary"],
                corner_radius=10,
                command=lambda fp=file_path_obj: self._on_file_selected(fp),
            )
            open_btn.pack(side="right")

        # Footer with close button
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(fill="x", padx=28, pady=(0, 28))

        btn_close = ctk.CTkButton(
            footer_frame,
            text="Закрыть",
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
            command=self.destroy,
        )
        btn_close.pack(fill="x")

    def _on_file_selected(self, file_path: Path):
        """Handle file selection."""
        self.destroy()
        if file_path.exists():
            self.on_select_callback(file_path)
        else:
            messagebox.showerror("Ошибка", f"Файл не найден:\n{file_path}")
