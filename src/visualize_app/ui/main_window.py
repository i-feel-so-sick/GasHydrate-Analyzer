"""
Главное окно приложения ThermoViz.

Координирует взаимодействие между компонентами UI, сервисами и состоянием приложения.
Все UI компоненты создаются через специализированные классы (TopBar, SidebarPanel, PlotArea).
Коммуникация между компонентами происходит через EventBus для слабой связанности.
"""

import logging
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

# Try to import tkinterdnd2 for drag & drop support
try:
    from tkinterdnd2 import DND_FILES
    from tkinterdnd2 import TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False
    logger = logging.getLogger(__name__)

from visualize_app.core import AppState
from visualize_app.core import EventBus
from visualize_app.models import ExperimentalData
from visualize_app.models import PlotSettings
from visualize_app.services import ExcelParser
from visualize_app.services import ExcelParserError
from visualize_app.services import PlotEngine
from visualize_app.services.solubility_engine import analyze_solubility
from visualize_app.services.solubility_plot_engine import create_accumulation_plot
from visualize_app.services.solubility_plot_engine import create_pressure_plot
from visualize_app.services.solubility_plot_engine import create_saturation_plot
from visualize_app.ui.components import PlotArea
from visualize_app.ui.components import SidebarPanel
from visualize_app.ui.components import SolubilityTab
from visualize_app.ui.components import TopBar
from visualize_app.ui.dialogs import PlotSettingsDialog
from visualize_app.ui.dialogs import RecentFilesDialog
from visualize_app.ui.dialogs import SetupConfigDialog
from visualize_app.ui.theme import COLORS
from visualize_app.ui.theme import ThemeManager
from visualize_app.utils.file_history import FileHistory
from visualize_app.utils.pressure_units import convert_pressure_series
from visualize_app.utils.pressure_units import normalize_pressure_unit
from visualize_app.utils.setup_config import SetupConfig
from visualize_app.utils.setup_config import SetupConfigManager

logger = logging.getLogger(__name__)


