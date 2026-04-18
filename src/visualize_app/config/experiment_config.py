"""
Configuration for experimental setups and methods.
"""

from typing import Dict
from typing import List

from visualize_app.models import ExperimentMethod
from visualize_app.models import ExperimentSetup


class ExperimentConfig:
    """Central configuration for experimental setups and methods."""

    # Experimental setups configuration
    SETUPS: Dict[str, ExperimentSetup] = {
        "setup_1": ExperimentSetup(
            id="setup_1",
            name="Установка №1 - Теплообменник типа А",
            description="Экспериментальная установка для исследования теплообмена в горизонтальном теплообменнике",
            parameters={
                "type": "heat_exchanger_a",
                "volume": 10.0,  # литры
                "pressure_range": (0, 300),  # кПа
                "temp_range": (-20, 100),  # °C
            },
        ),
        "setup_2": ExperimentSetup(
            id="setup_2",
            name="Установка №2 - Вертикальный реактор",
            description="Установка для исследования процессов конденсации в вертикальном реакторе",
            parameters={
                "type": "vertical_reactor",
                "volume": 25.0,
                "pressure_range": (0, 500),
                "temp_range": (0, 150),
            },
        ),
        "setup_3": ExperimentSetup(
            id="setup_3",
            name="Установка №3 - Криогенная система",
            description="Установка для экспериментов при низких температурах",
            parameters={
                "type": "cryogenic",
                "volume": 5.0,
                "pressure_range": (0, 200),
                "temp_range": (-100, 50),
            },
        ),
    }

    # Experimental methods configuration
    METHODS: Dict[str, ExperimentMethod] = {
        "method_1": ExperimentMethod(
            id="method_1",
            name="Метод 1 - Изотермический процесс",
            description="Исследование при постоянной температуре",
            plot_configs=[
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": ["Давление"],
                    "title": "Изменение давления во времени",
                    "ylabel": "Давление, кПа",
                    "grid": True,
                },
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": ["ТемператураГаза", "ТемператураЖидкости"],
                    "title": "Температурные профили",
                    "ylabel": "Температура, °C",
                    "grid": True,
                },
            ],
        ),
        "method_2": ExperimentMethod(
            id="method_2",
            name="Метод 2 - Изобарический процесс",
            description="Исследование при постоянном давлении",
            plot_configs=[
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": ["ТемператураГаза", "ТемператураЖидкости", "ТемператураВКоробе"],
                    "title": "Температурные изменения",
                    "ylabel": "Температура, °C",
                    "grid": True,
                },
                {
                    "type": "scatter",
                    "x": "ТемператураГаза",
                    "y": "Давление",
                    "title": "Зависимость давления от температуры газа",
                    "xlabel": "Температура газа, °C",
                    "ylabel": "Давление, кПа",
                },
            ],
        ),
        "method_3": ExperimentMethod(
            id="method_3",
            name="Метод 3 - Полный мониторинг",
            description="Комплексный анализ всех параметров",
            plot_configs=[
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": [
                        "ТемператураГаза",
                        "ТемператураЖидкости",
                        "ТемператураВКоробе",
                        "ТемператураВКомнате",
                    ],
                    "title": "Все температурные датчики",
                    "ylabel": "Температура, °C",
                    "grid": True,
                },
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": ["Давление"],
                    "title": "Давление в системе",
                    "ylabel": "Давление, кПа",
                    "grid": True,
                },
                {
                    "type": "scatter",
                    "x": "ТемператураГаза",
                    "y": "ТемператураЖидкости",
                    "title": "Корреляция температур газ-жидкость",
                    "xlabel": "Температура газа, °C",
                    "ylabel": "Температура жидкости, °C",
                },
            ],
        ),
        "method_4": ExperimentMethod(
            id="method_4",
            name="Метод 4 - Анализ градиентов",
            description="Исследование температурных градиентов",
            plot_configs=[
                {
                    "type": "time_series",
                    "x": "Часы",
                    "y": ["ТемператураГаза", "ТемператураЖидкости"],
                    "title": "Температуры рабочих сред",
                    "ylabel": "Температура, °C",
                    "grid": True,
                },
                {
                    "type": "scatter",
                    "x": "ТемператураВКоробе",
                    "y": "ТемператураВКомнате",
                    "title": "Соотношение температур окружающей среды",
                    "xlabel": "Температура в коробе, °C",
                    "ylabel": "Температура в комнате, °C",
                },
            ],
        ),
    }

    @classmethod
    def get_setup(cls, setup_id: str) -> ExperimentSetup:
        """Get setup configuration by ID."""
        return cls.SETUPS.get(setup_id)

    @classmethod
    def get_method(cls, method_id: str) -> ExperimentMethod:
        """Get method configuration by ID."""
        return cls.METHODS.get(method_id)

    @classmethod
    def get_all_setups(cls) -> List[ExperimentSetup]:
        """Get all available setups."""
        return list(cls.SETUPS.values())

    @classmethod
    def get_all_methods(cls) -> List[ExperimentMethod]:
        """Get all available methods."""
        return list(cls.METHODS.values())

    @classmethod
    def get_setup_names(cls) -> Dict[str, str]:
        """Get mapping of setup IDs to names."""
        return {sid: setup.name for sid, setup in cls.SETUPS.items()}

    @classmethod
    def get_method_names(cls) -> Dict[str, str]:
        """Get mapping of method IDs to names."""
        return {mid: method.name for mid, method in cls.METHODS.items()}
