from __future__ import annotations

from typing import Dict
from typing import List

from visualize_app.models import ExperimentalData
from visualize_app.services.solubility_engine import SolubilityResult
from visualize_app.utils.pressure_units import convert_pressure_series
from visualize_app.utils.pressure_units import normalize_pressure_unit
from visualize_app.utils.setup_config import SetupConfig

from .schemas import PlotSettingsPayload

PALETTE = [
    "#3b82f6",
    "#f97316",
    "#14b8a6",
    "#f43f5e",
    "#8b5cf6",
    "#eab308",
    "#06b6d4",
    "#84cc16",
]


def build_setup(payload) -> SetupConfig:
    return SetupConfig(
        name=payload.name,
        pressure_unit=payload.pressure_unit,
        pressure_coefficient=payload.pressure_coefficient,
        vessel_volume=payload.vessel_volume_ml,
        water_volume=payload.water_volume_ml,
        time_column=payload.time_column,
        data_columns=[column.model_dump() for column in payload.data_columns],
    )


def convert_pressure_for_display(
    data: ExperimentalData,
    setup: SetupConfig,
    settings: PlotSettingsPayload,
) -> ExperimentalData:
    pressure_columns = []
    for column in data.series.keys():
        low = column.strip().lower()
        configured_unit = _get_pressure_source_unit(column, data, setup)
        if low in {"давление", "pressure"} or configured_unit:
            pressure_columns.append(column)

    if not pressure_columns:
        return data

    coefficient = float(getattr(setup, "pressure_coefficient", 1.0) or 1.0)
    target_setting = settings.pressure_display_unit
    target_unit = normalize_pressure_unit(target_setting) if target_setting != "setup" else ""

    converted_series = {name: list(values) for name, values in data.series.items()}
    converted_units = data.units.copy()

    for column in pressure_columns:
        source_unit = _get_pressure_source_unit(column, data, setup)
        raw_series = list(data.series[column])
        if coefficient != 1.0:
            raw_series = [float(value) * coefficient for value in raw_series]

        if target_setting == "setup" or not target_unit or not source_unit:
            converted_series[column] = raw_series
            if source_unit:
                converted_units[column] = source_unit
            continue

        converted_series[column] = convert_pressure_series(raw_series, source_unit, target_unit)
        converted_units[column] = target_unit

    return ExperimentalData(
        hours=list(data.hours),
        series=converted_series,
        units=converted_units,
        metadata=data.metadata.copy(),
    )


def downsample_data(data: ExperimentalData, factor: int) -> ExperimentalData:
    factor = max(1, int(factor))
    if factor == 1:
        return data

    indices = list(range(0, len(data.hours), factor))
    if indices[-1] != len(data.hours) - 1:
        indices.append(len(data.hours) - 1)

    return ExperimentalData(
        hours=[data.hours[index] for index in indices],
        series={name: [values[index] for index in indices] for name, values in data.series.items()},
        units=data.units.copy(),
        metadata=data.metadata.copy(),
    )


def build_data_charts(
    data: ExperimentalData,
    settings: PlotSettingsPayload,
) -> List[Dict]:
    charts = []
    x_values = list(data.hours)

    for index, (column, values) in enumerate(data.series.items()):
        unit = data.units.get(column, "").strip()
        color = PALETTE[index % len(PALETTE)]
        label = f"{column} ({unit})" if unit else column
        charts.append(
            {
                "id": column,
                "title": column,
                "description": "Временной ряд с интерактивным масштабированием и панорамированием.",
                "traces": [
                    {
                        "type": "scattergl",
                        "mode": "lines+markers" if settings.show_markers else "lines",
                        "name": column,
                        "x": x_values,
                        "y": list(values),
                        "line": {"width": settings.line_width, "color": color},
                        "opacity": settings.line_alpha,
                        "marker": {"size": settings.marker_size, "color": color},
                        "hovertemplate": f"<b>{column}</b><br>Время: %{{x:.3f}} ч<br>Значение: %{{y:.5g}}<extra></extra>",
                    }
                ],
                "layout": _base_layout(
                    title=column,
                    yaxis_title=label,
                    show_grid=settings.show_grid,
                    grid_alpha=settings.grid_alpha,
                ),
            }
        )

    return charts


