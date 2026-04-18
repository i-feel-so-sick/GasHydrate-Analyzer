"""
Setup configuration dialog for creating and editing experimental setup parameters.
"""

import logging
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from visualize_app.ui.dialogs.parsing_schema_dialog import ParsingSchemaDialog
from visualize_app.ui.theme import COLORS
from visualize_app.utils.pressure_units import normalize_pressure_unit
from visualize_app.utils.setup_config import SetupConfig
from visualize_app.utils.setup_config import SetupConfigManager
from visualize_app.utils.setup_config import normalize_data_columns
from visualize_app.utils.setup_config import normalize_time_column

logger = logging.getLogger(__name__)


class SetupConfigDialog(ctk.CTkToplevel):
    """
    Dialog for creating or editing experimental setup configuration.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        setup_config_manager: SetupConfigManager,
        event_bus,
        edit_setup: Optional[SetupConfig] = None,
    ):
        """
        Initialize setup config dialog.

        Args:
            parent: Parent window
            setup_config_manager: Setup configuration manager
            event_bus: Event bus for publishing events
            edit_setup: Existing setup to edit, or None to create new
        """
        super().__init__(parent)
        self.withdraw()

        self.parent_window = parent
        self.setup_config = setup_config_manager
        self.event_bus = event_bus
        self.edit_setup = edit_setup
        self.is_edit_mode = edit_setup is not None
        self.time_column = normalize_time_column(edit_setup.time_column if edit_setup else None)
        self.data_columns = normalize_data_columns(edit_setup.data_columns if edit_setup else None)

        # UI elements
        self.name_entry = None
        self.description_entry = None
        self.vessel_entry = None
        self.water_entry = None
        self.pressure_coeff_entry = None
        self.btn_delete = None
        self.schema_summary_label = None

        self._build_ui()
        self.deiconify()
        self.lift()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        """Build dialog UI."""
        title = "Редактирование установки" if self.is_edit_mode else "Новая установка"
        self.title(title)
        width, height = 580, 820
        self.transient(self.parent_window)
        self.configure(fg_color=COLORS["bg_dark"])

        # Center dialog
        self.update_idletasks()
        x = self.parent_window.winfo_x() + (self.parent_window.winfo_width() // 2) - (width // 2)
        y = self.parent_window.winfo_y() + (self.parent_window.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(28, 18))

        title_text = "Редактирование установки" if self.is_edit_mode else "Создание новой установки"
        title_label = ctk.CTkLabel(
            header_frame,
            text=title_text,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(self, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", padx=28, pady=(0, 22))

        # Form container
        form_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        form_frame.pack(fill="x", padx=28, pady=(0, 18))

        # Get current values if editing
        current_name = self.edit_setup.name if self.edit_setup else ""
        current_description = self.edit_setup.description if self.edit_setup else ""
        current_vessel = self.edit_setup.vessel_volume if self.edit_setup else 0.0
        current_water = self.edit_setup.water_volume if self.edit_setup else 0.0
        current_coeff = self.edit_setup.pressure_coefficient if self.edit_setup else 1.0

        # Setup name field
        name_label = ctk.CTkLabel(
            form_frame,
            text="Название установки *",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        name_label.pack(anchor="w", padx=24, pady=(20, 6))

        self.name_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Например: Установка №1 - Теплообменник",
        )
        self.name_entry.pack(fill="x", padx=24, pady=(0, 16))
        if current_name:
            self.name_entry.insert(0, current_name)

        # Description field
        desc_label = ctk.CTkLabel(
            form_frame,
            text="Описание (необязательно)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        desc_label.pack(anchor="w", padx=24, pady=(0, 6))

        self.description_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Краткое описание установки",
        )
        self.description_entry.pack(fill="x", padx=24, pady=(0, 16))
        if current_description:
            self.description_entry.insert(0, current_description)

        # Vessel volume field
        vessel_label = ctk.CTkLabel(
            form_frame,
            text="Объем сосуда (литры) *",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        vessel_label.pack(anchor="w", padx=24, pady=(0, 6))

        self.vessel_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Введите объем сосуда",
        )
        self.vessel_entry.pack(fill="x", padx=24, pady=(0, 16))
        if current_vessel > 0:
            self.vessel_entry.insert(0, str(current_vessel))

        # Water volume field
        water_label = ctk.CTkLabel(
            form_frame,
            text="Объем воды (литры) *",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        water_label.pack(anchor="w", padx=24, pady=(0, 6))

        self.water_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Введите объем воды",
        )
        self.water_entry.pack(fill="x", padx=24, pady=(0, 16))
        if current_water > 0:
            self.water_entry.insert(0, str(current_water))

        # Pressure coefficient field
        coeff_label = ctk.CTkLabel(
            form_frame,
            text="Коэффициент давления",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        coeff_label.pack(anchor="w", padx=24, pady=(0, 4))

        coeff_hint = ctk.CTkLabel(
            form_frame,
            text="Сырые значения умножаются на этот коэффициент перед отображением",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        coeff_hint.pack(anchor="w", padx=24, pady=(0, 6))

        self.pressure_coeff_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="1.0",
        )
        self.pressure_coeff_entry.pack(fill="x", padx=24, pady=(0, 20))
        self.pressure_coeff_entry.insert(0, str(current_coeff))

        # Parsing schema configuration
        schema_label = ctk.CTkLabel(
            form_frame,
            text="Парсинг таблицы",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        schema_label.pack(anchor="w", padx=24, pady=(0, 6))

        schema_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        schema_frame.pack(fill="x", padx=24, pady=(0, 16))

        self.schema_summary_label = ctk.CTkLabel(
            schema_frame,
            text=self._build_schema_summary(),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.schema_summary_label.pack(side="left", fill="x", expand=True)

        schema_btn = ctk.CTkButton(
            schema_frame,
            text="Настроить...",
            height=34,
            width=140,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._open_parsing_schema_dialog,
        )
        schema_btn.pack(side="right")

        # Hint
        hint_label = ctk.CTkLabel(
            self,
            text="* — обязательные поля",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        hint_label.pack(anchor="w", padx=28, pady=(0, 12))

        # Buttons frame
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=28, pady=(0, 28))

        btn_save = ctk.CTkButton(
            buttons_frame,
            text="Сохранить",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["accent_success"],
            hover_color=COLORS["accent_success_hover"],
            corner_radius=12,
            command=self._save_config,
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(10, 0))

        btn_cancel = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=12,
            command=self.destroy,
        )
        btn_cancel.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Delete button (only in edit mode)
        if self.is_edit_mode:
            delete_frame = ctk.CTkFrame(self, fg_color="transparent")
            delete_frame.pack(fill="x", padx=28, pady=(0, 20))

            self.btn_delete = ctk.CTkButton(
                delete_frame,
                text="Удалить установку",
                height=40,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color=COLORS["accent_danger"],
                hover_color=COLORS["accent_danger_hover"],
                corner_radius=10,
                command=self._delete_config,
            )
            self.btn_delete.pack(fill="x")

    def _build_schema_summary(self) -> str:
        """Build a short summary string for parsing schema."""
        if not self.data_columns:
            return "Схема парсинга не задана"

        columns = [item.get("column", "") for item in self.data_columns if item.get("column")]
        if not columns:
            return "Схема парсинга не задана"

        preview = ", ".join(columns[:3])
        tail = "..." if len(columns) > 3 else ""
        return f"Колонки: {preview}{tail}"

    def _open_parsing_schema_dialog(self):
        """Open parsing schema dialog."""
        dialog = ParsingSchemaDialog(self, self.time_column, self.data_columns)
        self.wait_window(dialog)

        if dialog.result:
            self.time_column = normalize_time_column(dialog.result.get("time_column"))
            self.data_columns = normalize_data_columns(dialog.result.get("data_columns"))
            if self.schema_summary_label:
                self.schema_summary_label.configure(text=self._build_schema_summary())

    def _save_config(self):
        """Validate and save configuration."""
        try:
            setup_name = self.name_entry.get().strip()
            description = self.description_entry.get().strip()
            pressure_unit = self._resolve_pressure_unit_from_schema()

            # Parse volumes with comma support
            vessel_text = self.vessel_entry.get().replace(",", ".").strip()
            water_text = self.water_entry.get().replace(",", ".").strip()
            coeff_text = self.pressure_coeff_entry.get().replace(",", ".").strip()

            # Validation
            if not setup_name:
                messagebox.showerror("Ошибка", "Введите название установки")
                return

            # Check for duplicate names (except current setup when editing)
            existing = self.setup_config.get_setup_by_name(setup_name)
            if existing:
                if not self.is_edit_mode or existing.id != self.edit_setup.id:
                    messagebox.showerror("Ошибка", "Установка с таким названием уже существует")
                    return

            if not vessel_text:
                messagebox.showerror("Ошибка", "Введите объем сосуда")
                return

            if not water_text:
                messagebox.showerror("Ошибка", "Введите объем воды")
                return

            vessel_volume = float(vessel_text)
            water_volume = float(water_text)

            if vessel_volume <= 0:
                messagebox.showerror("Ошибка", "Объем сосуда должен быть больше 0")
                return

            if water_volume <= 0:
                messagebox.showerror("Ошибка", "Объем воды должен быть больше 0")
                return

            if water_volume > vessel_volume:
                messagebox.showerror("Ошибка", "Объем воды не может быть больше объема сосуда")
                return

            if not coeff_text:
                coeff_text = "1.0"
            pressure_coefficient = float(coeff_text)
            if pressure_coefficient <= 0:
                messagebox.showerror("Ошибка", "Коэффициент давления должен быть больше 0")
                return

            # Validate parsing columns
            self.time_column = normalize_time_column(self.time_column)
            self.data_columns = normalize_data_columns(self.data_columns)
            if not self.data_columns:
                messagebox.showerror("Ошибка", "Добавьте хотя бы один столбец данных")
                return

            # Save
            if self.is_edit_mode:
                # Update existing setup
                self.setup_config.update_setup(
                    self.edit_setup.id,
                    name=setup_name,
                    description=description,
                    pressure_unit=pressure_unit,
                    pressure_coefficient=pressure_coefficient,
                    vessel_volume=vessel_volume,
                    water_volume=water_volume,
                    time_column=self.time_column,
                    data_columns=self.data_columns,
                )
            else:
                # Create new setup
                self.setup_config.create_setup(
                    name=setup_name,
                    description=description,
                    pressure_unit=pressure_unit,
                    pressure_coefficient=pressure_coefficient,
                    vessel_volume=vessel_volume,
                    water_volume=water_volume,
                    time_column=self.time_column,
                    data_columns=self.data_columns,
                )

            # Publish event
            self.event_bus.publish("setup:config_updated", None)

            action = "обновлены" if self.is_edit_mode else "созданы"
            messagebox.showinfo("Успех", f"Параметры установки {action}")
            self.destroy()

        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные числовые значения для объемов")

    def _resolve_pressure_unit_from_schema(self) -> str:
        """
        Resolve pressure unit from parsing schema.
        Fallback order: pressure column unit -> existing setup value -> default кПа.
        """
        # 1) Preferred: explicit pressure column by name
        for item in self.data_columns:
            column = str(item.get("column", "")).strip().lower()
            if column not in {"давление", "pressure"}:
                continue
            unit = str(item.get("unit", "")).strip()
            normalized = normalize_pressure_unit(unit)
            if normalized:
                return normalized

        # 2) Fallback: any column that has a known pressure unit
        for item in self.data_columns:
            unit = str(item.get("unit", "")).strip()
            normalized = normalize_pressure_unit(unit)
            if not normalized:
                continue
            return normalized

        if self.edit_setup:
            existing = normalize_pressure_unit(self.edit_setup.pressure_unit)
            if existing:
                return existing

        return "кПа"

    def _delete_config(self):
        """Delete current configuration."""
        if not self.is_edit_mode or not self.edit_setup:
            return

        # Confirm deletion
        result = messagebox.askyesno(
            "Подтверждение", f'Вы уверены, что хотите удалить установку\n"{self.edit_setup.name}"?'
        )

        if result:
            self.setup_config.delete_setup(self.edit_setup.id)
            self.event_bus.publish("setup:config_updated", None)
            self.destroy()
            messagebox.showinfo("Успех", "Установка удалена")
