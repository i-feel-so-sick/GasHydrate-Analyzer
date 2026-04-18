"""
Main application window with modern UI using customtkinter.
"""

import logging
import time
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from PIL import Image
from PIL import ImageTk

from visualize_app.config import ExperimentConfig
from visualize_app.models import ExperimentalData
from visualize_app.models import PlotSettings
from visualize_app.services import ExcelParser
from visualize_app.services import ExcelParserError
from visualize_app.services import PlotEngine
from visualize_app.ui.theme import COLORS
from visualize_app.ui.theme import DARK_THEME
from visualize_app.ui.theme import LIGHT_THEME
from visualize_app.ui.theme import ThemeManager
from visualize_app.utils.file_history import FileHistory
from visualize_app.utils.setup_config import SetupConfigManager

logger = logging.getLogger(__name__)

# Initialize with light theme
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Main application window with modern glassmorphism design."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("ThermoViz | Визуализация экспериментальных данных")
        self.geometry("1500x950")
        self.configure(fg_color=COLORS["bg_dark"])

        # Center window on screen
        self.center_window()

        # State
        self.current_data: Optional[ExperimentalData] = None
        self.current_file_path: Optional[Path] = None
        self.plot_settings = PlotSettings()
        self.plot_engine = PlotEngine(settings=self.plot_settings)
        self.canvas_widgets: dict = {}
        self.toolbars: dict = {}
        self.file_history = FileHistory(max_items=10)
        self.setup_config = SetupConfigManager()
        self.sidebar_visible = True

        # Thumbnails cache
        self.thumbnails = {}  # {plot_id: PhotoImage}
        self.thumbnail_frames = {}  # {plot_id: CTkFrame}

        # Build UI
        self._build_ui()

        # Register theme change callback
        ThemeManager.register(self._apply_theme)

        logger.info("Main window initialized")

    def center_window(self):
        """Center window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Build user interface."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Plot area row gets extra space

        # Top bar - full width toolbar
        self._build_top_bar()

        # Left panel - Controls (collapsible)
        self._build_control_panel()

        # Right panel - Plot area
        self._build_plot_area()

    def _build_top_bar(self):
        """Build unified top toolbar spanning full width."""
        # Main top bar - full width
        self.top_bar = ctk.CTkFrame(
            self, height=56, corner_radius=0, fg_color=COLORS["bg_secondary"], border_width=0
        )
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.top_bar.grid_propagate(False)

        # Bottom border
        top_bar_border = ctk.CTkFrame(self.top_bar, height=1, fg_color=COLORS["border"])
        top_bar_border.pack(side="bottom", fill="x")

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
            command=self._toggle_sidebar,
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

        # Separator
        sep = ctk.CTkFrame(left_section, width=1, height=28, fg_color=COLORS["border"])
        sep.pack(side="left", padx=12)

        # File path label
        self.file_path_label = ctk.CTkLabel(
            left_section,
            text="Файл не выбран",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.file_path_label.pack(side="left", padx=8)

        # Right section - thumbnails
        right_section = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_section.pack(side="right", padx=12, pady=8)

        # Container for thumbnails
        self.thumbnails_container = ctk.CTkFrame(right_section, fg_color="transparent")
        self.thumbnails_container.pack()

        # Placeholder text
        self.thumbnails_placeholder = ctk.CTkLabel(
            self.thumbnails_container,
            text="Загрузите файл для просмотра графиков",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="center",
        )
        self.thumbnails_placeholder.pack(pady=4)

        self.current_plot = "pressure"
        self.thumbnail_frames = {}

        # Create dropdown menus (hidden by default)
        self._create_dropdown_menus()

    def _create_dropdown_menus(self):
        """Create dropdown menu frames."""
        # File menu dropdown
        self.file_menu = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.file_menu_visible = False

        menu_items = [
            ("Открыть...", self._select_file, "Ctrl+O"),
            ("Сохранить график...", self._save_plot, "Ctrl+S"),
            ("separator", None, None),
            ("Недавние файлы", self._show_recent_files, ""),
            ("separator", None, None),
            ("Очистить", self._clear_all, ""),
        ]

        for item in menu_items:
            if item[0] == "separator":
                sep = ctk.CTkFrame(self.file_menu, height=1, fg_color=COLORS["border"])
                sep.pack(fill="x", padx=10, pady=6)
            else:
                item_frame = ctk.CTkFrame(self.file_menu, fg_color="transparent")
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

        # View menu dropdown
        self.view_menu = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.view_menu_visible = False

        view_items = [
            ("Боковая панель", self._toggle_sidebar, "Ctrl+B"),
            ("separator", None, None),
            ("Сбросить масштаб", self._reset_current_zoom, "Ctrl+0"),
            ("Увеличить", lambda: self._zoom_current(1.2), "Ctrl++"),
            ("Уменьшить", lambda: self._zoom_current(0.8), "Ctrl+-"),
            ("separator", None, None),
            ("Тёмная тема", self._toggle_theme, "Ctrl+D"),
        ]

        for item in view_items:
            if item[0] == "separator":
                sep = ctk.CTkFrame(self.view_menu, height=1, fg_color=COLORS["border"])
                sep.pack(fill="x", padx=10, pady=6)
            else:
                item_frame = ctk.CTkFrame(self.view_menu, fg_color="transparent")
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

        # Click outside to close menus
        self.bind("<Button-1>", self._on_click_outside)

    def _show_file_menu(self):
        """Show file dropdown menu."""
        if self.file_menu_visible:
            self._hide_all_menus()
            return
        self._hide_all_menus()
        self.update_idletasks()
        x = self.menu_file_btn.winfo_rootx() - self.winfo_rootx()
        y = (
            self.menu_file_btn.winfo_rooty()
            - self.winfo_rooty()
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
        self.update_idletasks()
        x = self.menu_view_btn.winfo_rootx() - self.winfo_rootx()
        y = (
            self.menu_view_btn.winfo_rooty()
            - self.winfo_rooty()
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

        # Check if widget or any of its parents is a menu or menu button
        check_widgets = [self.file_menu, self.view_menu, self.menu_file_btn, self.menu_view_btn]

        current = widget
        while current:
            if current in check_widgets:
                return
            try:
                current = current.master
            except Exception:
                break

        # Schedule hide to avoid race condition with button command
        self.after(10, self._hide_all_menus)

    def _build_control_panel(self):
        """Build collapsible control panel (sidebar)."""
        # Main control panel (collapsible)
        self.control_frame = ctk.CTkFrame(
            self, corner_radius=0, width=280, fg_color=COLORS["bg_secondary"], border_width=0
        )
        self.control_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.control_frame.grid_propagate(False)

        # Right border separator
        border = ctk.CTkFrame(self.control_frame, width=1, fg_color=COLORS["border"])
        border.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        # Header
        self.sidebar_header = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.sidebar_header.pack(fill="x", pady=(12, 8), padx=12)

        self.sidebar_title = ctk.CTkLabel(
            self.sidebar_header,
            text="Панель управления",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.sidebar_title.pack(side="left")

        # Setup selection
        self.setup_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.setup_card.pack(pady=6, padx=12, fill="x")

        self.setup_label = ctk.CTkLabel(
            self.setup_card,
            text="Установка",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.setup_label.pack(anchor="w", padx=12, pady=(10, 4))

        setup_names = [setup.name for setup in ExperimentConfig.get_all_setups()]
        self.setup_combo = ctk.CTkComboBox(
            self.setup_card,
            values=setup_names,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            button_color=COLORS["accent_primary"],
            dropdown_font=ctk.CTkFont(size=13),
            corner_radius=8,
        )
        self.setup_combo.pack(fill="x", padx=12, pady=(0, 10))
        self.setup_combo.set(setup_names[0] if setup_names else "")

        # Setup configuration button
        self.btn_setup_config = ctk.CTkButton(
            self.control_frame,
            text="Настройки установки",
            command=self._show_setup_config_dialog,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            corner_radius=8,
        )
        self.btn_setup_config.pack(fill="x", padx=12, pady=6)

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

        self.setup_info_text = ctk.CTkTextbox(
            self.setup_info_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            fg_color=COLORS["bg_secondary"],
            corner_radius=8,
            text_color=COLORS["text_secondary"],
            height=80,
        )
        self.setup_info_text.pack(fill="both", padx=8, pady=(0, 10))
        self._update_setup_info_display()

        # Plot settings button
        self.btn_plot_settings = ctk.CTkButton(
            self.control_frame,
            text="Настройки графиков",
            command=self._show_plot_settings,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
        )
        self.btn_plot_settings.pack(fill="x", padx=12, pady=6)

        # Clear button
        self.btn_clear = ctk.CTkButton(
            self.control_frame,
            text="Очистить данные",
            command=self._clear_all,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_danger"],
            hover_color="#dc2626",
            corner_radius=8,
        )
        self.btn_clear.pack(fill="x", padx=12, pady=4)

        # Statistics
        self.stats_card = ctk.CTkFrame(
            self.control_frame, fg_color=COLORS["bg_card"], corner_radius=10
        )
        self.stats_card.pack(pady=(4, 12), padx=12, fill="both", expand=True)

        self.stats_label = ctk.CTkLabel(
            self.stats_card,
            text="Статистика данных",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.stats_label.pack(anchor="w", padx=12, pady=(10, 4))

        self.info_text = ctk.CTkTextbox(
            self.stats_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none",
            fg_color=COLORS["bg_secondary"],
            corner_radius=8,
            text_color=COLORS["text_primary"],
        )
        self.info_text.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        self.info_text.insert(
            "1.0", "Нажмите 'Файл' → 'Открыть'\nили выберите из истории\n\nФорматы: .xlsx, .xls"
        )
        self.info_text.configure(state="disabled")

    def _build_plot_area(self):
        """Build plot display area."""
        self.plot_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
        )
        self.plot_frame.grid(row=1, column=1, padx=(8, 12), pady=(8, 12), sticky="nsew")

        # Single canvas frame for current plot
        self.canvas_frame = ctk.CTkFrame(
            self.plot_frame, fg_color=COLORS["bg_card"], corner_radius=12
        )
        self.canvas_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Placeholder for initial state
        self.placeholder = ctk.CTkFrame(self.canvas_frame, fg_color="transparent")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.placeholder_text = ctk.CTkLabel(
            self.placeholder,
            text="Загрузите файл для визуализации",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_secondary"],
        )
        self.placeholder_text.pack()

        self.placeholder_hint = ctk.CTkLabel(
            self.placeholder,
            text="Нажмите 'Открыть' или выберите из истории",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
        )
        self.placeholder_hint.pack(pady=(8, 0))

        # Store figures for each plot type
        self.figures = {}

    def _select_file(self):
        """Handle file selection."""
        file_path = filedialog.askopenfilename(
            title="Выберите Excel файл",
            filetypes=[("Excel файлы", "*.xlsx *.xls"), ("Все файлы", "*.*")],
        )

        if not file_path:
            return

        self._load_file(file_path)

    def _load_file(self, file_path: str):
        """Load file and generate plots."""
        try:
            self._update_status("Загрузка файла...")

            # Parse file
            self.current_file_path = Path(file_path)
            self.current_data = ExcelParser.parse_file(self.current_file_path)

            # Add to history
            self.file_history.add(str(self.current_file_path))

            # Update top bar file label
            file_name = self.current_file_path.name
            if len(file_name) > 40:
                file_name = file_name[:37] + "..."
            self.file_path_label.configure(text=f"{file_name}", text_color=COLORS["text_primary"])

            # Update info
            self._update_info_text()

            # Automatically generate plots
            self._generate_plots()

            self._update_status(f"Файл загружен: {self.current_file_path.name}")

            messagebox.showinfo(
                "Успех", f"Файл успешно загружен!\nЗаписей: {self.current_data.size}"
            )

        except ExcelParserError as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке файла:\n{str(e)}")
            self._update_status("Ошибка загрузки файла")
            logger.error(f"Error loading file: {e}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка:\n{str(e)}")
            self._update_status("Ошибка")
            logger.error(f"Unexpected error: {e}", exc_info=True)

    def _generate_plots(self):
        """Generate all plots and store them."""
        if self.current_data is None:
            messagebox.showwarning("Предупреждение", "Сначала загрузите файл данных")
            return

        try:
            self._update_status("Построение графиков...")

            # Clear previous
            self.plot_engine.close_all()
            self.figures.clear()

            # Update plot engine settings
            self.plot_engine.settings = self.plot_settings

            # Generate all figures using current settings
            self.figures["pressure"] = self.plot_engine.create_time_series_plot(
                self.current_data,
                y_columns=["Давление"],
                title="Изменение давления во времени",
                ylabel="Давление, кПа",
                figsize=(12, 7),
            )

            self.figures["gas"] = self.plot_engine.create_time_series_plot(
                self.current_data,
                y_columns=["ТемператураГаза"],
                title="Температура газа",
                ylabel="Температура, °C",
                figsize=(12, 7),
            )

            self.figures["liquid"] = self.plot_engine.create_time_series_plot(
                self.current_data,
                y_columns=["ТемператураЖидкости"],
                title="Температура жидкости",
                ylabel="Температура, °C",
                figsize=(12, 7),
            )

            self.figures["all"] = self.plot_engine.create_time_series_plot(
                self.current_data,
                y_columns=[
                    "ТемператураГаза",
                    "ТемператураЖидкости",
                    "ТемператураВКоробе",
                    "ТемператураВКомнате",
                ],
                title="Все температуры",
                ylabel="Температура, °C",
                figsize=(12, 7),
            )

            # Build thumbnails
            self._build_thumbnails()

            # Display current plot
            self._display_current_plot()
            self._update_status("Графики построены")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при построении графиков:\n{str(e)}")
            self._update_status("Ошибка построения графиков")
            logger.error(f"Error generating plots: {e}", exc_info=True)

    def _switch_plot(self, plot_id: str):
        """Switch to a different plot type."""
        if plot_id == self.current_plot:
            return

        self.current_plot = plot_id

        # Update thumbnail selection
        self._update_thumbnail_selection()

        # Display new plot if data is loaded
        if self.current_data is not None and plot_id in self.figures:
            self._display_current_plot()

    def _display_current_plot(self):
        """Display the currently selected plot."""
        if self.current_plot not in self.figures:
            return

        # Hide placeholder
        self.placeholder.place_forget()

        # Clear previous canvas
        for widget in self.canvas_frame.winfo_children():
            if widget != self.placeholder:
                widget.destroy()

        fig = self.figures[self.current_plot]

        # Create canvas
        self.current_canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Add compact toolbar
        toolbar_container = ctk.CTkFrame(
            self.canvas_frame, fg_color=COLORS["bg_secondary"], corner_radius=10, height=48
        )
        toolbar_container.pack(fill="x", pady=(8, 6), padx=6)
        toolbar_container.pack_propagate(False)

        # Matplotlib toolbar
        self.current_toolbar = NavigationToolbar2Tk(self.current_canvas, toolbar_container)
        self.current_toolbar.update()
        self.current_toolbar.pack(side="left", padx=8)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(toolbar_container, fg_color="transparent")
        zoom_frame.pack(side="right", padx=12)

        hint_label = ctk.CTkLabel(
            zoom_frame,
            text="СКМ/ПКМ - двигать  |  Колесо - зум",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        hint_label.pack(side="left", padx=(0, 14))

        btn_zoom_in = ctk.CTkButton(
            zoom_frame,
            text="+",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom_current(1.2),
        )
        btn_zoom_in.pack(side="left", padx=3)

        btn_zoom_out = ctk.CTkButton(
            zoom_frame,
            text="-",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom_current(0.8),
        )
        btn_zoom_out.pack(side="left", padx=3)

        btn_reset = ctk.CTkButton(
            zoom_frame,
            text="Сброс",
            width=70,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_warning"],
            hover_color="#d97706",
            text_color="#ffffff",
            corner_radius=8,
            command=self._reset_current_zoom,
        )
        btn_reset.pack(side="left", padx=3)

        # Bind mouse events for zoom
        canvas_widget = self.current_canvas.get_tk_widget()
        canvas_widget.bind("<MouseWheel>", self._on_mouse_wheel_current)
        canvas_widget.bind("<Button-4>", self._on_mouse_wheel_current)
        canvas_widget.bind("<Button-5>", self._on_mouse_wheel_current)

        # Bind pan events - Button-2 (middle) and Button-3 (right) for cross-platform
        # macOS may use Button-2 for right-click
        canvas_widget.bind("<ButtonPress-2>", self._on_pan_start_current)
        canvas_widget.bind("<B2-Motion>", self._on_pan_motion_current)
        canvas_widget.bind("<ButtonRelease-2>", self._on_pan_end_current)
        canvas_widget.bind("<ButtonPress-3>", self._on_pan_start_current)
        canvas_widget.bind("<B3-Motion>", self._on_pan_motion_current)
        canvas_widget.bind("<ButtonRelease-3>", self._on_pan_end_current)

        # Initialize pan state with throttling
        self.pan_state = {
            "active": False,
            "start_x": 0,
            "start_y": 0,
            "last_update": 0,
            "pending_update": None,
        }

    def _create_thumbnail(self, figure, size=(70, 35)):
        """Create a low-resolution thumbnail from matplotlib figure."""
        try:
            # Save figure to buffer with low DPI for performance
            buf = BytesIO()
            figure.savefig(
                buf, format="png", dpi=20, bbox_inches="tight", facecolor="white", edgecolor="none"
            )
            buf.seek(0)

            # Open with PIL and resize
            img = Image.open(buf)
            img = img.resize(size, Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            buf.close()

            return photo
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None

    def _build_thumbnails(self):
        """Build compact thumbnail buttons in top bar."""
        # Clear existing thumbnails
        for widget in self.thumbnails_container.winfo_children():
            widget.destroy()

        self.thumbnail_frames.clear()

        # Hide placeholder
        self.thumbnails_placeholder.pack_forget()

        # Plot info: (id, name)
        plot_info = [
            ("pressure", "Давление"),
            ("gas", "Газ"),
            ("liquid", "Жидкость"),
            ("all", "Все"),
        ]

        # Create horizontal layout with compact buttons
        for idx, (plot_id, name) in enumerate(plot_info):
            if plot_id not in self.figures:
                continue

            # Create compact button-style thumbnail
            thumb_btn = ctk.CTkButton(
                self.thumbnails_container,
                text=name,
                width=80,
                height=36,
                font=ctk.CTkFont(
                    size=13, weight="bold" if plot_id == self.current_plot else "normal"
                ),
                fg_color=COLORS["accent_primary"]
                if plot_id == self.current_plot
                else COLORS["bg_card"],
                hover_color=COLORS["accent_secondary"]
                if plot_id == self.current_plot
                else COLORS["hover_light"],
                text_color="#ffffff" if plot_id == self.current_plot else COLORS["text_primary"],
                corner_radius=8,
                command=lambda pid=plot_id: self._switch_plot(pid),
            )
            thumb_btn.pack(side="left", padx=3)

            # Store frame reference
            self.thumbnail_frames[plot_id] = thumb_btn

    def _update_thumbnail_selection(self):
        """Update style of selected thumbnail button."""
        for plot_id, btn in self.thumbnail_frames.items():
            if plot_id == self.current_plot:
                btn.configure(
                    fg_color=COLORS["accent_primary"],
                    hover_color=COLORS["accent_secondary"],
                    text_color="#ffffff",
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=13, weight="normal"),
                )

    def _zoom_current(self, scale_factor: float):
        """Zoom current plot."""
        if not hasattr(self, "current_canvas"):
            return
        fig = self.current_canvas.figure
        for ax in fig.get_axes():
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            x_center, y_center = (xlim[0] + xlim[1]) / 2, (ylim[0] + ylim[1]) / 2
            x_range = (xlim[1] - xlim[0]) / scale_factor
            y_range = (ylim[1] - ylim[0]) / scale_factor
            ax.set_xlim([x_center - x_range / 2, x_center + x_range / 2])
            ax.set_ylim([y_center - y_range / 2, y_center + y_range / 2])
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _reset_current_zoom(self):
        """Reset zoom on current plot."""
        if not hasattr(self, "current_canvas"):
            return
        for ax in self.current_canvas.figure.get_axes():
            ax.autoscale()
        self.current_canvas.draw()

    def _on_mouse_wheel_current(self, event):
        """Handle mouse wheel zoom on current plot."""
        if not hasattr(self, "current_canvas"):
            return
        if event.num == 5 or event.delta < 0:
            self._zoom_current(0.9)
        elif event.num == 4 or event.delta > 0:
            self._zoom_current(1.1)

    def _on_pan_start_current(self, event):
        """Start panning current plot."""
        if not hasattr(self, "current_canvas"):
            return
        self.pan_state["active"] = True
        self.pan_state["start_x"] = event.x
        self.pan_state["start_y"] = event.y
        self.pan_state["accumulated_dx"] = 0
        self.pan_state["accumulated_dy"] = 0

    def _on_pan_motion_current(self, event):
        """Pan current plot with throttling for smoothness."""
        if not hasattr(self, "current_canvas") or not self.pan_state.get("active"):
            return

        current_time = time.time() * 1000  # ms

        dx = event.x - self.pan_state["start_x"]
        dy = event.y - self.pan_state["start_y"]

        if dx == 0 and dy == 0:
            return

        # Accumulate movement
        self.pan_state["accumulated_dx"] = dx
        self.pan_state["accumulated_dy"] = dy

        # Throttle: update at most every 16ms (~60fps)
        time_since_last = current_time - self.pan_state.get("last_update", 0)
        if time_since_last < 16:
            # Schedule update if not already scheduled
            if not self.pan_state.get("pending_update"):
                self.pan_state["pending_update"] = self.after(
                    int(16 - time_since_last), self._do_pan_update
                )
            return

        self._do_pan_update()

    def _do_pan_update(self):
        """Perform the actual pan update."""
        if not hasattr(self, "current_canvas") or not self.pan_state.get("active"):
            self.pan_state["pending_update"] = None
            return

        dx = self.pan_state.get("accumulated_dx", 0)
        dy = self.pan_state.get("accumulated_dy", 0)

        if dx == 0 and dy == 0:
            self.pan_state["pending_update"] = None
            return

        for ax in self.current_canvas.figure.get_axes():
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]

            # Get canvas size for scaling
            canvas_widget = self.current_canvas.get_tk_widget()
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()

            if canvas_width > 0 and canvas_height > 0:
                x_shift = -(dx / canvas_width) * x_range
                y_shift = (dy / canvas_height) * y_range
                ax.set_xlim([xlim[0] + x_shift, xlim[1] + x_shift])
                ax.set_ylim([ylim[0] + y_shift, ylim[1] + y_shift])

        # Update start position for incremental panning
        self.pan_state["start_x"] += dx
        self.pan_state["start_y"] += dy
        self.pan_state["accumulated_dx"] = 0
        self.pan_state["accumulated_dy"] = 0
        self.pan_state["last_update"] = time.time() * 1000
        self.pan_state["pending_update"] = None

        # Use blit for faster rendering if available
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _on_pan_end_current(self, event):
        """End panning current plot."""
        # Cancel any pending update
        if self.pan_state.get("pending_update"):
            self.after_cancel(self.pan_state["pending_update"])

        # Do final update with accumulated movement
        if self.pan_state.get("active"):
            self._do_pan_update()

        self.pan_state["active"] = False
        self.pan_state["pending_update"] = None

        # Final redraw
        if hasattr(self, "current_canvas"):
            self.current_canvas.draw()

    def _save_plot(self):
        """Save current plot to file."""
        if self.current_plot not in self.figures:
            messagebox.showwarning("Предупреждение", "Нет графика для сохранения")
            return

        plot_names = {"pressure": "Давление", "gas": "Газ", "liquid": "Жидкость", "all": "Все"}
        plot_name = plot_names.get(self.current_plot, self.current_plot)

        file_path = filedialog.asksaveasfilename(
            title=f"Сохранить график ({plot_name})",
            defaultextension=".png",
            filetypes=[
                ("PNG файлы", "*.png"),
                ("PDF файлы", "*.pdf"),
                ("SVG файлы", "*.svg"),
                ("Все файлы", "*.*"),
            ],
        )

        if not file_path:
            return

        try:
            fig = self.figures[self.current_plot]
            dpi = self.plot_settings.export_dpi
            # Use theme-appropriate background color
            bg_color = (
                COLORS["plot_bg"]
                if "plot_bg" in COLORS
                else ("white" if not ThemeManager.is_dark() else "#1e293b")
            )
            fig.savefig(Path(file_path), dpi=dpi, bbox_inches="tight", facecolor=bg_color)
            messagebox.showinfo("Успех", f"График сохранен:\n{file_path}\n(DPI: {dpi})")
            self._update_status(f"График сохранен: {Path(file_path).name}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении:\n{str(e)}")
            logger.error(f"Error saving plot: {e}", exc_info=True)

    def _show_plot_settings(self):
        """Show plot settings dialog."""
        from visualize_app.ui.dialogs import PlotSettingsDialog

        def on_settings_apply(new_settings: PlotSettings):
            self.plot_settings = new_settings
            self.plot_engine.settings = new_settings
            if self.current_data is not None:
                self._generate_plots()

        PlotSettingsDialog(self, self.plot_settings, on_apply=on_settings_apply)

    def _clear_all(self):
        """Clear all data and plots."""
        self.current_data = None
        self.current_file_path = None
        self.figures.clear()
        self.plot_engine.close_all()

        # Clear thumbnails
        self.thumbnails.clear()
        self.thumbnail_frames.clear()
        for widget in self.thumbnails_container.winfo_children():
            widget.destroy()

        # Show thumbnails placeholder
        self.thumbnails_placeholder.pack(pady=8)

        # Reset file label
        self.file_path_label.configure(text="Файл не выбран", text_color=COLORS["text_secondary"])

        # Clear canvas
        for widget in self.canvas_frame.winfo_children():
            if widget != self.placeholder:
                widget.destroy()

        # Show placeholder
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Clear info
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(
            "1.0", "Нажмите 'Открыть'\nили выберите из истории\n\nФорматы: .xlsx, .xls"
        )
        self.info_text.configure(state="disabled")

        self._update_status("Данные очищены")

    def _update_info_text(self):
        """Update info text with current data information."""
        if self.current_data is None:
            return

        # Calculate statistics
        pressure = self.current_data.pressure
        gas_temp = self.current_data.gas_temperature
        liquid_temp = self.current_data.liquid_temperature

        p_min, p_max = float(min(pressure)), float(max(pressure))
        p_avg = float(np.mean(pressure))

        g_min, g_max = float(min(gas_temp)), float(max(gas_temp))
        g_avg = float(np.mean(gas_temp))

        l_min, l_max = float(min(liquid_temp)), float(max(liquid_temp))
        l_avg = float(np.mean(liquid_temp))

        duration = float(self.current_data.hours[-1])

        info = f"""Общая информация