def build_solubility_charts(result: SolubilityResult) -> List[Dict]:
    time_values = result.time_hours.tolist()
    injection_times = [float(result.time_hours[index]) for index in result.injection_indices]
    vlines = [
        {
            "type": "line",
            "xref": "x",
            "yref": "paper",
            "x0": x_value,
            "x1": x_value,
            "y0": 0,
            "y1": 1,
            "line": {"color": "rgba(248, 113, 113, 0.55)", "width": 1.5, "dash": "dot"},
        }
        for x_value in injection_times
    ]

    pressure_chart = {
        "id": "pressure",
        "title": "Давление",
        "description": "Давление во времени с отметками подкачек газа.",
        "traces": [
            {
                "type": "scattergl",
                "mode": "lines",
                "name": "Давление",
                "x": time_values,
                "y": result.pressure_bar.tolist(),
                "line": {"width": 2.5, "color": "#3b82f6"},
                "hovertemplate": "<b>Давление</b><br>Время: %{x:.3f} ч<br>%{y:.4f} бар<extra></extra>",
            },
            {
                "type": "scattergl",
                "mode": "markers",
                "name": "Подкачка газа",
                "x": [float(result.time_hours[i]) for i in result.injection_indices],
                "y": [float(result.pressure_bar[i]) for i in result.injection_indices],
                "marker": {
                    "color": "#ef4444",
                    "size": 11,
                    "symbol": "triangle-up",
                    "line": {"width": 1.5, "color": "#7f1d1d"},
                },
                "hovertemplate": "<b>Подкачка</b><br>Время: %{x:.3f} ч<br>%{y:.4f} бар<extra></extra>",
            },
        ],
        "layout": _base_layout(
            title="Изменение давления во времени",
            yaxis_title="Давление (бар)",
            shapes=vlines,
        ),
    }

    accumulation_chart = {
        "id": "accumulation",
        "title": "Накопление CO₂",
        "description": "Суммарное количество CO₂ в системе с учетом подкачек.",
        "traces": [
            {
                "type": "scattergl",
                "mode": "lines",
                "name": "Всего CO₂ в системе",
                "x": time_values,
                "y": result.total_mol.tolist(),
                "line": {"width": 2.5, "color": "#0f172a"},
                "fill": "tozeroy",
                "fillcolor": "rgba(59, 130, 246, 0.16)",
                "hovertemplate": "<b>CO₂</b><br>Время: %{x:.3f} ч<br>%{y:.5f} моль<extra></extra>",
            }
        ],
        "layout": _base_layout(
            title="Накопление CO₂ в системе",
            yaxis_title="Всего CO₂ (моль)",
            shapes=vlines,
        ),
    }

    saturation_chart = {
        "id": "saturation",
        "title": "Насыщение",
        "description": "Степень насыщения раствора относительно предела растворимости.",
        "traces": [
            {
                "type": "scattergl",
                "mode": "lines",
                "name": "Степень насыщения",
                "x": time_values,
                "y": result.saturation_pct.tolist(),
                "line": {"width": 2.5, "color": "#06b6d4"},
                "fill": "tozeroy",
                "fillcolor": "rgba(34, 211, 238, 0.18)",
                "hovertemplate": "<b>Насыщение</b><br>Время: %{x:.3f} ч<br>%{y:.3f}%<extra></extra>",
            },
            {
                "type": "scatter",
                "mode": "lines",
                "name": "100% насыщение",
                "x": time_values,
                "y": [100.0] * len(time_values),
                "line": {"width": 2, "color": "#16a34a", "dash": "dash"},
                "hoverinfo": "skip",
            },
        ],
        "layout": _base_layout(
            title="Степень насыщения раствора",
            yaxis_title="Насыщение (%)",
            yaxis_range=[0, 110],
            shapes=vlines,
        ),
    }

    return [pressure_chart, accumulation_chart, saturation_chart]


def preview_rows(data: ExperimentalData, limit: int = 10) -> List[Dict[str, float]]:
    rows = []
    for index in range(min(limit, len(data.hours))):
        row = {"Часы": float(data.hours[index])}
        for name, values in data.series.items():
            row[name] = float(values[index])
        rows.append(row)
    return rows


def result_summary(result: SolubilityResult) -> Dict[str, str]:
    return {
        "injection_count": str(len(result.injection_indices)),
        "pressure_min_bar": f"{float(result.pressure_bar.min()):.4f}",
        "pressure_max_bar": f"{float(result.pressure_bar.max()):.4f}",
        "saturation_peak_pct": f"{float(result.saturation_pct.max()):.2f}",
        "total_co2_final_mol": f"{float(result.total_mol[-1]):.6f}",
    }


def _base_layout(
    title: str,
    yaxis_title: str,
    show_grid: bool = True,
    grid_alpha: float = 0.24,
    shapes: List[Dict] | None = None,
    yaxis_range: List[float] | None = None,
) -> Dict:
    return {
        "title": {"text": title, "x": 0.03, "font": {"size": 20, "color": "#e5eefc"}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "#081120",
        "font": {"family": "Manrope, sans-serif", "color": "#bfd3f2"},
        "hovermode": "x unified",
        "dragmode": "pan",
        "margin": {"l": 70, "r": 28, "t": 56, "b": 56},
        "xaxis": {
            "title": "Время (ч)",
            "showgrid": show_grid,
            "gridcolor": f"rgba(148, 163, 184, {grid_alpha})",
            "zeroline": False,
            "showspikes": True,
            "spikemode": "across",
            "spikecolor": "rgba(191, 219, 254, 0.45)",
            "color": "#d6e4ff",
        },
        "yaxis": {
            "title": yaxis_title,
            "showgrid": show_grid,
            "gridcolor": f"rgba(148, 163, 184, {grid_alpha})",
            "zeroline": False,
            "color": "#d6e4ff",
            "range": yaxis_range,
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(2, 6, 23, 0.35)",
        },
        "shapes": shapes or [],
    }


def _get_pressure_source_unit(column: str, data: ExperimentalData, setup: SetupConfig) -> str:
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
        return ""

    return normalize_pressure_unit(setup.pressure_unit)