# Use TkinterDnD as base class if available, otherwise fallback to CTk
if HAS_DND:

    class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        """CustomTkinter window with drag & drop support."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    BaseWindowClass = DnDCTk
else:
    BaseWindowClass = ctk.CTk


class MainWindow(BaseWindowClass):  # type: ignore[misc]
    """
    Главное окно приложения ThermoViz.

    Координирует взаимодействие между:
    - UI компонентами (TopBar, SidebarPanel, PlotArea)
    - Сервисами (PlotEngine, ExcelParser, FileHistory)
    - Состоянием приложения (AppState)
    - Событиями (EventBus)
    """

    def __init__(self):
        """Инициализация главного окна."""
        super().__init__()

        logger.info("Инициализация главного окна приложения")

        # Инициализация ядра приложения
        self.app_state = AppState()
        self.event_bus = EventBus()

        # Инициализация сервисов
        self.plot_engine = PlotEngine()
        self.file_history = FileHistory()
        self.setup_config_manager = SetupConfigManager()

        # Настройка окна
        self._setup_window()

        # Создание компонентов UI
        self._build_ui()

        # Настройка обработчиков событий
        self._setup_event_handlers()

        # Настройка горячих клавиш
        self._setup_keyboard_shortcuts()

        # Настройка drag & drop
        self._setup_drag_and_drop()

        # Регистрация callback для темы
        ThemeManager.register(self._on_theme_changed)

        logger.info("Главное окно успешно инициализировано")

    def _setup_window(self):
        """Настройка главного окна (размер, заголовок, позиция)."""
        self.title("ThermoViz - Визуализация теплофизических экспериментов")
        self.geometry("1500x950")
        self.configure(fg_color=COLORS["bg_dark"])

        # Центрирование окна
        self.center_window()

        # Настройка grid layout для главного окна
        self.grid_rowconfigure(0, weight=0, minsize=0)  # TopBar
        self.grid_rowconfigure(1, weight=0, minsize=0)  # Sub-bar
        self.grid_rowconfigure(2, weight=1)  # Content area
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        logger.debug("Окно настроено: размер 1500x950, позиция центрирована")

    def center_window(self):
        """Центрирование окна на экране."""
        self.update_idletasks()
        width = 1500
        height = 950
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Создание и размещение UI компонентов в grid layout."""
        logger.debug("Создание компонентов UI")

        # TopBar component
        self.top_bar = TopBar(
            parent=self,
            app_state=self.app_state,
            event_bus=self.event_bus,
            on_toggle_sidebar=self._toggle_sidebar,
            on_file_open=self._select_file,
            on_file_save=self._save_plot,
            on_file_clear=self._clear_all,
            on_recent_files=self._show_recent_files,
            on_reset_zoom=self._reset_zoom,
            on_zoom_in=self._zoom_in,
            on_zoom_out=self._zoom_out,
            on_theme_toggle=self._toggle_theme,
        )
        # Передаём колбэки для вкладок главного переключателя в TopBar
        self._active_main_tab = "data"
        top_bar_widget = self.top_bar.build()
        top_bar_widget.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)

        # ── Sub-bar: Данные/Растворимость + кнопки графиков (row 1) ──────
        self._sub_bar = ctk.CTkFrame(
            self,
            height=44,
            corner_radius=0,
            fg_color=COLORS["bg_secondary"],
        )
        self._sub_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self._sub_bar.grid_propagate(False)
        self._sub_bar.pack_propagate(False)

        ctk.CTkFrame(self._sub_bar, height=1, fg_color=COLORS["border"]).pack(
            side="bottom", fill="x"
        )

        # Левая часть — переключатель Данные / Растворимость
        tab_section = ctk.CTkFrame(self._sub_bar, fg_color="transparent")
        tab_section.pack(side="left", padx=(12, 0), pady=6)

        self._tab_data_btn = ctk.CTkButton(
            tab_section,
            text="Данные",
            width=100,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_primary"],
            hover_color=COLORS["accent_secondary"],
            text_color="#ffffff",
            corner_radius=8,
            command=lambda: self._switch_main_tab("data"),
        )
        self._tab_data_btn.pack(side="left", padx=(0, 4))

        self._tab_sol_btn = ctk.CTkButton(
            tab_section,
            text="Растворимость CO₂",
            width=150,
            height=32,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._switch_main_tab("solubility"),
        )
        self._tab_sol_btn.pack(side="left")

        # Разделитель
        ctk.CTkFrame(self._sub_bar, width=1, fg_color=COLORS["border"]).pack(
            side="left", fill="y", padx=14, pady=8
        )

        # Правая часть — кнопки конкретных графиков
        self._sub_bar_btn_row = ctk.CTkFrame(self._sub_bar, fg_color="transparent")
        self._sub_bar_btn_row.pack(side="left", pady=6)

        self._sub_bar_placeholder = ctk.CTkLabel(
            self._sub_bar_btn_row,
            text="",
            width=0,
        )
        # placeholder is invisible — only shown when needed

        self._sub_bar_btns: dict = {}

        # Храним кнопки для каждой вкладки отдельно
        self._sub_bar_btns: dict = {}  # кнопки вкладки "data"
        self._sub_bar_sol_btns: dict = {}  # кнопки вкладки "solubility"

        # Подписки на события для sub-bar
        self.event_bus.subscribe("plot:generated", self._on_sub_bar_plots_generated)
        self.event_bus.subscribe("plot:switch", self._on_sub_bar_plot_switch)
        self.event_bus.subscribe("file:clear", self._on_sub_bar_cleared)
        self.event_bus.subscribe("solubility:ready", self._on_sub_bar_sol_ready)
        self.event_bus.subscribe("solubility:switch", self._on_sub_bar_sol_switch)

        # SidebarPanel component
        self.sidebar = SidebarPanel(
            parent=self,
            app_state=self.app_state,
            event_bus=self.event_bus,
            setup_config=self.setup_config_manager,
            on_plot_settings=self._show_plot_settings,
            on_clear_data=self._clear_all,
            on_setup_config=self._edit_setup_config,
            on_add_setup=self._add_new_setup,
        )
        sidebar_widget = self.sidebar.build()
        sidebar_widget.grid(row=2, column=0, sticky="nsw", padx=0, pady=0)

        # PlotArea component (Данные tab)
        self.plot_area = PlotArea(parent=self, app_state=self.app_state, event_bus=self.event_bus)
        self._plot_area_widget = self.plot_area.build()
        self._plot_area_widget.grid(row=2, column=1, sticky="nsew", padx=(8, 12), pady=(8, 12))

        # SolubilityTab component (hidden initially)
        self.solubility_tab = SolubilityTab(
            parent=self,
            app_state=self.app_state,
            event_bus=self.event_bus,
        )
        self._sol_tab_widget = self.solubility_tab.build()
        # not gridded yet — shown on tab switch

        logger.debug("Компоненты UI созданы и размещены")

    def _update_main_tab_buttons(self):
        """Re-apply tab button colours after theme change."""
        active = self._active_main_tab
        if self._tab_data_btn and self._tab_sol_btn:
            if active == "data":
                self._tab_data_btn.configure(
                    fg_color=COLORS["accent_primary"],
                    hover_color=COLORS["accent_secondary"],
                    text_color="#ffffff",
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
                self._tab_sol_btn.configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=13),
                )
            else:
                self._tab_sol_btn.configure(
                    fg_color=COLORS["accent_primary"],
                    hover_color=COLORS["accent_secondary"],
                    text_color="#ffffff",
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
                self._tab_data_btn.configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=13),
                )

    def _switch_main_tab(self, tab: str):
        """Switch between 'data' and 'solubility' main tabs."""
        if tab == self._active_main_tab:
            return
        self._active_main_tab = tab
        self._update_main_tab_buttons()
        self._refresh_sub_bar_buttons()

        if tab == "data":
            self._sol_tab_widget.grid_forget()
            self._plot_area_widget.grid(row=2, column=1, sticky="nsew", padx=(8, 12), pady=(8, 12))
        else:
            self._plot_area_widget.grid_forget()
            self._sol_tab_widget.grid(row=2, column=1, sticky="nsew", padx=(8, 12), pady=(8, 12))

    def _refresh_sub_bar_buttons(self):
        """Show the right set of graph buttons for the active tab."""
        if self._active_main_tab == "data":
            for btn in self._sub_bar_sol_btns.values():
                btn.pack_forget()
            current = self.app_state.current_plot
            if self._sub_bar_btns:
                self._sub_bar_placeholder.pack_forget()
                for pid, btn in self._sub_bar_btns.items():
                    is_active = pid == current
                    btn.configure(
                        fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                        hover_color=COLORS["accent_secondary"]
                        if is_active
                        else COLORS["hover_light"],
                        text_color="#ffffff" if is_active else COLORS["text_primary"],
                        font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                    )
                    btn.pack(side="left", padx=3)
            else:
                self._sub_bar_placeholder.pack(side="left", padx=4)
        else:
            for btn in self._sub_bar_btns.values():
                btn.pack_forget()
            current = self.app_state.current_sol_plot
            if self._sub_bar_sol_btns:
                self._sub_bar_placeholder.pack_forget()
                for pid, btn in self._sub_bar_sol_btns.items():
                    is_active = pid == current
                    btn.configure(
                        fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                        hover_color=COLORS["accent_secondary"]
                        if is_active
                        else COLORS["hover_light"],
                        text_color="#ffffff" if is_active else COLORS["text_primary"],
                        font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                    )
                    btn.pack(side="left", padx=3)
            else:
                self._sub_bar_placeholder.pack(side="left", padx=4)

    def _setup_event_handlers(self):
        """Подписка на события из EventBus."""
        logger.debug("Настройка обработчиков событий")

        self.event_bus.subscribe("file:loaded", self._on_file_loaded)
        self.event_bus.subscribe("plot:switch", self._on_plot_switch)
        self.event_bus.subscribe("settings:changed", self._on_settings_changed)
        self.event_bus.subscribe("time_filter:changed", self._on_time_filter_changed)
        self.event_bus.subscribe("signal_downsample:changed", self._on_signal_downsample_changed)
        self.event_bus.subscribe("solubility:switch", self._on_sol_plot_switch)

        logger.debug("Обработчики событий настроены")

    def _setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш."""
        logger.debug("Настройка горячих клавиш")

        # Файл
        self.bind("<Control-o>", lambda e: self._select_file())
        self.bind("<Control-O>", lambda e: self._select_file())
        self.bind("<Control-s>", lambda e: self._save_plot())
        self.bind("<Control-S>", lambda e: self._save_plot())

        # Вид
        self.bind("<Control-b>", lambda e: self._toggle_sidebar())
        self.bind("<Control-B>", lambda e: self._toggle_sidebar())
        self.bind("<Control-d>", lambda e: self._toggle_theme())
        self.bind("<Control-D>", lambda e: self._toggle_theme())

        # Масштаб
        self.bind("<Control-0>", lambda e: self._reset_zoom())
        self.bind("<Control-plus>", lambda e: self._zoom_in())
        self.bind("<Control-equal>", lambda e: self._zoom_in())  # = на клавиатуре без Shift
        self.bind("<Control-minus>", lambda e: self._zoom_out())

        # Переключение графиков (1-9)
        for idx in range(1, 10):
            self.bind(f"<Control-{idx}>", lambda e, i=idx - 1: self._switch_plot_by_index(i))

        logger.debug("Горячие клавиши настроены")

    def _setup_drag_and_drop(self):
        """Настройка drag & drop для файлов."""
        if not HAS_DND:
            logger.debug("tkinterdnd2 не установлен, drag & drop недоступен")
            return

        try:
            # Регистрируем окно для приёма файлов
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_file_drop)

            logger.debug("Drag & drop настроен")
        except Exception as e:
            logger.warning(f"Не удалось настроить drag & drop: {e}")

    def _on_file_drop(self, event):
        """
        Обработка события перетаскивания файла.

        Args:
            event: Событие с данными о файле
        """
        # Получаем путь к файлу (может быть в фигурных скобках на Windows)
        file_path = event.data.strip()

        # Убираем фигурные скобки если есть (Windows с пробелами в пути)
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]

        # Проверяем расширение
        path = Path(file_path)
        if path.suffix.lower() not in [".xlsx", ".xls"]:
            messagebox.showwarning(
                "Неподдерживаемый формат",
                f"Файл '{path.name}' не является Excel файлом.\n\n"
                "Поддерживаемые форматы: .xlsx, .xls",
            )
            return

        logger.info(f"Файл перетащен: {file_path}")
        self._load_file(path)

    # ==================== Event Handlers ====================

    def _on_file_loaded(self, data: ExperimentalData):
        """
        Обработка события загрузки файла.

        Args:
            data: Загруженные экспериментальные данные
        """
        logger.info(f"Обработка события загрузки файла: {data.size} точек данных")

        # Генерация графиков данных
        self._generate_plots()

        # Расчёт и генерация графиков растворимости
        self._generate_solubility_plots()

        # Обновление UI происходит автоматически через подписки компонентов на события

    def _on_plot_switch(self, plot_id: str):
        """
        Обработка события переключения графика.

        Args:
            plot_id: Идентификатор графика (имя колонки)
        """
        logger.info(f"Переключение на график: {plot_id}")

        # Обновление состояния
        self.app_state.current_plot = plot_id

        # PlotArea автоматически обновится через подписку на событие

    def _on_settings_changed(self, settings: PlotSettings):
        """
        Обработка события изменения настроек графиков.

        Args:
            settings: Новые настройки графиков
        """
        logger.info("Настройки графиков изменены, перегенерация графиков")

        # Обновление настроек в состоянии
        self.app_state.plot_settings = settings

        # Перегенерация графиков с новыми настройками
        if self.app_state.current_data:
            self._generate_plots()

    def _on_time_filter_changed(self, time_range):
        """
        Обработка события изменения фильтра времени.

        Args:
            time_range: Кортеж (start_time, end_time) в часах
        """
        logger.info(f"Фильтр времени изменен: {time_range[0]:.1f} - {time_range[1]:.1f} ч")

        # Сохранение фильтра в состоянии
        self.app_state.time_filter = time_range

        # Перегенерация графиков с новым фильтром
        if self.app_state.current_data:
            self._generate_plots()

    def _on_signal_downsample_changed(self, factor):
        """
        Обработка события изменения коэффициента прореживания сигнала.

        Args:
            factor: Целочисленный коэффициент (1 = без прореживания)
        """
        try:
            factor = max(1, int(factor))
        except (TypeError, ValueError):
            factor = 1

        logger.info(f"Коэффициент прореживания сигнала изменен: x{factor}")

        self.app_state.signal_downsample_factor = factor

        if self.app_state.current_data:
            self._generate_plots()

    def _on_theme_changed(self):
        """Обработка события смены темы."""
        logger.info("Тема изменена, обновление UI")

        # Обновление главного окна
        self.configure(fg_color=COLORS["bg_dark"])

        # Обновление всех компонентов
        self.top_bar.update_theme()
        self.sidebar.update_theme()
        self.plot_area.update_theme()
        self.solubility_tab.update_theme()
        self._sub_bar.configure(fg_color=COLORS["bg_secondary"])
        self._update_main_tab_buttons()

    # ==================== Action Handlers (Callbacks) ====================

    def _select_file(self):
        """Выбор файла через диалог и загрузка данных."""
        logger.debug("Открытие диалога выбора файла")

        file_path = filedialog.askopenfilename(
            title="Выберите файл с данными эксперимента",
            filetypes=[("Excel файлы", "*.xlsx *.xls"), ("Все файлы", "*.*")],
        )

        if file_path:
            self._load_file(Path(file_path))

    def _load_file(self, file_path: Path):
        """
        Загрузка и парсинг файла, публикация события 'file:loaded'.

        Args:
            file_path: Путь к файлу Excel
        """
        logger.info(f"Загрузка файла: {file_path}")

        try:
            setup = self.setup_config_manager.get_current_setup()
            if setup is None:
                messagebox.showwarning("Нет установки", "Сначала создайте и выберите установку.")
                return

            # Парсинг файла
            data = ExcelParser.parse_file(
                file_path, time_column=setup.time_column, data_columns=setup.data_columns
            )

            if data.metadata.get("time_source") == "index":
                messagebox.showwarning(
                    "Нет колонки времени",
                    "Колонка времени не найдена. Графики построены по индексу строк.",
                )
            missing_optional = data.metadata.get("missing_optional_columns", "")
            if missing_optional:
                messagebox.showwarning(
                    "Пропущены необязательные столбцы",
                    f"Следующие необязательные столбцы не найдены и были пропущены:\n{missing_optional}",
                )

            # Обновление состояния
            self.app_state.current_data = data
            self.app_state.current_file_path = file_path

            # Добавление в историю
            self.file_history.add(str(file_path))

            # Публикация события
            self.event_bus.publish("file:loaded", data)

            logger.info(f"Файл успешно загружен: {data.size} точек данных")
            messagebox.showinfo(
                "Успех",
                f"Файл успешно загружен!\n\nТочек данных: {data.size}\n"
                f"Период: {data.hours[0]:.2f} - {data.hours[-1]:.2f} ч",
            )

        except ExcelParserError as e:
            logger.error(f"Ошибка парсинга файла: {e}")
            messagebox.showerror("Ошибка загрузки", str(e))
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при загрузке файла: {e}")
            messagebox.showerror("Ошибка", f"Неожиданная ошибка при загрузке файла:\n{str(e)}")

    def _generate_plots(self):
        """Генерация всех графиков, публикация события 'plot:generated'."""
        import matplotlib.pyplot as plt

        if not self.app_state.current_data:
            logger.warning("Попытка генерации графиков без данных")
            return

        logger.info("Генерация графиков")

        try:
            # Close old figures to prevent memory leaks
            for fig in self.app_state.figures.values():
                plt.close(fig)

            data = self.app_state.current_data
            settings = self.app_state.plot_settings
            figures = {}
            setup = self.setup_config_manager.get_current_setup()
            if not setup or not setup.data_columns:
                logger.warning("Не настроены колонки данных для установки")
                return

            # Применение фильтра времени если задан
            if self.app_state.time_filter:
                start_time, end_time = self.app_state.time_filter
                data = self._filter_data_by_time(data, start_time, end_time)
                if data is None or data.size == 0:
                    logger.warning("После фильтрации не осталось данных")
                    return

            # Прореживание сигнала (уменьшение частоты дискретизации отображения)
            downsample_factor = max(1, int(getattr(self.app_state, "signal_downsample_factor", 1)))
            if downsample_factor > 1:
                data = self._downsample_data(data, downsample_factor)

            # Конвертация единиц давления для отображения на графиках
            data_for_plot = self._convert_pressure_units_for_plot(data, setup, settings)

            plot_order = []
            for column in data_for_plot.series.keys():
                unit = data_for_plot.units.get(column, "").strip()
                ylabel = f"{column} ({unit})" if unit else column
                figures[column] = self.plot_engine.create_time_series_plot(
                    data=data_for_plot,
                    y_columns=[column],
                    title=column,
                    ylabel=ylabel,
                    figsize=settings.figure_size,
                    settings=settings,
                )
                plot_order.append(column)

            # Обновление состояния
            self.app_state.figures = figures
            self.app_state.plot_order = plot_order
            if plot_order and self.app_state.current_plot not in plot_order:
                self.app_state.current_plot = plot_order[0]

            # Публикация события
            self.event_bus.publish("plot:generated", figures)

            logger.info("Все графики успешно сгенерированы")

        except Exception as e:
            logger.exception(f"Ошибка при генерации графиков: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при создании графиков:\n{str(e)}")

    def _generate_solubility_plots(self):
        """Расчёт растворимости CO₂ и генерация трёх графиков."""
        import matplotlib.pyplot as plt

        if not self.app_state.current_data:
            return

        logger.info("Генерация графиков растворимости CO₂")

        try:
            # Close old figures
            for fig in self.app_state.solubility_figures.values():
                plt.close(fig)

            data = self.app_state.current_data
            settings = self.app_state.plot_settings

            setup = self.setup_config_manager.get_current_setup()
            V_total = float(getattr(setup, "vessel_volume", 150.0) or 150.0) / 1e6  # мл → м³
            V_water = float(getattr(setup, "water_volume", 100.0) or 100.0) / 1e6
            m_water = V_water * 1000.0  # кг (плотность воды ~1 кг/л)

            result = analyze_solubility(
                data,
                V_total=V_total,
                V_water=V_water,
                m_water=m_water,
            )

            figures = {
                "pressure": create_pressure_plot(result, settings),
                "accumulation": create_accumulation_plot(result, settings),
                "saturation": create_saturation_plot(result, settings),
            }
            plot_order = ["pressure", "accumulation", "saturation"]

            self.app_state.solubility_figures = figures
            self.app_state.sol_plot_order = plot_order
            if not self.app_state.current_sol_plot:
                self.app_state.current_sol_plot = "pressure"

            self.event_bus.publish("solubility:ready", None)
            logger.info(
                "Графики растворимости сгенерированы (%d точек, %d подкачек)",
                len(result.time_hours),
                len(result.injection_indices),
            )

        except Exception as e:
            logger.warning("Не удалось рассчитать растворимость: %s", e)

    def _on_sol_plot_switch(self, plot_id: str):
        """Handle solubility plot switch (update state, SolubilityTab handles display)."""
        self.app_state.current_sol_plot = plot_id

    def _convert_pressure_units_for_plot(
        self, data: ExperimentalData, setup: SetupConfig, settings: PlotSettings
    ) -> ExperimentalData:
        """Convert pressure data for plot display according to selected units and setup coefficient."""
        pressure_columns = self._detect_pressure_columns(data, setup)
        if not pressure_columns:
            return data

        coefficient = float(getattr(setup, "pressure_coefficient", 1.0) or 1.0)

        target_setting = getattr(settings, "pressure_display_unit", "setup")
        target_unit = normalize_pressure_unit(target_setting) if target_setting != "setup" else ""
        if target_setting != "setup" and not target_unit:
            logger.warning("Неизвестная единица отображения давления: %s", target_setting)
            return data

        converted_series = {name: list(values) for name, values in data.series.items()}
        converted_units = data.units.copy()
        changed = False

        for column in pressure_columns:
            source_unit = self._get_pressure_source_unit(column, data, setup)

            # Apply coefficient to raw values
            raw_series = data.series[column]
            if coefficient != 1.0:
                raw_series = [v * coefficient for v in raw_series]
                changed = True

            if target_setting == "setup":
                converted_series[column] = raw_series
                if source_unit and converted_units.get(column, "").strip() != source_unit:
                    converted_units[column] = source_unit
                    changed = True
            else:
                if not source_unit:
                    logger.warning("Не удалось определить единицу давления для '%s'", column)
                    converted_series[column] = raw_series
                    continue

                try:
                    if source_unit != target_unit:
                        converted_series[column] = convert_pressure_series(
                            raw_series, source_unit, target_unit
                        )
                    else:
                        converted_series[column] = raw_series
                    converted_units[column] = target_unit
                    changed = True
                except ValueError as exc:
                    logger.warning("Не удалось конвертировать давление для '%s': %s", column, exc)
                    converted_series[column] = raw_series
                    continue

        if not changed:
            return data

        return ExperimentalData(
            hours=list(data.hours),
            series=converted_series,
            units=converted_units,
            metadata=data.metadata.copy(),
        )

    def _detect_pressure_columns(self, data: ExperimentalData, setup: SetupConfig) -> list[str]:
        """Detect pressure columns by schema unit and common column names."""
        pressure_columns: list[str] = []
        for column in data.series.keys():
            column_name = column.strip().lower()
            is_pressure_name = column_name in {"давление", "pressure"}
            has_pressure_unit = bool(self._get_pressure_source_unit(column, data, setup))

            if is_pressure_name or has_pressure_unit:
                pressure_columns.append(column)

        return pressure_columns

    def _get_pressure_source_unit(
        self, column: str, data: ExperimentalData, setup: SetupConfig
    ) -> str:
        """Get source pressure unit for a specific column."""
        parsed_unit = normalize_pressure_unit(data.units.get(column, ""))
        if parsed_unit:
            return parsed_unit

        for item in setup.data_columns:
            configured_column = str(item.get("column", "")).strip()
            if configured_column != column:
                continue
            configured_unit = normalize_pressure_unit(item.get("unit", ""))
            if configured_unit:
                return configured_unit
            return ""  # Column found but not a pressure unit — don't fall through

        setup_unit = normalize_pressure_unit(setup.pressure_unit)
        return setup_unit

    def _filter_data_by_time(
        self, data: ExperimentalData, start_time: float, end_time: float
    ) -> Optional[ExperimentalData]:
        """
        Фильтрация данных по временному диапазону.

        Args:
            data: Исходные данные
            start_time: Начальное время (часы)
            end_time: Конечное время (часы)

        Returns:
            Отфильтрованные данные или None если нет данных в диапазоне
        """
        import numpy as np

        # Находим индексы для фильтрации
        hours_array = np.array(data.hours)
        mask = (hours_array >= start_time) & (hours_array <= end_time)

        if not np.any(mask):
            return None

        # Создаём новый объект с отфильтрованными данными
        filtered_series = {}
        for name, values in data.series.items():
            filtered_series[name] = [values[i] for i in range(len(values)) if mask[i]]

        filtered_data = ExperimentalData(
            hours=[data.hours[i] for i in range(len(data.hours)) if mask[i]],
            series=filtered_series,
            units=data.units.copy(),
            metadata=data.metadata.copy(),
        )

        logger.debug(f"Данные отфильтрованы: {filtered_data.size} из {data.size} точек")
        return filtered_data

    def _downsample_data(self, data: ExperimentalData, factor: int) -> ExperimentalData:
        """
        Прореживание данных для отображения (каждая N-я точка).

        Args:
            data: Исходные данные
            factor: Коэффициент прореживания (1 = без изменений)

        Returns:
            Новый объект данных с уменьшенной частотой дискретизации
        """
        factor = max(1, int(factor))
        if factor <= 1 or data.size <= 2:
            return data

        indices = list(range(0, data.size, factor))
        if indices and indices[-1] != data.size - 1:
            indices.append(data.size - 1)

        downsampled_series = {
            name: [values[i] for i in indices] for name, values in data.series.items()
        }

        result = ExperimentalData(
            hours=[data.hours[i] for i in indices],
            series=downsampled_series,
            units=data.units.copy(),
            metadata=data.metadata.copy(),
        )

        logger.debug("Прореживание данных: %s -> %s точек (x%s)", data.size, result.size, factor)
        return result

    def _switch_plot_by_index(self, index: int):
        """Switch plot by index in current plot order."""
        plot_order = self.app_state.plot_order
        if 0 <= index < len(plot_order):
            self.event_bus.publish("plot:switch", plot_order[index])

    def _save_plot(self):
        """Сохранение текущего графика в файл."""
        if not self.app_state.current_plot_id or not self.app_state.figures:
            logger.warning("Попытка сохранения графика без данных")
            messagebox.showwarning(
                "Предупреждение", "Нет графика для сохранения. Сначала загрузите данные."
            )
            return

        logger.debug("Открытие диалога сохранения графика")

        file_path = filedialog.asksaveasfilename(
            title="Сохранить график",
            defaultextension=".png",
            filetypes=[
                ("PNG изображение", "*.png"),
                ("PDF документ", "*.pdf"),
                ("SVG векторная графика", "*.svg"),
                ("Все файлы", "*.*"),
            ],
        )

        if file_path:
            try:
                figure = self.app_state.figures.get(self.app_state.current_plot_id)
                if figure:
                    dpi = self.app_state.plot_settings.export_dpi
                    figure.savefig(file_path, dpi=dpi, bbox_inches="tight")
                    logger.info(f"График сохранен: {file_path}")
                    messagebox.showinfo("Успех", f"График успешно сохранен:\n{file_path}")
                else:
                    logger.error("График не найден в состоянии")
                    messagebox.showerror("Ошибка", "График не найден")

            except Exception as e:
                logger.exception(f"Ошибка при сохранении графика: {e}")
                messagebox.showerror("Ошибка", f"Не удалось сохранить график:\n{str(e)}")

    def _clear_all(self):
        """Очистка всех данных, публикация события 'file:clear'."""
        logger.info("Очистка всех данных")

        # Подтверждение от пользователя
        if self.app_state.current_data:
            response = messagebox.askyesno(
                "Подтверждение",
                "Вы уверены, что хотите очистить все данные?\n"
                "Все несохраненные изменения будут потеряны.",
            )
            if not response:
                logger.debug("Очистка данных отменена пользователем")
                return

        # Очистка состояния
        self.app_state.clear_data()

        # Публикация события
        self.event_bus.publish("file:clear", None)

        logger.info("Все данные очищены")

    def _show_plot_settings(self):
        """Показ диалога настроек графиков."""
        logger.debug("Открытие диалога настроек графиков")

        PlotSettingsDialog(
            parent=self, current_settings=self.app_state.plot_settings, event_bus=self.event_bus
        )

    def _show_recent_files(self):
        """Показ диалога истории файлов."""
        logger.debug("Открытие диалога истории файлов")

        recent_items = self.file_history.get_recent()

        if not recent_items:
            messagebox.showinfo(
                "Информация", "История файлов пуста.\nОткройте файл, чтобы он появился в истории."
            )
            return

        # Extract just the paths for the dialog
        recent_paths = [item["path"] for item in recent_items]

        RecentFilesDialog(
            parent=self, recent_files=recent_paths, on_select_callback=self._load_file
        )

    def _add_new_setup(self):
        """Добавление новой конфигурации установки."""
        logger.debug("Открытие диалога создания новой установки")

        SetupConfigDialog(
            parent=self,
            setup_config_manager=self.setup_config_manager,
            event_bus=self.event_bus,
            edit_setup=None,
        )

    def _edit_setup_config(self, setup: SetupConfig | None = None):
        """
        Редактирование существующей конфигурации установки.

        Args:
            setup: Конфигурация для редактирования, или None для текущей
        """
        logger.debug("Открытие диалога редактирования установки")

        if setup is None:
            setup = self.setup_config_manager.get_current_setup()

        if setup is None:
            logger.warning("Нет установки для редактирования")
            return

        SetupConfigDialog(
            parent=self,
            setup_config_manager=self.setup_config_manager,
            event_bus=self.event_bus,
            edit_setup=setup,
        )

    # ==================== Sub-bar (plot switcher) ====================

    def _on_sub_bar_plots_generated(self, figures):
        """Rebuild sub-bar buttons when plots are generated."""
        plot_order = self.app_state.plot_order or (list(figures.keys()) if figures else [])
        # Destroy and recreate data tab buttons
        for btn in self._sub_bar_btns.values():
            btn.destroy()
        self._sub_bar_btns.clear()

        if not plot_order:
            if self._active_main_tab == "data":
                self._sub_bar_placeholder.pack(side="left", padx=4)
            return

        current = self.app_state.current_plot
        for plot_id in plot_order:
            is_active = plot_id == current
            btn = ctk.CTkButton(
                self._sub_bar_btn_row,
                text=plot_id,
                width=120,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                hover_color=COLORS["accent_secondary"] if is_active else COLORS["hover_light"],
                text_color="#ffffff" if is_active else COLORS["text_primary"],
                corner_radius=8,
                command=lambda pid=plot_id: self.event_bus.publish("plot:switch", pid),
            )
            self._sub_bar_btns[plot_id] = btn

        # Show only if data tab is active
        if self._active_main_tab == "data":
            self._refresh_sub_bar_buttons()

    def _on_sub_bar_plot_switch(self, plot_id: str):
        """Update sub-bar button highlights."""
        for pid, btn in self._sub_bar_btns.items():
            is_active = pid == plot_id
            btn.configure(
                fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                hover_color=COLORS["accent_secondary"] if is_active else COLORS["hover_light"],
                text_color="#ffffff" if is_active else COLORS["text_primary"],
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
            )

    def _on_sub_bar_cleared(self, _data):
        """Clear sub-bar buttons on file clear."""
        for btn in self._sub_bar_btns.values():
            btn.destroy()
        self._sub_bar_btns.clear()
        for btn in self._sub_bar_sol_btns.values():
            btn.destroy()
        self._sub_bar_sol_btns.clear()
        self._sub_bar_placeholder.pack(side="left", padx=4)

    def _on_sub_bar_sol_ready(self, _data=None):
        """Build solubility graph buttons when calculation is done."""
        _SOL_LABELS = {
            "pressure": "Давление",
            "accumulation": "Накопление CO₂",
            "saturation": "Насыщение",
        }
        for btn in self._sub_bar_sol_btns.values():
            btn.destroy()
        self._sub_bar_sol_btns.clear()

        current = self.app_state.current_sol_plot or "pressure"
        for plot_id in self.app_state.sol_plot_order:
            is_active = plot_id == current
            label = _SOL_LABELS.get(plot_id, plot_id)
            btn = ctk.CTkButton(
                self._sub_bar_btn_row,
                text=label,
                width=130,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                hover_color=COLORS["accent_secondary"] if is_active else COLORS["hover_light"],
                text_color="#ffffff" if is_active else COLORS["text_primary"],
                corner_radius=8,
                command=lambda pid=plot_id: self.event_bus.publish("solubility:switch", pid),
            )
            self._sub_bar_sol_btns[plot_id] = btn

        # Show solubility buttons only if solubility tab is active
        if self._active_main_tab == "solubility":
            self._refresh_sub_bar_buttons()

    def _on_sub_bar_sol_switch(self, plot_id: str):
        """Update solubility sub-bar button highlights."""
        for pid, btn in self._sub_bar_sol_btns.items():
            is_active = pid == plot_id
            btn.configure(
                fg_color=COLORS["accent_primary"] if is_active else COLORS["bg_card"],
                hover_color=COLORS["accent_secondary"] if is_active else COLORS["hover_light"],
                text_color="#ffffff" if is_active else COLORS["text_primary"],
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
            )

    def _toggle_sidebar(self):
        """Переключение видимости боковой панели."""
        logger.debug("Переключение видимости боковой панели")

        # Делегирование компоненту
        self.sidebar.toggle_visibility()

    def _toggle_theme(self):
        """Переключение темы оформления."""
        logger.debug("Переключение темы")

        # Переключение темы через ThemeManager
        # ThemeManager.toggle() вызывает _on_theme_changed через register
        ThemeManager.toggle()

    # ==================== Zoom Functions ====================

    def _reset_zoom(self):
        """Сброс масштаба графика."""
        logger.debug("Сброс масштаба графика")

        # Делегирование PlotArea
        self.plot_area.reset_zoom()

    def _zoom_in(self):
        """Увеличение масштаба графика."""
        logger.debug("Увеличение масштаба")

        # Делегирование PlotArea
        self.plot_area.zoom_in()

    def _zoom_out(self):
        """Уменьшение масштаба графика."""
        logger.debug("Уменьшение масштаба")

        # Делегирование PlotArea
        self.plot_area.zoom_out()
