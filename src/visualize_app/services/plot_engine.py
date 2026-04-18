"""
Advanced plotting engine for experimental data visualization.
"""

import logging
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from visualize_app.models import ExperimentalData
from visualize_app.models import PlotSettings

logger = logging.getLogger(__name__)

# Set style
sns.set_style("whitegrid")
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


class PlotEngine:
    """Advanced plotting engine with multiple visualization types."""

    # Color palette for consistent styling
    COLOR_PALETTE = sns.color_palette("husl", 8)

    def __init__(self, settings: Optional[PlotSettings] = None):
        """Initialize plot engine with optional settings."""
        self.current_figure: Optional[Figure] = None
        self.settings = settings or PlotSettings()
        self.dark_mode = False

    def set_dark_mode(self, enabled: bool):
        """Set dark mode for plots."""
        self.dark_mode = enabled

    def _apply_theme(self, fig, ax):
        """Apply current theme colors to figure and axes."""
        if self.dark_mode:
            bg_color = "#1e293b"
            text_color = "#f1f5f9"
            grid_color = "#475569"
        else:
            bg_color = "#ffffff"
            text_color = "#1e293b"
            grid_color = "#e2e8f0"

        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)

        for spine in ax.spines.values():
            spine.set_color(grid_color)

        if ax.legend_:
            ax.legend_.get_frame().set_facecolor(bg_color)
            ax.legend_.get_frame().set_edgecolor(grid_color)
            for text in ax.legend_.get_texts():
                text.set_color(text_color)

    def create_time_series_plot(
        self,
        data: ExperimentalData,
        y_columns: List[str],
        title: str = "Временной ряд",
        ylabel: str = "Значение",
        figsize: tuple = (12, 6),
        settings: Optional[PlotSettings] = None,
    ) -> Figure:
        """
        Create time series plot.

        Args:
            data: Experimental data object
            y_columns: List of column names to plot
            title: Plot title
            ylabel: Y-axis label
            figsize: Figure size
            settings: Optional plot settings (uses engine settings if not provided)

        Returns:
            Matplotlib Figure object
        """
        try:
            s = settings or self.settings
            fig, ax = plt.subplots(figsize=figsize, dpi=100)

            df = data.to_dataframe()

            # Plot each column
            for idx, col in enumerate(y_columns):
                if col in df.columns and col != "Часы":
                    color = self.COLOR_PALETTE[idx % len(self.COLOR_PALETTE)]
                    plot_kwargs = {
                        "label": col,
                        "linewidth": s.line_width,
                        "color": color,
                        "alpha": s.line_alpha,
                    }
                    if s.show_markers:
                        plot_kwargs["marker"] = s.marker_style
                        plot_kwargs["markersize"] = s.marker_size
                    ax.plot(df["Часы"], df[col], **plot_kwargs)

            # Formatting
            ax.set_xlabel("Часы", fontsize=11, fontweight="bold")
            ax.set_ylabel(ylabel, fontsize=11, fontweight="bold")
            ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

            if s.show_grid:
                ax.grid(True, alpha=s.grid_alpha, linestyle="--")

            ax.legend(loc="best", framealpha=0.9, fontsize=9)

            # Apply theme
            self._apply_theme(fig, ax)

            # Tight layout
            fig.tight_layout()

            self.current_figure = fig
            logger.info(f"Created time series plot: {title}")

            return fig

        except Exception as e:
            logger.error(f"Error creating time series plot: {e}", exc_info=True)
            raise

    def create_scatter_plot(
        self,
        data: ExperimentalData,
        x_column: str,
        y_column: str,
        title: str = "Диаграмма рассеяния",
        xlabel: str = "X",
        ylabel: str = "Y",
        figsize: tuple = (10, 6),
    ) -> Figure:
        """
        Create scatter plot.

        Args:
            data: Experimental data object
            x_column: Column name for x-axis
            y_column: Column name for y-axis
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            figsize: Figure size

        Returns:
            Matplotlib Figure object
        """
        try:
            fig, ax = plt.subplots(figsize=figsize, dpi=100)

            df = data.to_dataframe()

            # Create scatter plot
            ax.scatter(
                df[x_column],
                df[y_column],
                alpha=0.6,
                s=50,
                color=self.COLOR_PALETTE[0],
                edgecolors="black",
                linewidths=0.5,
            )

            # Formatting
            ax.set_xlabel(xlabel, fontsize=11, fontweight="bold")
            ax.set_ylabel(ylabel, fontsize=11, fontweight="bold")
            ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

            ax.grid(True, alpha=0.3, linestyle="--")

            # Apply theme
            self._apply_theme(fig, ax)

            fig.tight_layout()

            self.current_figure = fig
            logger.info(f"Created scatter plot: {title}")

            return fig

        except Exception as e:
            logger.error(f"Error creating scatter plot: {e}", exc_info=True)
            raise

    def create_multi_plot(
        self,
        data: ExperimentalData,
        plot_configs: List[Dict],
        figsize: tuple = (14, 10),
        settings: Optional[PlotSettings] = None,
    ) -> Figure:
        """
        Create multiple subplots based on configurations.

        Args:
            data: Experimental data object
            plot_configs: List of plot configuration dictionaries
            figsize: Figure size
            settings: Optional plot settings (uses engine settings if not provided)

        Returns:
            Matplotlib Figure object
        """
        try:
            s = settings or self.settings
            n_plots = len(plot_configs)
            if n_plots == 0:
                raise ValueError("No plot configurations provided")

            # Calculate subplot layout
            if n_plots == 1:
                rows, cols = 1, 1
            elif n_plots == 2:
                rows, cols = 1, 2
            elif n_plots <= 4:
                rows, cols = 2, 2
            elif n_plots <= 6:
                rows, cols = 2, 3
            else:
                rows, cols = 3, 3

            fig, axes = plt.subplots(rows, cols, figsize=figsize, dpi=100)

            # Flatten axes for easier iteration
            if n_plots == 1:
                axes = [axes]
            else:
                axes = axes.flatten()

            df = data.to_dataframe()

            for idx, config in enumerate(plot_configs):
                if idx >= len(axes):
                    break

                ax = axes[idx]
                plot_type = config.get("type", "time_series")

                if plot_type == "time_series":
                    y_columns = config.get("y", [])
                    for col_idx, col in enumerate(y_columns):
                        if col in df.columns:
                            color = self.COLOR_PALETTE[col_idx % len(self.COLOR_PALETTE)]
                            plot_kwargs = {
                                "label": col,
                                "linewidth": s.line_width,
                                "color": color,
                                "alpha": s.line_alpha,
                            }
                            if s.show_markers:
                                plot_kwargs["marker"] = s.marker_style
                                plot_kwargs["markersize"] = s.marker_size
                            ax.plot(df["Часы"], df[col], **plot_kwargs)

                elif plot_type == "scatter":
                    x_col = config.get("x")
                    y_col = config.get("y")
                    if x_col in df.columns and y_col in df.columns:
                        ax.scatter(
                            df[x_col],
                            df[y_col],
                            alpha=s.line_alpha,
                            s=30,
                            color=self.COLOR_PALETTE[0],
                        )
                        ax.set_xlabel(config.get("xlabel", x_col), fontsize=9)

                # Common formatting
                ax.set_title(config.get("title", ""), fontsize=10, fontweight="bold")
                ax.set_ylabel(config.get("ylabel", ""), fontsize=9)

                if s.show_grid:
                    ax.grid(True, alpha=s.grid_alpha, linestyle="--")

                if plot_type == "time_series":
                    ax.legend(loc="best", fontsize=7)

                # Apply theme to each subplot
                self._apply_theme(fig, ax)

            # Hide unused subplots
            for idx in range(n_plots, len(axes)):
                axes[idx].set_visible(False)

            fig.tight_layout()

            self.current_figure = fig
            logger.info(f"Created multi-plot with {n_plots} subplots")

            return fig

        except Exception as e:
            logger.error(f"Error creating multi-plot: {e}", exc_info=True)
            raise

    def save_figure(self, filepath: Path, dpi: int = 300):
        """
        Save current figure to file.

        Args:
            filepath: Path to save the figure
            dpi: Resolution in dots per inch
        """
        if self.current_figure is None:
            raise ValueError("No figure to save")

        try:
            self.current_figure.savefig(
                filepath,
                dpi=dpi,
                bbox_inches="tight",
                facecolor=self.current_figure.get_facecolor(),
            )
            logger.info(f"Figure saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving figure: {e}", exc_info=True)
            raise

    @staticmethod
    def close_all():
        """Close all matplotlib figures."""
        plt.close("all")
