"""
Dialog for configuring Excel parsing columns.
"""

from tkinter import messagebox
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import customtkinter as ctk

from visualize_app.ui.theme import COLORS
from visualize_app.utils.pressure_units import normalize_pressure_unit
from visualize_app.utils.setup_config import DEFAULT_TIME_COLUMN
from visualize_app.utils.setup_config import get_default_data_columns
from visualize_app.utils.setup_config import normalize_data_columns
from visualize_app.utils.setup_config import normalize_time_column


class ParsingSchemaDialog(ctk.CTkToplevel):
    """Dialog window for configuring Excel column names and units."""

    UNIT_CATEGORY_NONE = "Без категории"
    UNIT_CATEGORY_TEMPERATURE = "Температура"
    UNIT_CATEGORY_PRESSURE = "Давление"

    UNIT_PRESETS: Dict[str, List[str]] = {
        UNIT_CATEGORY_TEMPERATURE: ["°C", "K", "°F"],
        UNIT_CATEGORY_PRESSURE: ["кПа", "МПа", "бар", "атм", "Па", "psi", "мм рт. ст."],
    }

    TEMPERATURE_UNIT_ALIASES: Dict[str, str] = {
        "°c": "°C",
        "c": "°C",
        "celsius": "°C",
        "цельсия": "°C",
        "k": "K",
        "kelvin": "K",
        "к": "K",
        "кельвин": "K",
        "°f": "°F",
        "f": "°F",
        "fahrenheit": "°F",
        "фаренгейт": "°F",
    }

    def __init__(
        self, parent, time_column: Optional[str], data_columns: Optional[List[Dict[str, Any]]]
    ):
        super().__init__(parent)
        self.withdraw()

        self.time_column = normalize_time_column(time_column)
        self.data_columns = normalize_data_columns(data_columns)
        self.result: Optional[Dict[str, Any]] = None
        self._rows: List[Dict[str, Any]] = []

        self.dialog_width = 740
        self.dialog_height = 580

        self.title("Настройка столбцов Excel")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(True, True)
        self.minsize(600, 400)

        # Make modal
        self.transient(parent)

        # Center on parent
        self.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - self.dialog_width) // 2
        y = parent_y + (parent_h - self.dialog_height) // 2
        self.geometry(f"{self.dialog_width}x{self.dialog_height}+{x}+{y}")

        self._build_ui()
        self.deiconify()
        self.lift()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        """Build dialog UI."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        title = ctk.CTkLabel(
            main_frame,
            text="Настройка столбцов Excel",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            main_frame,
            text="Первая строка — колонка времени. Остальные — данные.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="left",
        )
        subtitle.pack(anchor="w", pady=(4, 12))

        # Scrollable table area
        content = ctk.CTkScrollableFrame(
            main_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        content.pack(fill="both", expand=True)

        # Table header
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        # Use pack with fixed widths for consistent columns
        for text, width, anchor in [
            ("Столбец", 180, "w"),
            ("Категория", 140, "w"),
            ("Ед. изм.", 110, "w"),
            ("Обязательный", 90, "center"),
        ]:
            ctk.CTkLabel(
                header,
                text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_secondary"],
                width=width,
                anchor=anchor,
            ).pack(side="left", padx=(0, 6))

        # Thin separator
        sep = ctk.CTkFrame(content, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=12, pady=(2, 4))

        self.rows_container = ctk.CTkFrame(content, fg_color="transparent")
        self.rows_container.pack(fill="both", padx=12, pady=(0, 4))

        # Populate rows
        self._add_row(self.time_column or DEFAULT_TIME_COLUMN, "", True)

        if not self.data_columns:
            self._add_row("", "", True)
        else:
            for item in self.data_columns:
                self._add_row(
                    item.get("column", ""), item.get("unit", ""), bool(item.get("required", True))
                )

        # Add row button
        add_btn = ctk.CTkButton(
            content,
            text="+ Добавить столбец",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_secondary"],
            corner_radius=8,
            command=lambda: self._add_row("", "", True),
        )
        add_btn.pack(anchor="w", padx=12, pady=(2, 10))

        # Bottom buttons
        buttons = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons.pack(fill="x", pady=(14, 0))

        reset_btn = ctk.CTkButton(
            buttons,
            text="По умолчанию",
            height=36,
            width=120,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            command=self._reset_defaults,
        )
        reset_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            buttons,
            text="Сохранить",
            height=36,
            width=110,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            corner_radius=8,
            command=self._apply_and_close,
        )
        save_btn.pack(side="right")

        cancel_btn = ctk.CTkButton(
            buttons,
            text="Отмена",
            height=36,
            width=90,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(0, 8))

    def _add_row(self, column: str, unit: str, required: bool):
        """Add a data column row — single line."""
        row_frame = ctk.CTkFrame(self.rows_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        col_entry = ctk.CTkEntry(
            row_frame,
            width=180,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            placeholder_text="Название",
        )
        col_entry.pack(side="left", padx=(0, 6))
        if column:
            col_entry.insert(0, column)

        category, normalized_unit = self._detect_unit_category_and_value(unit)

        category_var = ctk.StringVar(value=category)
        category_combo = ctk.CTkComboBox(
            row_frame,
            values=[
                self.UNIT_CATEGORY_NONE,
                self.UNIT_CATEGORY_TEMPERATURE,
                self.UNIT_CATEGORY_PRESSURE,
            ],
            variable=category_var,
            width=140,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_primary"],
            corner_radius=6,
            state="readonly",
        )
        category_combo.pack(side="left", padx=(0, 6))

        unit_var = ctk.StringVar(value=normalized_unit)
        unit_combo = ctk.CTkComboBox(
            row_frame,
            values=self._unit_options_for_category(category),
            variable=unit_var,
            width=110,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            button_color=COLORS["accent_primary"],
            corner_radius=6,
        )
        unit_combo.pack(side="left", padx=(0, 6))

        if normalized_unit:
            unit_combo.set(normalized_unit)

        category_combo.configure(
            command=lambda selected, uc=unit_combo, uv=unit_var: self._on_category_changed(
                selected, uc, uv
            )
        )

        required_var = ctk.BooleanVar(value=required)
        req_container = ctk.CTkFrame(row_frame, fg_color="transparent", width=90, height=32)
        req_container.pack(side="left", padx=(0, 6))
        req_container.pack_propagate(False)
        required_check = ctk.CTkCheckBox(
            req_container,
            text="",
            variable=required_var,
            width=22,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=4,
        )
        required_check.place(relx=0.5, rely=0.5, anchor="center")

        remove_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            height=30,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=COLORS["accent_danger"],
            text_color=COLORS["text_secondary"],
            corner_radius=6,
            command=lambda: self._remove_row(row_frame),
        )
        remove_btn.pack(side="right")

        self._rows.append(
            {
                "frame": row_frame,
                "column": col_entry,
                "category_var": category_var,
                "category_combo": category_combo,
                "unit_var": unit_var,
                "unit": unit_combo,
                "required_var": required_var,
            }
        )
        return col_entry

    def _on_category_changed(
        self, category: str, unit_combo: ctk.CTkComboBox, unit_var: ctk.StringVar
    ):
        """Update unit dropdown options when category changes."""
        current_unit = unit_var.get().strip()
        options = self._unit_options_for_category(category)
        unit_combo.configure(values=options)

        if current_unit in options:
            unit_combo.set(current_unit)
        elif options:
            unit_combo.set(options[0])
        else:
            unit_combo.set("")

    def _unit_options_for_category(self, category: str) -> List[str]:
        """Return unit options for selected category."""
        if category == self.UNIT_CATEGORY_NONE:
            return [""]
        return list(self.UNIT_PRESETS.get(category, []))

    def _detect_unit_category_and_value(self, raw_unit: str) -> tuple[str, str]:
        """
        Detect category and normalized preset value from raw unit.
        Unknown units are kept as-is under 'Без категории'.
        """
        unit = str(raw_unit).strip()
        if not unit:
            return self.UNIT_CATEGORY_NONE, ""

        pressure_unit = normalize_pressure_unit(unit)
        if pressure_unit:
            return self.UNIT_CATEGORY_PRESSURE, pressure_unit

        temperature_key = unit.lower().strip()
        if temperature_key in self.TEMPERATURE_UNIT_ALIASES:
            return self.UNIT_CATEGORY_TEMPERATURE, self.TEMPERATURE_UNIT_ALIASES[temperature_key]

        # Keep unknown unit editable
        return self.UNIT_CATEGORY_NONE, unit

    def _remove_row(self, frame):
        """Remove a row from UI."""
        self._rows = [row for row in self._rows if row["frame"] is not frame]
        frame.destroy()

    def _reset_defaults(self):
        """Reset fields to defaults."""
        for row in list(self._rows):
            row["frame"].destroy()
        self._rows = []
        self._add_row(DEFAULT_TIME_COLUMN, "", True)
        for item in get_default_data_columns():
            self._add_row(
                item.get("column", ""), item.get("unit", ""), bool(item.get("required", True))
            )

    def _apply_and_close(self):
        """Validate and save schema."""
        if not self._rows:
            messagebox.showerror("Ошибка", "Добавьте хотя бы одну строку")
            return

        # First row is time column
        time_column = self._rows[0]["column"].get().strip()

        columns: List[Dict[str, Any]] = []
        for row in self._rows[1:]:
            col_name = row["column"].get().strip()
            unit = row["unit"].get().strip()
            if not col_name:
                messagebox.showerror("Ошибка", "Заполните все названия колонок")
                return
            columns.append(
                {"column": col_name, "unit": unit, "required": bool(row["required_var"].get())}
            )

        if not columns:
            messagebox.showerror("Ошибка", "Добавьте хотя бы один столбец данных")
            return
        if len({item["column"] for item in columns}) != len(columns):
            messagebox.showerror("Ошибка", "Названия столбцов должны быть уникальны")
            return

        self.result = {"time_column": time_column, "data_columns": columns}
        self.destroy()
