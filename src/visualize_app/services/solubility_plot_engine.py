"""
Графики растворимости CO2.

Три отдельных графика, как в блокноте solubility.ipynb:
  1. Изменение давления во времени (с отметками подкачек)
  2. Накопление CO2 в системе (с учётом подкачек)
  3. Степень насыщения раствора

Каждая функция возвращает matplotlib Figure, готовую для встраивания
в CustomTkinter через FigureCanvasTkAgg.
"""

from __future__ import annotations

import logging
from typing import Optional

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

from visualize_app.models import PlotSettings
from visualize_app.services.solubility_engine import SolubilityResult

logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


def _set_xlim(ax, time):
    """Зафиксировать ось X от начала данных без пустых отступов."""
    t0 = float(time.min())
    t1 = float(time.max())
    margin = (t1 - t0) * 0.01
    ax.set_xlim([t0 - margin, t1 + margin])


def create_pressure_plot(
    result: SolubilityResult,
    settings: Optional[PlotSettings] = None,
) -> Figure:
    """
    График 1: Изменение давления во времени.
    Красные треугольники — события подкачки газа.
    Красные пунктирные вертикали — моменты подкачек.
    """
    s = settings or PlotSettings()
    fig, ax = plt.subplots(figsize=(14, 5), dpi=100)

    time = result.time_hours

    ax.plot(
        time,
        result.pressure_bar,
        "b-o",
        linewidth=s.line_width,
        markersize=3,
        alpha=s.line_alpha,
        label="Давление",
    )

    if result.injection_indices:
        idx = result.injection_indices
        ax.scatter(
            time[idx],
            result.pressure_bar[idx],
            color="red",
            s=150,
            marker="^",
            zorder=5,
            label="Подкачка газа",
            edgecolors="darkred",
            linewidths=2,
        )
        for i in idx:
            ax.axvline(x=time[i], color="red", linestyle=":", linewidth=2, alpha=0.5)

    ax.set_xlabel("Время (ч)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Давление (бар)", fontsize=13, fontweight="bold")
    ax.set_title("Изменение давления во времени", fontsize=14, fontweight="bold", pad=15)
    if s.show_grid:
        ax.grid(True, alpha=s.grid_alpha, linestyle="--")
    ax.legend(fontsize=11, loc="best")
    _set_xlim(ax, time)

    fig.tight_layout()
    return fig


def create_accumulation_plot(
    result: SolubilityResult,
    settings: Optional[PlotSettings] = None,
) -> Figure:
    """
    График 2: Накопление CO2 в системе с учётом подкачек.
    Синяя линия + заливка — всего CO2 в системе.
    Вертикальные пунктиры — моменты подкачек.
    """
    s = settings or PlotSettings()
    fig, ax = plt.subplots(figsize=(14, 5), dpi=100)

    time = result.time_hours

    ax.plot(
        time,
        result.total_mol,
        color="darkblue",
        linewidth=2.5,
        marker="o",
        markersize=3,
        label="Всего CO₂ в системе",
    )
    ax.fill_between(time, 0, result.total_mol, alpha=0.2, color="blue")

    if result.injection_indices:
        for i in result.injection_indices:
            ax.axvline(x=time[i], color="red", linestyle=":", linewidth=2, alpha=0.5)

    ax.set_xlabel("Время (ч)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Всего CO₂ (моль)", fontsize=13, fontweight="bold")
    ax.set_title(
        "Накопление CO₂ в системе (с учетом подкачек)", fontsize=14, fontweight="bold", pad=15
    )
    if s.show_grid:
        ax.grid(True, alpha=s.grid_alpha, linestyle="--")
    ax.legend(fontsize=11, loc="best")
    _set_xlim(ax, time)
    ax.set_ylim(bottom=0)

    fig.tight_layout()
    return fig


def create_saturation_plot(
    result: SolubilityResult,
    settings: Optional[PlotSettings] = None,
) -> Figure:
    """
    График 3: Степень насыщения раствора (%).
    Зелёная пунктирная горизонталь — предел 100%.
    """
    s = settings or PlotSettings()
    fig, ax = plt.subplots(figsize=(14, 5), dpi=100)

    time = result.time_hours

    ax.plot(
        time,
        result.saturation_pct,
        "c-o",
        linewidth=2.5,
        markersize=3,
        label="Степень насыщения",
    )
    ax.axhline(
        y=100, color="green", linestyle="--", linewidth=2.5, alpha=0.8, label="100% насыщение"
    )
    ax.fill_between(time, 0, result.saturation_pct, alpha=0.2, color="cyan")

    if result.injection_indices:
        for i in result.injection_indices:
            ax.axvline(x=time[i], color="red", linestyle=":", linewidth=2, alpha=0.5)

    ax.set_xlabel("Время (ч)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Степень насыщения (%)", fontsize=13, fontweight="bold")
    ax.set_title("Степень насыщения раствора", fontsize=14, fontweight="bold", pad=15)
    if s.show_grid:
        ax.grid(True, alpha=s.grid_alpha, linestyle="--")
    ax.set_ylim(0, 110)
    ax.legend(fontsize=11, loc="best")
    _set_xlim(ax, time)

    fig.tight_layout()
    return fig


__all__ = [
    "create_pressure_plot",
    "create_accumulation_plot",
    "create_saturation_plot",
]