─────────────────────
Записей:    {self.current_data.size:,}
Время:      {duration:.1f} ч

Давление (кПа)
─────────────────────
Мин:    {p_min:>8.1f}
Макс:   {p_max:>8.1f}
Средн:  {p_avg:>8.1f}

Температура газа (°C)
─────────────────────
Мин:    {g_min:>8.1f}
Макс:   {g_max:>8.1f}
Средн:  {g_avg:>8.1f}

Температура жидк. (°C)
─────────────────────
Мин:    {l_min:>8.1f}
Макс:   {l_max:>8.1f}
Средн:  {l_avg:>8.1f}"""

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", info)
        self.info_text.configure(state="disabled")

    def _update_status(self, message: str):
        """Update status (no-op, status bar removed)."""
        pass

    def _toggle_sidebar(self):
        """Toggle sidebar visibility."""
        if self.sidebar_visible:
            # Hide the control panel
            self.control_frame.grid_forget()
            self.sidebar_visible = False
        else:
            # Show the control panel
            self.control_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
            self.sidebar_visible = True

    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        ThemeManager.toggle()

    def _apply_theme(self):
        """Apply current theme to all UI components."""
        # Update main window
        self.configure(fg_color=COLORS["bg_dark"])

        # Update top bar
        self.top_bar.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])

        # Update menu buttons
        self.menu_file_btn.configure(
            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
        )
        self.menu_view_btn.configure(
            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
        )

        # Update file label
        self.file_path_label.configure(text_color=COLORS["text_secondary"])

        # Update sidebar toggle button
        self.toggle_btn.configure(
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
        )

        # Update thumbnails placeholder
        if hasattr(self, "thumbnails_placeholder"):
            self.thumbnails_placeholder.configure(text_color=COLORS["text_secondary"])

        # Update control frame
        self.control_frame.configure(fg_color=COLORS["bg_secondary"])

        # Update plot frame
        self.plot_frame.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])

        # Update canvas frame
        self.canvas_frame.configure(fg_color=COLORS["bg_card"])

        # Update dropdown menus
        self.file_menu.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])
        self.view_menu.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])
        # Update menu items (buttons and labels)
        self._update_menu_items(self.file_menu)
        self._update_menu_items(self.view_menu)

        # Update buttons in control panel
        self.btn_plot_settings.configure(
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
        )

        # Update clear button
        if hasattr(self, "btn_clear"):
            self.btn_clear.configure(
                fg_color=COLORS["accent_danger"],
                hover_color="#dc2626" if not ThemeManager.is_dark() else "#b91c1c",
            )

        # Update setup config button
        if hasattr(self, "btn_setup_config"):
            self.btn_setup_config.configure(
                fg_color=COLORS["accent_primary"], hover_color=COLORS["accent_secondary"]
            )

        # Update setup combo
        if hasattr(self, "setup_combo"):
            self.setup_combo.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
                button_color=COLORS["accent_primary"],
                text_color=COLORS["text_primary"],
            )

        # Update info text
        if hasattr(self, "info_text"):
            self.info_text.configure(
                fg_color=COLORS["bg_secondary"], text_color=COLORS["text_primary"]
            )

        # Update setup info text
        if hasattr(self, "setup_info_text"):
            self.setup_info_text.configure(
                fg_color=COLORS["bg_secondary"], text_color=COLORS["text_secondary"]
            )

        # Update all cards in sidebar
        if hasattr(self, "setup_card"):
            self.setup_card.configure(fg_color=COLORS["bg_card"])
        if hasattr(self, "setup_label"):
            self.setup_label.configure(text_color=COLORS["text_primary"])
        if hasattr(self, "setup_info_card"):
            self.setup_info_card.configure(fg_color=COLORS["bg_card"])
        if hasattr(self, "setup_info_label"):
            self.setup_info_label.configure(text_color=COLORS["text_primary"])
        if hasattr(self, "stats_card"):
            self.stats_card.configure(fg_color=COLORS["bg_card"])
        if hasattr(self, "stats_label"):
            self.stats_label.configure(text_color=COLORS["text_primary"])

        # Update sidebar header
        if hasattr(self, "sidebar_title"):
            self.sidebar_title.configure(text_color=COLORS["text_primary"])

        # Update placeholder labels
        if hasattr(self, "placeholder_text"):
            self.placeholder_text.configure(text_color=COLORS["text_secondary"])
        if hasattr(self, "placeholder_hint"):
            self.placeholder_hint.configure(text_color=COLORS["text_secondary"])

        # Update thumbnail buttons
        self._update_thumbnail_selection()

        # Update header in control panel
        self._update_child_widgets(self.control_frame)

        # Update plot engine theme
        self.plot_engine.set_dark_mode(ThemeManager.is_dark())

        # Regenerate plots with new theme if data is loaded
        if self.current_data is not None:
            self._generate_plots()

        logger.info(f"Theme changed to: {ThemeManager.get_theme()}")

    def _update_menu_items(self, menu_frame):
        """Update all items in a dropdown menu."""
        for child in menu_frame.winfo_children():
            widget_class = child.__class__.__name__
            if widget_class == "CTkFrame":
                # Update separator or item frame
                try:
                    height = child.cget("height")
                    if height == 1:  # Separator
                        child.configure(fg_color=COLORS["border"])
                except Exception:
                    pass
                # Recurse into item frames
                for subchild in child.winfo_children():
                    subclass = subchild.__class__.__name__
                    if subclass == "CTkButton":
                        subchild.configure(
                            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
                        )
                    elif subclass == "CTkLabel":
                        subchild.configure(text_color=COLORS["text_secondary"])

    def _update_child_widgets(self, parent):
        """Recursively update child widget colors."""
        for child in parent.winfo_children():
            widget_class = child.__class__.__name__
            try:
                if widget_class == "CTkFrame":
                    # Check if it's a card
                    current_fg = child.cget("fg_color")
                    if current_fg in [
                        "#f0f4f8",
                        "#334155",
                        LIGHT_THEME.get("bg_card"),
                        DARK_THEME.get("bg_card"),
                    ]:
                        child.configure(fg_color=COLORS["bg_card"])
                    elif current_fg == "transparent":
                        pass  # Keep transparent
                    else:
                        child.configure(fg_color=COLORS["bg_secondary"])
                elif widget_class == "CTkLabel":
                    current_color = child.cget("text_color")
                    if current_color in [
                        "#64748b",
                        "#94a3b8",
                        LIGHT_THEME.get("text_secondary"),
                        DARK_THEME.get("text_secondary"),
                    ]:
                        child.configure(text_color=COLORS["text_secondary"])
                    else:
                        child.configure(text_color=COLORS["text_primary"])
                elif widget_class == "CTkButton":
                    # Only update non-accent buttons
                    current_fg = child.cget("fg_color")
                    if current_fg == "transparent":
                        child.configure(
                            hover_color=COLORS["hover_light"], text_color=COLORS["text_primary"]
                        )
            except Exception:
                pass  # Skip widgets that don't support these options

            # Recurse into children
            self._update_child_widgets(child)

    def _show_recent_files(self):
        """Show modern recent files modal."""
        recent_files = self.file_history.get_recent()

        if not recent_files:
            messagebox.showinfo("История", "История файлов пуста")
            return

        # Create modern popup window
        popup = ctk.CTkToplevel(self)
        popup.title("Недавние файлы")
        popup.geometry("700x520")
        popup.transient(self)
        popup.grab_set()
        popup.configure(fg_color=COLORS["bg_dark"])

        # Center popup
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (700 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (520 // 2)
        popup.geometry(f"700x520+{x}+{y}")

        # Header
        header_frame = ctk.CTkFrame(popup, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(28, 18))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Недавние файлы",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(popup, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", padx=28, pady=(0, 18))

        # Scrollable frame for files
        scroll_frame = ctk.CTkScrollableFrame(
            popup,
            fg_color=COLORS["bg_secondary"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        scroll_frame.pack(fill="both", expand=True, padx=28, pady=(0, 18))

        # Add file cards
        for i, item in enumerate(recent_files):
            file_path = item["path"]
            file_name = item["name"]

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

            file_path_short = file_path if len(file_path) <= 55 else "..." + file_path[-52:]
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
                command=lambda fp=file_path: self._load_from_history(fp, popup),
            )
            open_btn.pack(side="right")

        # Footer with clear button
        footer_frame = ctk.CTkFrame(popup, fg_color="transparent")
        footer_frame.pack(fill="x", padx=28, pady=(0, 28))

        btn_clear_history = ctk.CTkButton(
            footer_frame,
            text="Очистить историю",
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_danger"],
            hover_color="#dc2626",
            corner_radius=12,
            command=lambda: self._clear_history(popup),
        )
        btn_clear_history.pack(fill="x")

    def _load_from_history(self, file_path: str, popup):
        """Load file from history and close popup."""
        popup.destroy()
        if Path(file_path).exists():
            self._load_file(file_path)
        else:
            messagebox.showerror("Ошибка", f"Файл не найден:\n{file_path}")

    def _clear_history(self, popup):
        """Clear file history."""
        result = messagebox.askyesno("Подтверждение", "Очистить всю историю файлов?")
        if result:
            self.file_history.clear()
            popup.destroy()
            messagebox.showinfo("Успех", "История очищена")

    def _show_setup_config_dialog(self):
        """Show setup configuration dialog."""
        # Create modern popup window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Настройки установки")
        dialog.geometry("580x650")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=COLORS["bg_dark"])

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (580 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (650 // 2)
        dialog.geometry(f"580x650+{x}+{y}")

        # Header
        header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(28, 18))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Параметры установки",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.pack(side="left")

        # Divider
        divider = ctk.CTkFrame(dialog, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", padx=28, pady=(0, 22))

        # Form container
        form_frame = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_secondary"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
        )
        form_frame.pack(fill="x", padx=28, pady=(0, 18))

        # Get current parameters
        params = self.setup_config.get_parameters()

        # Setup name field
        name_label = ctk.CTkLabel(
            form_frame,
            text="Название установки",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        name_label.pack(anchor="w", padx=24, pady=(20, 6))

        name_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
        )
        name_entry.pack(fill="x", padx=24, pady=(0, 16))
        name_entry.insert(0, params.setup_name)

        # Pressure unit field
        pressure_label = ctk.CTkLabel(
            form_frame,
            text="Единицы измерения давления",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        pressure_label.pack(anchor="w", padx=24, pady=(0, 6))

        pressure_units = ["кПа", "МПа", "бар", "атм"]
        pressure_combo = ctk.CTkComboBox(
            form_frame,
            values=pressure_units,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            button_color=COLORS["accent_primary"],
            dropdown_font=ctk.CTkFont(size=14),
            corner_radius=10,
        )
        pressure_combo.pack(fill="x", padx=24, pady=(0, 16))
        pressure_combo.set(params.pressure_unit)

        # Vessel volume field
        vessel_label = ctk.CTkLabel(
            form_frame,
            text="Объем сосуда (литры)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        vessel_label.pack(anchor="w", padx=24, pady=(0, 6))

        vessel_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Введите объем сосуда",
        )
        vessel_entry.pack(fill="x", padx=24, pady=(0, 16))
        vessel_entry.insert(0, str(params.vessel_volume) if params.vessel_volume > 0 else "")

        # Water volume field
        water_label = ctk.CTkLabel(
            form_frame,
            text="Объем воды (литры)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        water_label.pack(anchor="w", padx=24, pady=(0, 6))

        water_entry = ctk.CTkEntry(
            form_frame,
            height=42,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["bg_card"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=10,
            placeholder_text="Введите объем воды",
        )
        water_entry.pack(fill="x", padx=24, pady=(0, 20))
        water_entry.insert(0, str(params.water_volume) if params.water_volume > 0 else "")

        # Buttons frame
        buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=28, pady=(0, 28))

        def save_config():
            """Validate and save configuration."""
            try:
                setup_name = name_entry.get().strip()
                pressure_unit = pressure_combo.get()
                vessel_volume = float(vessel_entry.get().replace(",", "."))
                water_volume = float(water_entry.get().replace(",", "."))

                # Validation
                if not setup_name:
                    messagebox.showerror("Ошибка", "Введите название установки")
                    return

                if vessel_volume <= 0:
                    messagebox.showerror("Ошибка", "Объем сосуда должен быть больше 0")
                    return

                if water_volume <= 0:
                    messagebox.showerror("Ошибка", "Объем воды должен быть больше 0")
                    return

                if water_volume > vessel_volume:
                    messagebox.showerror("Ошибка", "Объем воды не может быть больше объема сосуда")
                    return

                # Save
                self.setup_config.update_parameters(
                    pressure_unit=pressure_unit,
                    vessel_volume=vessel_volume,
                    water_volume=water_volume,
                    setup_name=setup_name,
                )

                # Update display
                self._update_setup_info_display()

                dialog.destroy()
                messagebox.showinfo("Успех", "Параметры установки сохранены")

            except ValueError:
                messagebox.showerror("Ошибка", "Введите корректные числовые значения для объемов")

        btn_save = ctk.CTkButton(
            buttons_frame,
            text="Сохранить",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["accent_success"],
            hover_color="#059669",
            corner_radius=12,
            command=save_config,
        )
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_cancel = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=12,
            command=dialog.destroy,
        )
        btn_cancel.pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _update_setup_info_display(self):
        """Update setup information display in sidebar."""
        params = self.setup_config.get_parameters()

        if self.setup_config.is_configured():
            info = f"""{params.setup_name}
━━━━━━━━━━━━━━━━━━━
Давление: {params.pressure_unit}
Объем сосуда: {params.vessel_volume:.2f} л
Объем воды: {params.water_volume:.2f} л
Объем газа: {params.vessel_volume - params.water_volume:.2f} л"""
        else:
            info = "Параметры не настроены\n\nНажмите 'Настройки установки'\nдля ввода данных"

        self.setup_info_text.configure(state="normal")
        self.setup_info_text.delete("1.0", tk.END)
        self.setup_info_text.insert("1.0", info)
        self.setup_info_text.configure(state="disabled")
