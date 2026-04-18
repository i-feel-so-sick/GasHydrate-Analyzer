"""
Centralized application state management.
"""

import logging
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict
from typing import Optional
from typing import Tuple

from matplotlib.figure import Figure

from visualize_app.models import ExperimentalData
from visualize_app.models import PlotSettings

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """
    Centralized application state.

    This class holds all application state in one place,
    making it easier to manage and test.
    """

    # Data state
    current_data: Optional[ExperimentalData] = None
    current_file_path: Optional[Path] = None

    # Plot state
    plot_settings: PlotSettings = field(default_factory=PlotSettings)
    current_plot: str = ""
    figures: Dict[str, Figure] = field(default_factory=dict)
    plot_order: list[str] = field(default_factory=list)

    # UI state
    sidebar_visible: bool = True

    # Time filter state (start_time, end_time) in hours
    time_filter: Optional[Tuple[float, float]] = None

    # Display downsampling factor for loaded signal (1 = no downsampling)
    signal_downsample_factor: int = 1

    # Solubility analysis state
    solubility_figures: Dict[str, Figure] = field(default_factory=dict)
    sol_plot_order: list[str] = field(default_factory=list)
    current_sol_plot: str = ""

    @property
    def current_plot_id(self) -> str:
        """Alias for current_plot (backwards compatibility)."""
        return self.current_plot

    @current_plot_id.setter
    def current_plot_id(self, value: str):
        """Alias setter for current_plot (backwards compatibility)."""
        self.current_plot = value

    def has_data(self) -> bool:
        """Check if data is loaded."""
        return self.current_data is not None

    def clear_data(self):
        """Clear all data and reset state."""
        self.current_data = None
        self.current_file_path = None
        self.figures.clear()
        self.current_plot = ""
        self.plot_order = []
        self.time_filter = None
        self.signal_downsample_factor = 1
        self.solubility_figures.clear()
        self.sol_plot_order = []
        self.current_sol_plot = ""
        logger.info("Application state cleared")

    def load_data(self, data: ExperimentalData, file_path: Path):
        """Load new data."""
        self.current_data = data
        self.current_file_path = file_path
        logger.info(f"Data loaded: {file_path.name}")

    def set_plot_settings(self, settings: PlotSettings):
        """Update plot settings."""
        self.plot_settings = settings
        logger.info("Plot settings updated")

    def switch_plot(self, plot_id: str):
        """Switch current plot."""
        if plot_id != self.current_plot:
            self.current_plot = plot_id
            logger.info(f"Switched to plot: {plot_id}")
