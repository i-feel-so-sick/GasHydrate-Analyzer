"""
Sidebar control panel component.
"""

import logging
import tkinter as tk
from typing import Callable
from typing import Optional

import customtkinter as ctk
import numpy as np

from visualize_app.core import AppState
from visualize_app.core import EventBus
from visualize_app.ui.components.base_component import BaseComponent
from visualize_app.ui.theme import COLORS
from visualize_app.utils.setup_config import SetupConfigManager

logger = logging.getLogger(__name__)


class SidebarPanel(BaseComponent):
    """
    Left sidebar control panel with setup selection and statistics.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        app_state: AppState,
        event_bus: EventBus,
        setup_config: SetupConfigManager,
        on_plot_settings: Callable,
        on_clear_data: Callable,
        on_setup_config: Callable,
        on_add_setup: Callable,
    ):
        super().__init__(parent, app_state, event_bus)

        self.setup_config = setup_config
        self.on_plot_settings = on_plot_settings
        self.on_clear_data = on_clear_data
        self.on_setup_config = on_setup_config
        self.on_add_setup = on_add_setup

        # UI elements
        self.control_frame = None
        self.right_border = None  # Right border separator
        self.sidebar_header = None
        self.sidebar_title = None
        self.setup_card = None
        self.setup_label = None
        self.setup_combo = None
        self.btn_add_setup = None
        self.btn_edit_setup = None
        self.setup_info_card = None
        self.setup_info_label = None
        self.setup_info_text = None
        self.btn_plot_settings = None
        self.btn_clear = None
        self.stats_card = None
        self.stats_label = None
        self.info_text = None

        # Time filter elements
        self.time_filter_card = None
        self.time_filter_label = None
        self.time_start_slider = None
        self.time_end_slider = None
        self.time_start_entry = None
        self.time_end_entry = None
        self.btn_reset_filter = None
        self.time_range = (0, 100)  # Default range in hours
        self._filter_debounce_id = None  # Debounce timer for time filter
        self._time_controls_syncing = False

        # Signal downsampling elements (display-only frequency reduction)
        self.signal_filter_card = None
        self.signal_filter_label = None
        self.signal_filter_hint = None
        self.signal_downsample_slider = None
        self.signal_downsample_entry = None
        self._signal_debounce_id = None
        self._pending_signal_downsample_factor = 1
        self._signal_controls_syncing = False

    def build(self) -> ctk.CTkFrame:
        """Build sidebar panel."""
        # Main control panel
        self.control_frame = ctk.CTkFrame(
            self.parent, corner_radius=0, width=280, fg_color=COLORS["bg_secondary"], border_width=0
        )
        self.control_frame.grid_propagate(False)

        # Right border separator
        self.right_border = ctk.CTkFrame(self.control_frame, width=1, fg_color=COLORS["border"])
        self.right_border.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # Setup selection card
        self.setup_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.setup_card.pack(pady=(12, 6), padx=12, fill="x")

        self.setup_label = ctk.CTkLabel(
            self.setup_card,
            text="Установка",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.setup_label.pack(anchor="w", padx=12, pady=(10, 4))

        # Build setup selection UI based on existing setups
        self._build_setup_selection()

        # Setup info display
        self.setup_info_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.setup_info_card.pack(pady=6, padx=12, fill="x")

        self.setup_info_label = ctk.CTkLabel(
            self.setup_info_card,
            text="Параметры",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.setup_info_label.pack(anchor="w", padx=12, pady=(10, 4))

        self.setup_info_text = ctk.CTkLabel(
            self.setup_info_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w",
            wraplength=220,
        )
        self.setup_info_text.pack(fill="x", padx=12, pady=(0, 10))
        self.update_setup_info_display()

        # Plot settings button
        self.btn_plot_settings = ctk.CTkButton(
            self.control_frame,
            text="Настройки графиков",
            command=self.on_plot_settings,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
        )
        self.btn_plot_settings.pack(fill="x", padx=12, pady=6)

        # Clear button — created here, packed at the bottom after stats card
        self.btn_clear = ctk.CTkButton(
            self.control_frame,
            text="Очистить данные",
            command=self.on_clear_data,
            height=32,
            state="disabled",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_danger"],
            text_color=COLORS["accent_danger"],
            border_width=1,
            border_color=COLORS["accent_danger"],
            corner_radius=8,
        )

        # Time filter card
        self.time_filter_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.time_filter_card.pack(pady=6, padx=12, fill="x")

        self.time_filter_label = ctk.CTkLabel(
            self.time_filter_card,
            text="Фильтр по времени",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.time_filter_label.pack(anchor="w", padx=12, pady=(10, 4))

        # Start time slider
        start_frame = ctk.CTkFrame(self.time_filter_card, fg_color="transparent")
        start_frame.pack(fill="x", padx=12, pady=(4, 0))

        ctk.CTkLabel(
            start_frame,
            text="Начало:",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            width=55,
        ).pack(side="left")

        self.time_start_entry = ctk.CTkEntry(
            start_frame,
            width=68,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            justify="center",
        )
        self.time_start_entry.pack(side="right")
        self.time_start_entry.insert(0, "0.00")
        self.time_start_entry.bind("<Return>", self._on_time_entry_submit)
        self.time_start_entry.bind("<FocusOut>", self._on_time_entry_submit)

        self.time_start_slider = ctk.CTkSlider(
            start_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            height=16,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            fg_color=COLORS["border"],
            command=self._on_start_time_change,
        )
        self.time_start_slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.time_start_slider.set(0)

        # End time slider
        end_frame = ctk.CTkFrame(self.time_filter_card, fg_color="transparent")
        end_frame.pack(fill="x", padx=12, pady=(4, 0))

        ctk.CTkLabel(
            end_frame,
            text="Конец:",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            width=55,
        ).pack(side="left")

        self.time_end_entry = ctk.CTkEntry(
            end_frame,
            width=68,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            justify="center",
        )
        self.time_end_entry.pack(side="right")
        self.time_end_entry.insert(0, "100.00")
        self.time_end_entry.bind("<Return>", self._on_time_entry_submit)
        self.time_end_entry.bind("<FocusOut>", self._on_time_entry_submit)

        self.time_end_slider = ctk.CTkSlider(
            end_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            height=16,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            fg_color=COLORS["border"],
            command=self._on_end_time_change,
        )
        self.time_end_slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.time_end_slider.set(100)

        # Reset filter button
        self.btn_reset_filter = ctk.CTkButton(
            self.time_filter_card,
            text="Сбросить фильтр",
            command=self._reset_time_filter,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
        )
        self.btn_reset_filter.pack(fill="x", padx=12, pady=(8, 10))

        # Signal frequency reduction (display downsampling) card
        self.signal_filter_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.signal_filter_card.pack(pady=6, padx=12, fill="x")

        self.signal_filter_label = ctk.CTkLabel(
            self.signal_filter_card,
            text="Уменьшение частоты",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.signal_filter_label.pack(anchor="w", padx=12, pady=(10, 2))

        self.signal_filter_hint = ctk.CTkLabel(
            self.signal_filter_card,
            text="Показывать каждую N-ю точку данных",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="left",
        )
        self.signal_filter_hint.pack(anchor="w", padx=12, pady=(0, 4))

        signal_slider_frame = ctk.CTkFrame(self.signal_filter_card, fg_color="transparent")
        signal_slider_frame.pack(fill="x", padx=12, pady=(2, 0))

        ctk.CTkLabel(
            signal_slider_frame,
            text="Шаг:",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            width=55,
        ).pack(side="left")

        self.signal_downsample_entry = ctk.CTkEntry(
            signal_slider_frame,
            width=52,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            justify="center",
        )
        self.signal_downsample_entry.pack(side="right")
        self.signal_downsample_entry.insert(0, "1")
        self.signal_downsample_entry.bind("<Return>", self._on_signal_downsample_entry_submit)
        self.signal_downsample_entry.bind("<FocusOut>", self._on_signal_downsample_entry_submit)

        self.signal_downsample_slider = ctk.CTkSlider(
            signal_slider_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            height=16,
            button_color=COLORS["accent_primary"],
            button_hover_color=COLORS["accent_secondary"],
            progress_color=COLORS["accent_primary"],
            fg_color=COLORS["border"],
            command=self._on_signal_downsample_slider_change,
        )
        self.signal_downsample_slider.pack(side="left", fill="x", expand=True, padx=(8, 8))
        self.signal_downsample_slider.set(1)

        self._update_time_labels()
        self._update_signal_downsample_display()

        # Initially disable filter (no data) and hide filter cards
        self._set_filter_enabled(False)
        self.time_filter_card.pack_forget()
        self.signal_filter_card.pack_forget()

        # Clear button at the bottom — hidden until data is loaded
        # (packed dynamically in _on_file_loaded / _on_file_cleared)

        # Statistics (fills remaining space)
        self.stats_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.stats_card.pack(pady=(4, 0), padx=12, fill="both", expand=True)

        self.stats_label = ctk.CTkLabel(
            self.stats_card,
            text="Статистика данных",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.stats_label.pack(anchor="w", padx=12, pady=(10, 4))

        self.info_text = ctk.CTkTextbox(
            self.stats_card,
            font=ctk.CTkFont(size=11),
            wrap="word",
            fg_color=COLORS["bg_secondary"],
            corner_radius=8,
            text_color=COLORS["text_primary"],
        )
        self.info_text.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        self.info_text.configure(state="disabled")

        # Subscribe to events
        self.event_bus.subscribe("file:loaded", self._on_file_loaded)
        self.event_bus.subscribe("file:clear", self._on_file_cleared)
        self.event_bus.subscribe("setup:config_updated", self._on_setup_updated)

        self.widget = self.control_frame
        return self.control_frame

    def _build_setup_selection(self):
        """Build setup selection UI based on available setups."""
        # Clear existing widgets inside setup card except the label
        for child in self.setup_card.winfo_children():
            if child is not self.setup_label:
                child.destroy()
        self.setup_combo = None
        self.btn_add_setup = None
        self.btn_edit_setup = None

        if self.setup_config.has_setups():
            # Show ComboBox with existing setups
            setup_names = self.setup_config.get_setup_names()
            current_setup = self.setup_config.get_current_setup()
            current_name = (
                current_setup.name if current_setup else (setup_names[0] if setup_names else "")
            )

            self.setup_combo = ctk.CTkComboBox(
                self.setup_card,
                values=setup_names,
                state="readonly",
                height=36,
                font=ctk.CTkFont(size=14),
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                button_color=COLORS["accent_primary"],
                text_color=COLORS["text_primary"],
                dropdown_font=ctk.CTkFont(size=14),
                corner_radius=8,
                command=self._on_setup_selected,
            )
            self.setup_combo.pack(fill="x", padx=12, pady=(0, 6))

            if current_name in setup_names:
                self.setup_combo.set(current_name)
            elif setup_names:
                self.setup_combo.set(setup_names[0])

            # Buttons row
            btn_frame = ctk.CTkFrame(self.setup_card, fg_color="transparent")
            btn_frame.pack(fill="x", padx=12, pady=(0, 10))

            # Edit button
            self.btn_edit_setup = ctk.CTkButton(
                btn_frame,
                text="Редактировать",
                command=self._edit_current_setup,
                height=32,
                font=ctk.CTkFont(size=12),
                fg_color=COLORS["accent_primary"],
                hover_color=COLORS["accent_secondary"],
                corner_radius=6,
                width=120,
            )
            self.btn_edit_setup.pack(side="left", padx=(0, 6))

            # Add button
            self.btn_add_setup = ctk.CTkButton(
                btn_frame,
                text="+ Добавить",
                command=self.on_add_setup,
                height=32,
                font=ctk.CTkFont(size=12),
                fg_color=COLORS["bg_secondary"],
                hover_color=COLORS["hover_light"],
                text_color=COLORS["text_primary"],
                border_width=1,
                border_color=COLORS["border"],
                corner_radius=6,
            )
            self.btn_add_setup.pack(side="left", fill="x", expand=True)
        else:
            # Show only "Add setup" button
            no_setup_label = ctk.CTkLabel(
                self.setup_card,
                text="Нет сохраненных установок",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
            )
            no_setup_label.pack(anchor="w", padx=12, pady=(0, 6))

            self.btn_add_setup = ctk.CTkButton(
                self.setup_card,
                text="+ Добавить установку",
                command=self.on_add_setup,
                height=38,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=COLORS["accent_success"],
                hover_color=COLORS["accent_success_hover"],
                corner_radius=8,
            )
            self.btn_add_setup.pack(fill="x", padx=12, pady=(0, 10))

    def _edit_current_setup(self):
        """Edit currently selected setup."""
        current_setup = self.setup_config.get_current_setup()
        if current_setup:
            self.on_setup_config(current_setup)

    def update_info_text(self, data):
        """Update statistics display."""
        if not data:
            return

        duration = float(max(data.hours)) if data.hours else 0.0

        # Show filename if available
        filename = ""
        if self.app_state.current_file_path:
            filename = self.app_state.current_file_path.name

        info_lines = []
        if filename:
            info_lines.append(f"Файл: {filename}")
        info_lines.extend([f"Записей: {data.size:,}  ·  Время: {duration:.1f} ч", ""])

        for name, values in data.series.items():
            if not values:
                continue
            unit = data.units.get(name, "")
            title = f"{name} ({unit})" if unit else name
            v_min, v_max = float(min(values)), float(max(values))
            v_avg = float(np.mean(values))
            info_lines.extend(
                [title, f"  Мин: {v_min:.1f}   Макс: {v_max:.1f}   Ср: {v_avg:.1f}", ""]
            )

        info = "\n".join(info_lines).rstrip()

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")

    def clear_info_text(self):
        """Clear statistics display."""
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.configure(state="disabled")

    def update_setup_info_display(self):
        """Update setup information display."""
        current_setup = self.setup_config.get_current_setup()

        if current_setup and current_setup.is_configured():
            gas_volume = current_setup.get_gas_volume()
            coeff = getattr(current_setup, "pressure_coefficient", 1.0) or 1.0
            coeff_str = f"  ·  к-т {coeff}" if coeff != 1.0 else ""
            info = (
                f"Давление: {current_setup.pressure_unit}{coeff_str}\n"
                f"Сосуд: {current_setup.vessel_volume:.1f} л  ·  Вода: {current_setup.water_volume:.1f} л\n"
                f"Газ: {gas_volume:.1f} л"
            )
            if current_setup.description:
                info += f"\n{current_setup.description}"
        else:
            info = "Параметры не настроены.\nНажмите «+ Добавить»."

        self.setup_info_text.configure(text=info)

    def show(self):
        """Show sidebar."""
        self.control_frame.grid(row=2, column=0, padx=0, pady=0, sticky="nsw")
        self.app_state.sidebar_visible = True

    def hide(self):
        """Hide sidebar."""
        self.control_frame.grid_forget()
        self.app_state.sidebar_visible = False

    def toggle_visibility(self):
        """Toggle sidebar visibility."""
        if self.app_state.sidebar_visible:
            self.hide()
        else:
            self.show()

    def _set_filter_enabled(self, enabled: bool):
        """Enable or disable data filtering controls."""
        state = "normal" if enabled else "disabled"
        for widget in (
            self.time_start_slider,
            self.time_end_slider,
            self.time_start_entry,
            self.time_end_entry,
            self.btn_reset_filter,
            self.signal_downsample_slider,
            self.signal_downsample_entry,
        ):
            if widget:
                widget.configure(state=state)

    def _update_time_filter_range(self, data):
        """Update time filter sliders based on loaded data."""
        if not data or not data.hours:
            return

        max_time = float(max(data.hours))
        self.time_range = (0, max_time)
        slider_steps = 1 if max_time <= 0 else max(1, min(5000, int(round(max_time * 10))))

        # Enable first so configure/set work correctly on CTkSlider
        self._set_filter_enabled(True)

        # Update slider ranges
        if self.time_start_slider:
            self.time_start_slider.configure(from_=0, to=max_time, number_of_steps=slider_steps)
        if self.time_end_slider:
            self.time_end_slider.configure(from_=0, to=max_time, number_of_steps=slider_steps)

        # Sync controls without triggering plot regeneration on file load
        self._set_time_values(0, max_time, apply=False)

    def _set_entry_text(self, entry: Optional[ctk.CTkEntry], value: str):
        """Safely update entry text without leaving stale values."""
        if not entry:
            return
        if entry.get() == value:
            return
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def _parse_float_entry(self, entry: Optional[ctk.CTkEntry]) -> Optional[float]:
        """Parse float from entry supporting comma decimal separator."""
        if not entry:
            return None
        text = entry.get().strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _parse_int_entry(self, entry: Optional[ctk.CTkEntry]) -> Optional[int]:
        """Parse positive integer from entry (supports optional x prefix/suffix)."""
        if not entry:
            return None
        text = entry.get().strip().lower().replace("x", "")
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None

    def _get_time_min_gap(self) -> float:
        """Return minimum allowed gap between start and end time."""
        range_min, range_max = self.time_range
        span = max(0.0, float(range_max) - float(range_min))
        if span <= 0:
            return 0.0
        return min(0.1, span)

    def _set_time_values(self, start_val: float, end_val: float, apply: bool = True):
        """Synchronize sliders/labels/entries for the time filter."""
        if not self.time_start_slider or not self.time_end_slider:
            return

        range_min, range_max = self.time_range
        if range_max < range_min:
            range_min, range_max = range_max, range_min

        start_val = max(range_min, min(float(start_val), range_max))
        end_val = max(range_min, min(float(end_val), range_max))
        if end_val < start_val:
            start_val, end_val = end_val, start_val

        min_gap = self._get_time_min_gap()
        if min_gap > 0 and (end_val - start_val) < min_gap:
            if end_val >= range_max:
                start_val = max(range_min, end_val - min_gap)
            else:
                end_val = min(range_max, start_val + min_gap)

            if (end_val - start_val) < min_gap:
                start_val = range_min
                end_val = range_max

        self._time_controls_syncing = True
        try:
            self.time_start_slider.set(start_val)
            self.time_end_slider.set(end_val)
            self._update_time_labels()
        finally:
            self._time_controls_syncing = False

        if apply:
            self._apply_time_filter()

    def _update_time_labels(self):
        """Update time entry displays from current slider values."""
        if self.time_start_slider and self.time_start_entry:
            start_val = self.time_start_slider.get()
            self._set_entry_text(self.time_start_entry, f"{start_val:.2f}")
        if self.time_end_slider and self.time_end_entry:
            end_val = self.time_end_slider.get()
            self._set_entry_text(self.time_end_entry, f"{end_val:.2f}")

    def _on_time_entry_submit(self, _event=None):
        """Apply time filter values entered manually."""
        if self._time_controls_syncing:
            return

        start_val = self._parse_float_entry(self.time_start_entry)
        end_val = self._parse_float_entry(self.time_end_entry)

        if start_val is None or end_val is None:
            self._update_time_labels()
            return

        self._set_time_values(start_val, end_val, apply=True)

    def _on_start_time_change(self, value):
        """Handle start time slider change."""
        if self._time_controls_syncing or not self.time_end_slider:
            return
        self._set_time_values(float(value), self.time_end_slider.get(), apply=True)

    def _on_end_time_change(self, value):
        """Handle end time slider change."""
        if self._time_controls_syncing or not self.time_start_slider:
            return
        self._set_time_values(self.time_start_slider.get(), float(value), apply=True)

    def _reset_time_filter(self):
        """Reset time filter to full range."""
        self._set_time_values(self.time_range[0], self.time_range[1], apply=True)

    def _apply_time_filter(self):
        """Apply time filter with debounce to avoid excessive plot regeneration."""
        if not self.time_start_slider or not self.time_end_slider:
            return

        # Cancel previous pending update
        if self._filter_debounce_id is not None:
            self.parent.after_cancel(self._filter_debounce_id)

        # Schedule update after 300ms of inactivity
        self._filter_debounce_id = self.parent.after(300, self._do_apply_time_filter)

    def _do_apply_time_filter(self):
        """Actually apply time filter after debounce delay."""
        self._filter_debounce_id = None

        if not self.time_start_slider or not self.time_end_slider:
            return

        start_time = self.time_start_slider.get()
        end_time = self.time_end_slider.get()

        # Store filter values in app_state
        self.app_state.time_filter = (start_time, end_time)

        # Publish event to trigger plot regeneration
        self.event_bus.publish("time_filter:changed", (start_time, end_time))

    def _update_signal_downsample_display(self):
        """Refresh signal downsampling controls."""
        factor = max(1, int(getattr(self.app_state, "signal_downsample_factor", 1)))
        self._set_entry_text(self.signal_downsample_entry, str(factor))

    def _set_signal_downsample_factor(self, factor: int, publish: bool = True):
        """Set display downsampling factor and optionally publish change event."""
        factor = max(1, min(100, int(factor)))
        previous_factor = max(1, int(getattr(self.app_state, "signal_downsample_factor", 1)))
        self.app_state.signal_downsample_factor = factor
        self._pending_signal_downsample_factor = factor

        self._signal_controls_syncing = True
        try:
            if self.signal_downsample_slider:
                self.signal_downsample_slider.set(factor)
            self._update_signal_downsample_display()
        finally:
            self._signal_controls_syncing = False

        if publish and factor != previous_factor:
            self._apply_signal_downsample_change()

    def _apply_signal_downsample_change(self):
        """Debounced apply for signal downsampling."""
        if self._signal_debounce_id is not None:
            self.parent.after_cancel(self._signal_debounce_id)
        self._signal_debounce_id = self.parent.after(300, self._do_apply_signal_downsample_change)

    def _do_apply_signal_downsample_change(self):
        """Publish signal downsampling change after debounce delay."""
        self._signal_debounce_id = None
        factor = max(1, int(self._pending_signal_downsample_factor))
        self.event_bus.publish("signal_downsample:changed", factor)

    def _on_signal_downsample_slider_change(self, value):
        """Handle signal downsampling slider change."""
        if self._signal_controls_syncing:
            return
        self._set_signal_downsample_factor(int(round(float(value))), publish=True)

    def _on_signal_downsample_entry_submit(self, _event=None):
        """Apply manually entered signal downsampling factor."""
        if self._signal_controls_syncing:
            return

        factor = self._parse_int_entry(self.signal_downsample_entry)
        if factor is None or factor < 1:
            self._update_signal_downsample_display()
            return

        self._set_signal_downsample_factor(factor, publish=True)

    def _on_file_loaded(self, data):
        """Handle file loaded event."""
        if data:
            self.update_info_text(data)
            self._update_time_filter_range(data)
            self._update_signal_downsample_display()
            # Show filter cards (before stats_card which uses expand=True)
            if self.time_filter_card:
                self.time_filter_card.pack(pady=6, padx=12, fill="x", before=self.stats_card)
            if self.signal_filter_card:
                self.signal_filter_card.pack(pady=6, padx=12, fill="x", before=self.stats_card)
            # Show clear button
            if self.btn_clear:
                self.btn_clear.configure(
                    state="normal",
                    text_color="#ffffff",
                    fg_color=COLORS["accent_danger"],
                    hover_color=COLORS["accent_danger_hover"],
                    border_width=0,
                )
                self.btn_clear.pack(fill="x", padx=12, pady=(4, 12), side="bottom")

    def _on_file_cleared(self, data):
        """Handle file cleared event."""
        self.clear_info_text()

        if self._filter_debounce_id is not None:
            self.parent.after_cancel(self._filter_debounce_id)
            self._filter_debounce_id = None
        if self._signal_debounce_id is not None:
            self.parent.after_cancel(self._signal_debounce_id)
            self._signal_debounce_id = None

        # Reset and disable time filter
        self.time_range = (0, 100)
        if self.time_start_slider:
            self.time_start_slider.configure(from_=0, to=100, number_of_steps=100)
        if self.time_end_slider:
            self.time_end_slider.configure(from_=0, to=100, number_of_steps=100)
        self._set_time_values(0, 100, apply=False)
        self._set_signal_downsample_factor(1, publish=False)
        self._set_filter_enabled(False)

        # Hide filter cards and clear button
        if self.time_filter_card:
            self.time_filter_card.pack_forget()
        if self.signal_filter_card:
            self.signal_filter_card.pack_forget()
        if self.btn_clear:
            self.btn_clear.pack_forget()
            self.btn_clear.configure(state="disabled")

    def _on_setup_updated(self, data):
        """Handle setup config updated event."""
        self._build_setup_selection()
        self.update_setup_info_display()

    def _on_setup_selected(self, choice):
        """Handle setup selection from combobox."""
        self.setup_config.set_current_setup_by_name(choice)
        self.update_setup_info_display()

    def update_theme(self):
        """Update theme colors."""
        self.control_frame.configure(fg_color=COLORS["bg_secondary"])

        if self.right_border:
            self.right_border.configure(fg_color=COLORS["border"])

        if self.setup_card:
            self.setup_card.configure(fg_color=COLORS["bg_card"])
        if self.setup_label:
            self.setup_label.configure(text_color=COLORS["text_primary"])
        if self.setup_combo:
            self.setup_combo.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                button_color=COLORS["accent_primary"],
                text_color=COLORS["text_primary"],
            )

        if self.btn_add_setup:
            # Style depends on whether setups exist
            if self.setup_config.has_setups():
                self.btn_add_setup.configure(
                    fg_color=COLORS["bg_secondary"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    border_color=COLORS["border"],
                )
            else:
                self.btn_add_setup.configure(
                    fg_color=COLORS["accent_success"], hover_color=COLORS["accent_success_hover"]
                )

        if self.btn_edit_setup:
            self.btn_edit_setup.configure(
                fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"]
            )

        if self.setup_info_card:
            self.setup_info_card.configure(fg_color=COLORS["bg_card"])
        if self.setup_info_label:
            self.setup_info_label.configure(text_color=COLORS["text_primary"])
        if self.setup_info_text:
            self.setup_info_text.configure(text_color=COLORS["text_secondary"])

        if self.stats_card:
            self.stats_card.configure(fg_color=COLORS["bg_card"])
        if self.stats_label:
            self.stats_label.configure(text_color=COLORS["text_primary"])
        if self.info_text:
            self.info_text.configure(
                fg_color=COLORS["bg_secondary"], text_color=COLORS["text_primary"]
            )

        # Time filter theme
        if self.time_filter_card:
            self.time_filter_card.configure(fg_color=COLORS["bg_card"])
        if self.time_filter_label:
            self.time_filter_label.configure(text_color=COLORS["text_primary"])
        if self.time_start_slider:
            self.time_start_slider.configure(
                button_color=COLORS["accent_primary"],
                button_hover_color=COLORS["accent_secondary"],
                progress_color=COLORS["accent_primary"],
                fg_color=COLORS["border"],
            )
        if self.time_end_slider:
            self.time_end_slider.configure(
                button_color=COLORS["accent_primary"],
                button_hover_color=COLORS["accent_secondary"],
                progress_color=COLORS["accent_primary"],
                fg_color=COLORS["border"],
            )
        if self.time_start_entry:
            self.time_start_entry.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            )
        if self.time_end_entry:
            self.time_end_entry.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            )
        if self.btn_reset_filter:
            self.btn_reset_filter.configure(
                fg_color=COLORS["bg_secondary"],
                hover_color=COLORS["hover_light"],
                text_color=COLORS["text_primary"],
                border_color=COLORS["border"],
            )

        # Signal downsampling theme
        if self.signal_filter_card:
            self.signal_filter_card.configure(fg_color=COLORS["bg_card"])
        if self.signal_filter_label:
            self.signal_filter_label.configure(text_color=COLORS["text_primary"])
        if self.signal_filter_hint:
            self.signal_filter_hint.configure(text_color=COLORS["text_secondary"])
        if self.signal_downsample_slider:
            self.signal_downsample_slider.configure(
                button_color=COLORS["accent_primary"],
                button_hover_color=COLORS["accent_secondary"],
                progress_color=COLORS["accent_primary"],
                fg_color=COLORS["border"],
            )
        if self.signal_downsample_entry:
            self.signal_downsample_entry.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                text_color=COLORS["text_primary"],
            )
        if self.btn_plot_settings:
            self.btn_plot_settings.configure(
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["hover_light"],
                text_color=COLORS["text_primary"],
                border_color=COLORS["border"],
            )

        if self.btn_clear:
            if self.btn_clear.cget("state") == "normal":
                self.btn_clear.configure(
                    fg_color=COLORS["accent_danger"],
                    hover_color=COLORS["accent_danger_hover"],
                    text_color="#ffffff",
                    border_width=0,
                )
            else:
                self.btn_clear.configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["accent_danger"],
                    text_color=COLORS["accent_danger"],
                    border_width=1,
                    border_color=COLORS["accent_danger"],
                )
