from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class DataColumnSchema(BaseModel):
    column: str
    unit: str = ""
    required: bool = True


class SetupPayload(BaseModel):
    name: str = "Web setup"
    pressure_unit: str = "кПа"
    pressure_coefficient: float = 1.0
    vessel_volume_ml: float = 150.0
    water_volume_ml: float = 100.0
    time_column: str = "Время"
    data_columns: List[DataColumnSchema] = Field(default_factory=list)


class PlotSettingsPayload(BaseModel):
    line_width: float = 2.0
    line_alpha: float = 0.85
    show_markers: bool = False
    marker_size: float = 4.0
    marker_style: str = "o"
    show_grid: bool = True
    grid_alpha: float = 0.25
    pressure_display_unit: str = "setup"
    signal_downsample_factor: int = 1


class ChartSpec(BaseModel):
    id: str
    title: str
    description: str = ""
    traces: List[Dict[str, Any]]
    layout: Dict[str, Any]


class FileInspectionResponse(BaseModel):
    filename: str
    columns: List[str]
    preview_rows: List[Dict[str, Any]]
    suggested_time_column: Optional[str] = None
    suggested_data_columns: List[DataColumnSchema] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    filename: str
    metadata: Dict[str, str]
    columns: List[str]
    units: Dict[str, str]
    row_count: int
    time_range: Dict[str, float]
    setup: SetupPayload
    plot_settings: PlotSettingsPayload
    data_charts: List[ChartSpec]
    solubility_charts: List[ChartSpec]
    preview_rows: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)
