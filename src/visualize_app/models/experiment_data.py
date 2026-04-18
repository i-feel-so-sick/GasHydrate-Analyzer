"""
Data models for experimental data handling.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List

import pandas as pd


@dataclass
class ExperimentalData:
    """Model for storing experimental measurement data."""

    hours: List[float]
    series: Dict[str, List[float]]
    units: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate data integrity."""
        lengths = [len(self.hours)]
        for values in self.series.values():
            lengths.append(len(values))

        if len(set(lengths)) != 1:
            raise ValueError("All data arrays must have the same length")

    def to_dataframe(self) -> pd.DataFrame:
        """Convert experimental data to pandas DataFrame."""
        data = {"Часы": self.hours}
        data.update(self.series)
        return pd.DataFrame(data)

    @property
    def size(self) -> int:
        """Return the number of data points."""
        return len(self.hours)

    def get_column_names(self) -> List[str]:
        """Get list of available data columns."""
        return ["Часы", *self.series.keys()]

    def get_series(self, name: str) -> List[float]:
        """Get series values by column name."""
        return self.series.get(name, [])


@dataclass
class PlotSettings:
    """Model for plot visual settings."""

    # Line settings
    line_width: float = 2.0
    line_alpha: float = 0.8

    # Marker settings
    show_markers: bool = False
    marker_size: float = 3.0
    marker_style: str = "o"  # o, s, ^, D, v, <, >, p, *

    # Grid settings
    show_grid: bool = True
    grid_alpha: float = 0.3

    # Figure settings
    figure_size: tuple = (12, 6)

    # Export settings
    export_dpi: int = 300

    # Units settings
    pressure_display_unit: str = "setup"  # setup, кПа, МПа, бар, атм

    # Available marker styles with labels
    MARKER_STYLES: Dict[str, str] = field(
        default_factory=lambda: {
            "o": "● Круг",
            "s": "■ Квадрат",
            "^": "▲ Треугольник",
            "D": "◆ Ромб",
            "v": "▼ Треугольник вниз",
            "*": "★ Звезда",
            "p": "⬠ Пятиугольник",
            "h": "⬡ Шестиугольник",
        }
    )

    # Available DPI options
    DPI_OPTIONS: List[int] = field(default_factory=lambda: [72, 150, 300, 600])

    def to_dict(self) -> Dict:
        """Convert settings to dictionary for serialization."""
        return {
            "line_width": self.line_width,
            "line_alpha": self.line_alpha,
            "show_markers": self.show_markers,
            "marker_size": self.marker_size,
            "marker_style": self.marker_style,
            "show_grid": self.show_grid,
            "grid_alpha": self.grid_alpha,
            "figure_size": self.figure_size,
            "export_dpi": self.export_dpi,
            "pressure_display_unit": self.pressure_display_unit,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PlotSettings":
        """Create settings from dictionary."""
        return cls(
            line_width=data.get("line_width", 2.0),
            line_alpha=data.get("line_alpha", 0.8),
            show_markers=data.get("show_markers", False),
            marker_size=data.get("marker_size", 3.0),
            marker_style=data.get("marker_style", "o"),
            show_grid=data.get("show_grid", True),
            grid_alpha=data.get("grid_alpha", 0.3),
            figure_size=data.get("figure_size", (12, 6)),
            export_dpi=data.get("export_dpi", 300),
            pressure_display_unit=data.get("pressure_display_unit", "setup"),
        )


@dataclass
class ExperimentSetup:
    """Configuration for an experimental setup."""

    id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentMethod:
    """Configuration for an experimental method."""

    id: str
    name: str
    description: str
    plot_configs: List[Dict[str, Any]] = field(default_factory=list)
