"""
Pressure unit normalization and conversion helpers.
"""

from typing import Iterable
from typing import List
from typing import Optional

PRESSURE_UNIT_KPA_FACTORS = {
    "кПа": 1.0,
    "МПа": 1000.0,
    "бар": 100.0,
    "атм": 101.325,
    "Па": 0.001,
    "psi": 6.894757293168,
    "мм рт. ст.": 0.13332236842,
}

PRESSURE_UNIT_ALIASES = {
    "кпа": "кПа",
    "kpa": "кПа",
    "mpa": "МПа",
    "мпа": "МПа",
    "бар": "бар",
    "bar": "бар",
    "атм": "атм",
    "atm": "атм",
    "атмосфера": "атм",
    "atmosphere": "атм",
    "па": "Па",
    "pa": "Па",
    "pascal": "Па",
    "паскаль": "Па",
    "psi": "psi",
    "мм рт. ст.": "мм рт. ст.",
    "мм рт.ст.": "мм рт. ст.",
    "мм.рт.ст.": "мм рт. ст.",
    "мм рт ст": "мм рт. ст.",
    "mmhg": "мм рт. ст.",
    "torr": "мм рт. ст.",
}


def normalize_pressure_unit(unit: Optional[str]) -> str:
    """Normalize pressure unit to a canonical form."""
    if unit is None:
        return ""

    unit_text = str(unit).strip()
    if not unit_text:
        return ""

    if unit_text in PRESSURE_UNIT_KPA_FACTORS:
        return unit_text

    return PRESSURE_UNIT_ALIASES.get(unit_text.lower(), "")


def is_pressure_unit(unit: Optional[str]) -> bool:
    """Return True when value is a known pressure unit."""
    return bool(normalize_pressure_unit(unit))


def convert_pressure_value(value: float, from_unit: str, to_unit: str) -> float:
    """Convert pressure value from one unit to another."""
    source = normalize_pressure_unit(from_unit)
    target = normalize_pressure_unit(to_unit)

    if not source:
        raise ValueError(f"Unsupported source pressure unit: {from_unit}")
    if not target:
        raise ValueError(f"Unsupported target pressure unit: {to_unit}")

    if source == target:
        return value

    value_in_kpa = value * PRESSURE_UNIT_KPA_FACTORS[source]
    return value_in_kpa / PRESSURE_UNIT_KPA_FACTORS[target]


def convert_pressure_series(values: Iterable[float], from_unit: str, to_unit: str) -> List[float]:
    """Convert iterable pressure values from source unit to target unit."""
    return [convert_pressure_value(float(value), from_unit, to_unit) for value in values]
