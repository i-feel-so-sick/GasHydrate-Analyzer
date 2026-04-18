"""
Setup configuration manager for storing and loading equipment parameters.
Supports multiple user-defined configurations with PyInstaller compatibility.
"""

import json
import logging
import sys
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

logger = logging.getLogger(__name__)

# Default parsing configuration
DEFAULT_TIME_COLUMN = "Время"
DEFAULT_DATA_COLUMNS = [
    {"column": "Давление", "unit": "кПа", "required": True},
    {"column": "ТемператураГаза", "unit": "°C", "required": True},
    {"column": "ТемператураЖидкости", "unit": "°C", "required": True},
    {"column": "ТемператураВКоробе", "unit": "°C", "required": True},
    {"column": "ТемператураВКомнате", "unit": "°C", "required": True},
]


def get_default_data_columns() -> List[Dict[str, Any]]:
    """Return default data columns list."""
    return [dict(item) for item in DEFAULT_DATA_COLUMNS]


def normalize_time_column(value: Optional[str]) -> str:
    """Normalize time column name."""
    if value is None:
        return DEFAULT_TIME_COLUMN
    name = str(value).strip()
    return name


def normalize_data_columns(columns: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalize data columns list."""
    if columns is None:
        return []

    normalized: List[Dict[str, Any]] = []
    for item in columns:
        if not isinstance(item, dict):
            continue
        column = str(item.get("column", "")).strip()
        unit = str(item.get("unit", "")).strip()
        required = bool(item.get("required", True))
        if not column:
            continue
        normalized.append({"column": column, "unit": unit, "required": required})

    return normalized


def parsing_schema_to_columns(
    schema: Optional[Dict[str, Dict[str, Any]]],
) -> tuple[str, List[Dict[str, Any]]]:
    """Convert legacy parsing schema to time column and data columns list."""
    if not schema:
        return DEFAULT_TIME_COLUMN, get_default_data_columns()

    time_column = normalize_time_column(schema.get("time", {}).get("column"))
    data_columns: List[Dict[str, Any]] = []
    for key, cfg in schema.items():
        if key == "time":
            continue
        column = str(cfg.get("column", "")).strip()
        if not column:
            continue
        unit = str(cfg.get("unit", "")).strip()
        required = bool(cfg.get("required", True))
        data_columns.append({"column": column, "unit": unit, "required": required})

    if not data_columns:
        data_columns = get_default_data_columns()

    return time_column, data_columns


def get_app_data_dir() -> Path:
    """
    Get application data directory.
    Works with both normal Python and PyInstaller frozen executables.
    """
    # For PyInstaller: use user's home directory for data persistence
    # This ensures data survives between app updates and works in all modes
    if sys.platform == "win32":
        # Windows: %APPDATA%/ThermoViz
        base = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/ThermoViz
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux: ~/.local/share/ThermoViz
        base = Path.home() / ".local" / "share"

    app_dir = base / "ThermoViz"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


@dataclass
class SetupConfig:
    """Single experimental setup configuration."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    pressure_unit: str = "кПа"  # кПа, МПа, бар, атм
    pressure_coefficient: float = (
        1.0  # Коэффициент масштабирования давления (умножается на сырые значения)
    )
    vessel_volume: float = 0.0  # литры
    water_volume: float = 0.0  # литры
    parameters: Dict[str, Any] = field(default_factory=dict)
    time_column: str = field(default_factory=lambda: DEFAULT_TIME_COLUMN)
    data_columns: List[Dict[str, Any]] = field(default_factory=get_default_data_columns)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SetupConfig":
        """Create from dictionary."""
        if "parsing_schema" in data and ("time_column" not in data and "data_columns" not in data):
            time_column, data_columns = parsing_schema_to_columns(data.get("parsing_schema"))
        else:
            time_column = normalize_time_column(data.get("time_column"))
            data_columns = normalize_data_columns(data.get("data_columns"))

        if not data_columns:
            data_columns = get_default_data_columns()

        # Filter to only known fields to avoid TypeError on unexpected keys
        known_fields = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        filtered["time_column"] = time_column
        filtered["data_columns"] = data_columns
        return cls(**filtered)

    def is_configured(self) -> bool:
        """Check if setup has valid configuration."""
        return bool(self.name) and self.vessel_volume > 0 and self.water_volume > 0

    def get_gas_volume(self) -> float:
        """Calculate gas volume."""
        return max(0, self.vessel_volume - self.water_volume)


class SetupConfigManager:
    """
    Manager for multiple setup configurations with persistence.

    Stores configurations in user's app data directory for PyInstaller compatibility.
    """

    def __init__(self):
        """Initialize config manager."""
        self.config_dir = get_app_data_dir()
        self.config_file = self.config_dir / "setups.json"
        self._setups: Dict[str, SetupConfig] = {}
        self._current_setup_id: Optional[str] = None
        self._load()

    def _load(self):
        """Load configurations from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Load setups
                setups_data = data.get("setups", [])
                for setup_data in setups_data:
                    setup = SetupConfig.from_dict(setup_data)
                    self._setups[setup.id] = setup

                # Load current setup ID
                self._current_setup_id = data.get("current_setup_id")

                # Validate current setup exists
                if self._current_setup_id and self._current_setup_id not in self._setups:
                    self._current_setup_id = None

                logger.info(f"Loaded {len(self._setups)} setup configurations")

            except Exception as e:
                logger.warning(f"Failed to load setup configs: {e}")
                self._setups = {}
                self._current_setup_id = None
        else:
            logger.info("No saved configurations found")
            self._setups = {}
            self._current_setup_id = None

    def _save(self):
        """Save configurations to file."""
        try:
            data = {
                "setups": [setup.to_dict() for setup in self._setups.values()],
                "current_setup_id": self._current_setup_id,
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Setup configurations saved")
        except Exception as e:
            logger.error(f"Failed to save setup configs: {e}")

    def has_setups(self) -> bool:
        """Check if any setups are configured."""
        return len(self._setups) > 0

    def get_all_setups(self) -> List[SetupConfig]:
        """Get all configured setups."""
        return list(self._setups.values())

    def get_setup_names(self) -> List[str]:
        """Get list of setup names."""
        return [setup.name for setup in self._setups.values()]

    def get_setup_by_id(self, setup_id: str) -> Optional[SetupConfig]:
        """Get setup by ID."""
        return self._setups.get(setup_id)

    def get_setup_by_name(self, name: str) -> Optional[SetupConfig]:
        """Get setup by name."""
        for setup in self._setups.values():
            if setup.name == name:
                return setup
        return None

    def get_current_setup(self) -> Optional[SetupConfig]:
        """Get currently selected setup."""
        if self._current_setup_id:
            return self._setups.get(self._current_setup_id)
        return None

    def set_current_setup(self, setup_id: str):
        """Set current setup by ID."""
        if setup_id in self._setups:
            self._current_setup_id = setup_id
            self._save()
            logger.info(f"Current setup set to: {self._setups[setup_id].name}")

    def set_current_setup_by_name(self, name: str):
        """Set current setup by name."""
        setup = self.get_setup_by_name(name)
        if setup:
            self.set_current_setup(setup.id)

    def add_setup(self, setup: SetupConfig) -> str:
        """
        Add new setup configuration.

        Returns:
            The ID of the added setup.
        """
        # Ensure unique ID
        if not setup.id or setup.id in self._setups:
            setup.id = str(uuid.uuid4())[:8]

        self._setups[setup.id] = setup

        # Set as current if it's the first one
        if len(self._setups) == 1:
            self._current_setup_id = setup.id

        self._save()
        logger.info(f"Added setup: {setup.name} (ID: {setup.id})")
        return setup.id

    def update_setup(self, setup_id: str, **kwargs) -> bool:
        """
        Update existing setup configuration.

        Args:
            setup_id: ID of setup to update
            **kwargs: Fields to update

        Returns:
            True if update successful, False otherwise.
        """
        if setup_id not in self._setups:
            return False

        setup = self._setups[setup_id]
        for key, value in kwargs.items():
            if hasattr(setup, key):
                if key == "time_column":
                    value = normalize_time_column(value)
                if key == "data_columns":
                    value = normalize_data_columns(value)  # type: ignore[arg-type]
                setattr(setup, key, value)

        self._save()
        logger.info(f"Updated setup: {setup.name}")
        return True

    def delete_setup(self, setup_id: str) -> bool:
        """
        Delete setup configuration.

        Args:
            setup_id: ID of setup to delete

        Returns:
            True if deletion successful, False otherwise.
        """
        if setup_id not in self._setups:
            return False

        setup_name = self._setups[setup_id].name
        del self._setups[setup_id]

        # Update current setup if deleted
        if self._current_setup_id == setup_id:
            if self._setups:
                self._current_setup_id = list(self._setups.keys())[0]
            else:
                self._current_setup_id = None

        self._save()
        logger.info(f"Deleted setup: {setup_name}")
        return True

    def create_setup(
        self,
        name: str,
        description: str = "",
        pressure_unit: str = "кПа",
        vessel_volume: float = 0.0,
        water_volume: float = 0.0,
        time_column: Optional[str] = None,
        data_columns: Optional[List[Dict[str, Any]]] = None,
        **extra_params,
    ) -> SetupConfig:
        """
        Create and add a new setup configuration.

        Returns:
            The created SetupConfig object.
        """
        setup = SetupConfig(
            name=name,
            description=description,
            pressure_unit=pressure_unit,
            vessel_volume=vessel_volume,
            water_volume=water_volume,
            parameters=extra_params,
            time_column=normalize_time_column(time_column),
            data_columns=normalize_data_columns(data_columns),
        )
        self.add_setup(setup)
        return setup

    # Legacy compatibility methods
    def get_parameters(self) -> Optional[SetupConfig]:
        """
        Legacy method: Get current setup parameters.
        Returns current setup or None if no setups exist.
        """
        return self.get_current_setup()

    def is_configured(self) -> bool:
        """
        Legacy method: Check if current setup is configured.
        """
        current = self.get_current_setup()
        return current is not None and current.is_configured()
