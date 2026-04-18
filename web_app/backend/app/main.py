from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

import pandas as pd
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.middleware.cors import CORSMiddleware

from visualize_app.services.excel_parser import ExcelParser
from visualize_app.services.excel_parser import ExcelParserError
from visualize_app.services.solubility_engine import analyze_solubility
from visualize_app.utils.setup_config import DEFAULT_TIME_COLUMN
from visualize_app.utils.setup_config import get_default_data_columns
from visualize_app.utils.setup_config import normalize_data_columns
from visualize_app.utils.setup_config import normalize_time_column

from .plot_builders import build_data_charts
from .plot_builders import build_setup
from .plot_builders import build_solubility_charts
from .plot_builders import convert_pressure_for_display
from .plot_builders import downsample_data
from .plot_builders import preview_rows
from .plot_builders import result_summary
from .schemas import AnalysisResponse
from .schemas import DataColumnSchema
from .schemas import FileInspectionResponse
from .schemas import PlotSettingsPayload
from .schemas import SetupPayload

app = FastAPI(title="ThermoViz Web API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/defaults")
def defaults() -> Dict[str, Any]:
    return {
        "time_column": DEFAULT_TIME_COLUMN,
        "data_columns": get_default_data_columns(),
        "plot_settings": PlotSettingsPayload().model_dump(),
        "setup": SetupPayload(
            time_column=DEFAULT_TIME_COLUMN,
            data_columns=[DataColumnSchema(**item) for item in get_default_data_columns()],
        ).model_dump(),
    }


@app.post("/api/files/inspect", response_model=FileInspectionResponse)
async def inspect_file(file: UploadFile = File(...)) -> FileInspectionResponse:
    suffix = Path(file.filename or "dataset.xlsx").suffix or ".xlsx"
    temp_path = await _write_upload_to_temp(file, suffix)
    try:
        dataframe = pd.read_excel(temp_path, nrows=8)
        columns = [str(column) for column in dataframe.columns]
        preview = _sanitize_preview(dataframe.head(8).to_dict(orient="records"))
        suggested_time = _suggest_time_column(columns)
        suggested_columns = [
            DataColumnSchema(column=column, unit=_suggest_unit(column), required=True)
            for column in columns
            if column != suggested_time
        ]
        return FileInspectionResponse(
            filename=file.filename or temp_path.name,
            columns=columns,
            preview_rows=preview,
            suggested_time_column=suggested_time,
            suggested_data_columns=suggested_columns,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать файл: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_file(
    file: UploadFile = File(...),
    setup: str = Form(...),
    plot_settings: str = Form(...),
) -> AnalysisResponse:
    try:
        setup_payload = SetupPayload.model_validate_json(setup)
        plot_settings_payload = PlotSettingsPayload.model_validate_json(plot_settings)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Некорректные параметры: {exc}") from exc

    suffix = Path(file.filename or "dataset.xlsx").suffix or ".xlsx"
    temp_path = await _write_upload_to_temp(file, suffix)
    warnings: List[str] = []

    try:
        setup_obj = build_setup(setup_payload)
        experimental_data = ExcelParser.parse_file(
            temp_path,
            time_column=normalize_time_column(setup_obj.time_column),
            data_columns=normalize_data_columns(setup_obj.data_columns),
        )

        displayed_data = convert_pressure_for_display(
            experimental_data, setup_obj, plot_settings_payload
        )
        displayed_data = downsample_data(
            displayed_data, plot_settings_payload.signal_downsample_factor
        )

        vessel_volume_m3 = float(setup_payload.vessel_volume_ml or 150.0) / 1_000_000.0
        water_volume_m3 = float(setup_payload.water_volume_ml or 100.0) / 1_000_000.0
        water_mass_kg = water_volume_m3 * 1000.0

        solubility_result = analyze_solubility(
            experimental_data,
            V_total=vessel_volume_m3,
            V_water=water_volume_m3,
            m_water=water_mass_kg,
        )

        metadata = experimental_data.metadata.copy()
        metadata.update(result_summary(solubility_result))
        if plot_settings_payload.signal_downsample_factor > 1:
            warnings.append(
                f"Для отображения использовано прореживание x{plot_settings_payload.signal_downsample_factor}."
            )

        return AnalysisResponse(
            filename=file.filename or temp_path.name,
            metadata=metadata,
            columns=displayed_data.get_column_names(),
            units=displayed_data.units,
            row_count=displayed_data.size,
            time_range={
                "start": float(displayed_data.hours[0]),
                "end": float(displayed_data.hours[-1]),
            },
            setup=setup_payload,
            plot_settings=plot_settings_payload,
            data_charts=build_data_charts(displayed_data, plot_settings_payload),
            solubility_charts=build_solubility_charts(solubility_result),
            preview_rows=preview_rows(displayed_data),
            warnings=warnings,
        )
    except ExcelParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


async def _write_upload_to_temp(file: UploadFile, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        content = await file.read()
        handle.write(content)
        return Path(handle.name)


def _sanitize_preview(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clean_rows = []
    for row in rows:
        clean_row: Dict[str, Any] = {}
        for key, value in row.items():
            if pd.isna(value):
                clean_row[str(key)] = None
            elif hasattr(value, "isoformat"):
                clean_row[str(key)] = value.isoformat()
            else:
                clean_row[str(key)] = value
        clean_rows.append(clean_row)
    return clean_rows


def _suggest_time_column(columns: List[str]) -> str | None:
    candidates = ("время", "time", "timestamp", "дата")
    for column in columns:
        if any(token in column.strip().lower() for token in candidates):
            return column
    return columns[0] if columns else None


def _suggest_unit(column: str) -> str:
    lower = column.lower()
    if "давлен" in lower or "pressure" in lower:
        return "кПа"
    if "темпера" in lower or "temp" in lower:
        return "°C"
    return ""
