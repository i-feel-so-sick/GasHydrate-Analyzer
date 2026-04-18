"""
Plot settings dialog for customizing graph appearance.
"""

from typing import Callable
from typing import Optional

import customtkinter as ctk

from visualize_app.models import PlotSettings
from visualize_app.ui.theme import COLORS


class PlotSettingsDialog(ctk.CTkToplevel):
    """Dialog window for configuring plot settings."""

    def __init__(self, parent, current_settings: PlotSettings, event_bus):
        super().__init__(parent)
        self.withdraw()

        # Work with a copy so "Cancel" doesn't mutate global settings
        self.settings = PlotSettings.from_dict(current_settings.to_dict())
        self.event_bus = event_bus
        self.result: Optional[PlotSettings] = None
        self.pressure_display_options = {
            "Как в установке": "setup",
            "кПа": "кПа",
            "МПа": "МПа",
            "бар": "бар",
            "атм": "атм",
            "Па": "Па",
            "psi": "psi",
            "мм рт. ст.": "мм рт. ст.",
        }

        # Window configuration
        self.title("Настройки графиков")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)

        # Make modal
        self.transient(parent)

        # Center on parent
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 480) // 2
        y = parent_y + (parent_h - 700) // 2
        self.geometry(f"480x700+{x}+{y}")

        # Build UI
        self._build_ui()
        self.deiconify()
        self.lift()
        self.grab_set()

        # Focus
        self.focus_force()

    def _build_ui(self):
        """Build the dialog UI."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Настройки графиков",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.pack(pady=(0, 20))

        # Scrollable content
        content = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_primary"],
        )
        content.pack(fill="both", expand=True)

        # === LINES SECTION ===
        self._create_section_header(content, "Линии")
        lines_card = self._create_card(content)

        # Line width
        self._create_slider_row(
            lines_card,
            "Толщина линий",
            0.5,
            5.0,
            self.settings.line_width,
            self._on_line_width_change,
            "{:.1f} px",
        )

        # Line alpha
        self._create_slider_row(
            lines_card,
            "Прозрачность",
            0.1,
            1.0,
            self.settings.line_alpha,
            self._on_line_alpha_change,
            "{:.0%}",
        )

        # === MARKERS SECTION ===
        self._create_section_header(content, "Маркеры")
        markers_card = self._create_card(content)

        # Show markers toggle
        markers_toggle_frame = ctk.CTkFrame(markers_card, fg_color="transparent")
        markers_toggle_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            markers_toggle_frame,
            text="Показывать маркеры",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.markers_var = ctk.BooleanVar(value=self.settings.show_markers)
        self.markers_switch = ctk.CTkSwitch(
            markers_toggle_frame,
            text="",
            variable=self.markers_var,
            command=self._on_markers_toggle,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            width=46,
        )
        self.markers_switch.pack(side="right")

        # Marker size
        self.marker_size_row = self._create_slider_row(
            markers_card,
            "Размер маркеров",
            1.0,
            10.0,
            self.settings.marker_size,
            self._on_marker_size_change,
            "{:.1f} px",
        )

        # Marker style
        marker_style_frame = ctk.CTkFrame(markers_card, fg_color="transparent")
        marker_style_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            marker_style_frame,
            text="Тип маркера",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        # Get marker style labels
        marker_labels = list(self.settings.MARKER_STYLES.values())
        marker_keys = list(self.settings.MARKER_STYLES.keys())
        current_idx = (
            marker_keys.index(self.settings.marker_style)
            if self.settings.marker_style in marker_keys
            else 0
        )

        self.marker_style_var = ctk.StringVar(value=marker_labels[current_idx])
        self.marker_style_combo = ctk.CTkComboBox(
            marker_style_frame,
            values=marker_labels,
            variable=self.marker_style_var,
            command=self._on_marker_style_change,
            width=160,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            button_color=COLORS["accent_primary"],
            dropdown_font=ctk.CTkFont(size=12),
            state="readonly",
        )
        self.marker_style_combo.pack(side="right")

        # Update markers UI state
        self._update_markers_ui_state()

        # === GRID SECTION ===
        self._create_section_header(content, "Сетка")
        grid_card = self._create_card(content)

        # Show grid toggle
        grid_toggle_frame = ctk.CTkFrame(grid_card, fg_color="transparent")
        grid_toggle_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            grid_toggle_frame,
            text="Показывать сетку",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        self.grid_var = ctk.BooleanVar(value=self.settings.show_grid)
        self.grid_switch = ctk.CTkSwitch(
            grid_toggle_frame,
            text="",
            variable=self.grid_var,
            command=self._on_grid_toggle,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            width=46,
        )
        self.grid_switch.pack(side="right")

        # Grid alpha
        self.grid_alpha_row = self._create_slider_row(
            grid_card,
            "Прозрачность сетки",
            0.1,
            1.0,
            self.settings.grid_alpha,
            self._on_grid_alpha_change,
            "{:.0%}",
        )

        self._update_grid_ui_state()

        # === UNITS SECTION ===
        self._create_section_header(content, "Единицы")
        units_card = self._create_card(content)

        pressure_unit_frame = ctk.CTkFrame(units_card, fg_color="transparent")
        pressure_unit_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            pressure_unit_frame,
            text="Давление на графике",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        reverse_pressure_options = {v: k for k, v in self.pressure_display_options.items()}
        pressure_label = reverse_pressure_options.get(
            self.settings.pressure_display_unit, "Как в установке"
        )

        self.pressure_display_var = ctk.StringVar(value=pressure_label)
        self.pressure_display_combo = ctk.CTkComboBox(
            pressure_unit_frame,
            values=list(self.pressure_display_options.keys()),
            variable=self.pressure_display_var,
            command=self._on_pressure_display_unit_change,
            width=160,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            button_color=COLORS["accent_primary"],
            dropdown_font=ctk.CTkFont(size=12),
            state="readonly",
        )
        self.pressure_display_combo.pack(side="right")

        # === EXPORT SECTION ===
        self._create_section_header(content, "Экспорт")
        export_card = self._create_card(content)

        # DPI
        dpi_frame = ctk.CTkFrame(export_card, fg_color="transparent")
        dpi_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            dpi_frame,
            text="Разрешение (DPI)",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
        ).pack(side="left")

        dpi_options = [str(d) for d in self.settings.DPI_OPTIONS]
        self.dpi_var = ctk.StringVar(value=str(self.settings.export_dpi))
        self.dpi_combo = ctk.CTkComboBox(
            dpi_frame,
            values=dpi_options,
            variable=self.dpi_var,
            command=self._on_dpi_change,
            width=100,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            button_color=COLORS["accent_primary"],
            state="readonly",
        )
        self.dpi_combo.pack(side="right")

        # DPI hint
        dpi_hint = ctk.CTkLabel(
            export_card,
            text="72 — экран  •  150 — документы  •  300 — печать  •  600 — публикации",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        )
        dpi_hint.pack(anchor="w")

        # === BUTTONS ===
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(20, 0))

        # Reset button
        reset_btn = ctk.CTkButton(
            buttons_frame,
            text="Сбросить",
            width=100,
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._reset_to_defaults,
        )
        reset_btn.pack(side="left")

        # Apply button
        apply_btn = ctk.CTkButton(
            buttons_frame,
            text="Применить",
            width=120,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            command=self._apply_and_close,
        )
        apply_btn.pack(side="right")

        # Cancel button
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            width=100,
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(0, 10))

    def _create_section_header(self, parent, text: str):
        """Create a section header label."""
        header = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["accent_primary"],
        )
        header.pack(anchor="w", pady=(16, 8))

    def _create_card(self, parent) -> ctk.CTkFrame:
        """Create a styled card frame."""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.pack(fill="x", pady=(0, 4))

        # Inner padding
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        return inner

    def _create_slider_row(
        self,
        parent,
        label: str,
        from_: float,
        to: float,
        initial: float,
        command: Callable,
        format_str: str,
    ) -> dict:
        """Create a labeled slider row with value display."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 12))

        # Label
        lbl = ctk.CTkLabel(
            frame, text=label, font=ctk.CTkFont(size=13), text_color=COLORS["text_primary"]
        )
        lbl.pack(side="left")

        # Value label
        if "%" in format_str:
            value_text = format_str.format(initial)
        else:
            value_text = format_str.format(initial)

        value_lbl = ctk.CTkLabel(
            frame,
            text=value_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent_primary"],
            width=60,
        )
        value_lbl.pack(side="right")

        # Slider
        slider = ctk.CTkSlider(
            frame,
            from_=int(from_),
            to=int(to),
            number_of_steps=int((to - from_) * 10),
            width=160,
            height=18,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            fg_color=COLORS["border"],
            command=lambda v: self._on_slider_change(v, value_lbl, format_str, command),
        )
        slider.set(initial)
        slider.pack(side="right", padx=(0, 10))

        return {"frame": frame, "slider": slider, "value_label": value_lbl}

    def _on_slider_change(
        self, value: float, label: ctk.CTkLabel, format_str: str, command: Callable
    ):
        """Handle slider value change."""
        label.configure(text=format_str.format(value))
        command(value)

    # === VALUE CHANGE HANDLERS ===

    def _on_line_width_change(self, value: float):
        self.settings.line_width = value

    def _on_line_alpha_change(self, value: float):
        self.settings.line_alpha = value

    def _on_markers_toggle(self):
        self.settings.show_markers = self.markers_var.get()
        self._update_markers_ui_state()

    def _on_marker_size_change(self, value: float):
        self.settings.marker_size = value

    def _on_marker_style_change(self, value: str):
        # Find key by value
        for key, label in self.settings.MARKER_STYLES.items():
            if label == value:
                self.settings.marker_style = key
                break

    def _on_grid_toggle(self):
        self.settings.show_grid = self.grid_var.get()
        self._update_grid_ui_state()

    def _on_grid_alpha_change(self, value: float):
        self.settings.grid_alpha = value

    def _on_dpi_change(self, value: str):
        self.settings.export_dpi = int(value)

    def _on_pressure_display_unit_change(self, value: str):
        self.settings.pressure_display_unit = self.pressure_display_options.get(value, "setup")

    def _update_markers_ui_state(self):
        """Enable/disable marker controls based on toggle."""
        state = "normal" if self.settings.show_markers else "disabled"
        self.marker_size_row["slider"].configure(state=state)
        self.marker_style_combo.configure(
            state="readonly" if self.settings.show_markers else "disabled"
        )

    def _update_grid_ui_state(self):
        """Enable/disable grid controls based on toggle."""
        state = "normal" if self.settings.show_grid else "disabled"
        self.grid_alpha_row["slider"].configure(state=state)

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        default = PlotSettings()

        # Update UI
        self.settings = default

        # Close and reopen would be simpler
        self.destroy()
        PlotSettingsDialog(self.master, default, self.event_bus)

    def _apply_and_close(self):
        """Apply settings and close dialog."""
        self.result = self.settings
        # Publish event to update settings
        self.event_bus.publish("settings:changed", self.settings)
        self.destroy()
