"""
Excel file parsing service for experimental data.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import cast

import pandas as pd

from visualize_app.models import ExperimentalData
from visualize_app.utils.setup_config import normalize_data_columns
from visualize_app.utils.setup_config import normalize_time_column

logger = logging.getLogger(__name__)


class ExcelParserError(Exception):
    """Custom exception for Excel parsing errors."""

    pass


class ExcelParser:
    """Service for parsing experimental data from Excel files."""

    _SECONDS_PER_HOUR = 3600

    @staticmethod
    def parse_file(
        file_path: Path,
        time_column: Optional[str] = None,
        data_columns: Optional[List[Dict[str, Any]]] = None,
    ) -> ExperimentalData:
        """
        Parse Excel file and return ExperimentalData object.

        Args:
            file_path: Path to the Excel file

        Returns:
            ExperimentalData object with parsed data

        Raises:
            ExcelParserError: If file cannot be parsed or validation fails
        """
        try:
            if not file_path.exists():
                raise ExcelParserError(f"Файл не найден: {file_path}")

            # Read Excel file
            df = pd.read_excel(file_path)

            logger.info(f"Loaded Excel file with {len(df)} rows")

            time_column = normalize_time_column(time_column)
            data_columns = normalize_data_columns(data_columns)
            if not data_columns:
                raise ExcelParserError("Не задан ни один столбец данных")

            required_data_columns = [
                item["column"] for item in data_columns if bool(item.get("required", True))
            ]
            required_columns = list(required_data_columns)
            if time_column:
                required_columns = [time_column] + required_columns

            # Validate columns
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ExcelParserError(
                    f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}"
                )

            # Clean data - remove rows with NaN in critical columns
            df_clean = df.dropna(subset=required_columns)

            if len(df_clean) == 0:
                raise ExcelParserError("Нет корректных данных после очистки")

            logger.info(f"Cleaned data: {len(df_clean)} valid rows")

            # Ensure df_clean is a standalone copy to avoid SettingWithCopyWarning
            df_clean = df_clean.copy()

            # Parse timestamp and convert to hours
            if time_column and time_column in df_clean.columns:
                timestamps = ExcelParser._parse_timestamps(cast(pd.Series, df_clean[time_column]))

                # Ensure timestamps are monotonic by sorting rows
                df_clean["_parsed_time"] = pd.to_datetime(timestamps)
                df_clean = df_clean.sort_values("_parsed_time")
                timestamps = df_clean["_parsed_time"].tolist()
                df_clean = df_clean.drop(columns=["_parsed_time"])

                hours = ExcelParser._convert_to_hours(timestamps)
                time_source = "column"
            else:
                # Fallback: use index as time if no time column provided
                hours = list(range(len(df_clean)))
                timestamps = []
                time_source = "index"

            # Convert comma to dot for numerical columns and convert to float
            available_data_columns = [
                item["column"] for item in data_columns if item["column"] in df_clean.columns
            ]
            numeric_columns = list(available_data_columns)
            df_clean = ExcelParser._convert_numeric_columns(df_clean, numeric_columns)

            # Extract numerical data
            series: Dict[str, List[float]] = {}
            units: Dict[str, str] = {}
            missing_optional_columns: List[str] = []
            for item in data_columns:
                col_name = item["column"]
                if col_name in df_clean.columns:
                    series[col_name] = df_clean[col_name].tolist()
                    units[col_name] = item.get("unit", "")
                elif not bool(item.get("required", True)):
                    missing_optional_columns.append(col_name)

            if not series:
                raise ExcelParserError("В файле не найдено ни одного подходящего столбца данных")

            data = ExperimentalData(
                hours=[float(h) for h in hours],
                series=series,
                units=units,
                metadata={
                    "file_path": str(file_path),
                    "total_rows": str(len(df)),
                    "valid_rows": str(len(df_clean)),
                    "time_source": time_source,
                    "missing_optional_columns": ", ".join(missing_optional_columns),
                    "start_time": timestamps[0].strftime("%d.%m.%Y %H:%M:%S") if timestamps else "",
                    "end_time": timestamps[-1].strftime("%d.%m.%Y %H:%M:%S") if timestamps else "",
                },
            )

            logger.info(f"Successfully parsed {data.size} data points")
            return data

        except pd.errors.EmptyDataError:
            raise ExcelParserError("Файл Excel пуст")
        except pd.errors.ParserError as e:
            raise ExcelParserError(f"Ошибка парсинга файла: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing file: {e}", exc_info=True)
            raise ExcelParserError(f"Неожиданная ошибка: {str(e)}")

    @staticmethod
    def validate_file(
        file_path: Path,
        time_column: Optional[str] = None,
        data_columns: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate Excel file without full parsing.

        Args:
            file_path: Path to the Excel file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return False, "Файл не существует"

            if file_path.suffix not in [".xlsx", ".xls"]:
                return False, "Неподдерживаемый формат файла"

            df = pd.read_excel(file_path, nrows=1)
            time_column = normalize_time_column(time_column)
            data_columns = normalize_data_columns(data_columns)
            if not data_columns:
                return False, "Не задан ни один столбец данных"

            required_columns = [
                item["column"] for item in data_columns if bool(item.get("required", True))
            ]
            if time_column:
                required_columns = [time_column] + required_columns

            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                return False, f"Отсутствуют колонки: {', '.join(missing_columns)}"

            return True, None

        except Exception as e:
            return False, f"Ошибка валидации: {str(e)}"

    @staticmethod
    def _parse_timestamps(time_series: pd.Series) -> list[datetime]:
        """
        Parse timestamps from various formats.

        Args:
            time_series: Pandas series with time data

        Returns:
            List of datetime objects
        """
        timestamps = []

        for idx, value in enumerate(time_series):
            try:
                if isinstance(value, datetime):
                    timestamps.append(value)
                elif isinstance(value, str):
                    # Try to parse string format
                    timestamp = pd.to_datetime(value, format="%d.%m.%Y %H:%M:%S")
                    timestamps.append(timestamp)
                elif isinstance(value, pd.Timestamp):
                    timestamps.append(value.to_pydatetime())
                else:
                    # Try pandas to_datetime as fallback
                    timestamp = pd.to_datetime(value)
                    timestamps.append(timestamp)
            except Exception as e:
                logger.warning(f"Failed to parse timestamp at row {idx}: {value}")
                # Use a placeholder or skip
                raise ExcelParserError(
                    f"Не удалось распарсить время в строке {idx + 2}: {value}: {e}"
                )

        return timestamps

    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """
        Convert numeric columns from comma to dot decimal separator and to float.

        Args:
            df: DataFrame with numeric columns

        Returns:
            DataFrame with converted numeric columns
        """

        for col in columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", ".").astype(float)

        return df

    @staticmethod
    def _convert_to_hours(timestamps: list[datetime]) -> list[float]:
        """
        Convert timestamps to hours elapsed from the first timestamp.

        Args:
            timestamps: List of datetime objects

        Returns:
            List of hours elapsed from the first timestamp
        """
        if not timestamps:
            return []

        start_time = timestamps[0]
        hours = []

        for timestamp in timestamps:
            elapsed_seconds = (timestamp - start_time).total_seconds()
            elapsed_hours = elapsed_seconds / ExcelParser._SECONDS_PER_HOUR
            hours.append(elapsed_hours)

        return hours
