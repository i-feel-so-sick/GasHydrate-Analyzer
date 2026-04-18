"""
CO2 solubility analysis engine.

Портирован напрямую из блокнота solubility.ipynb.
Считает растворённый CO2, моли в газовой фазе (уравнение Бертло),
максимальную растворимость (закон Генри) и степень насыщения.
Также детектирует события подкачки газа по скачкам давления.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from dataclasses import field
from typing import List

import numpy as np
from scipy.optimize import fsolve

from visualize_app.models import ExperimentalData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Физические константы (взяты напрямую из блокнота)
# ---------------------------------------------------------------------------

R = 8.314462618  # Дж/(моль·К)

# Параметры корреляции константы Генри: ln H = A + B/T + C*ln(T)
A = -144.44443
B = 8071.06186
C = 19.20040

# Критические параметры CO2
T_c_CO2 = 304.1282  # К
P_c_CO2 = 7.3773e6  # Па

# Параметры уравнения Бертло
a_CO2 = 27 * R**2 * T_c_CO2**3 / (64 * P_c_CO2)
b_CO2 = R * T_c_CO2 / (8 * P_c_CO2)

# Параметры установки по умолчанию (как в блокноте)
V_TOTAL_DEFAULT = 0.00015  # м³ (150 мл)
V_WATER_DEFAULT = 0.0001  # м³ (100 мл)
M_WATER_DEFAULT = 0.1  # кг (100 г)


# ---------------------------------------------------------------------------
# Контейнер результатов
# ---------------------------------------------------------------------------


@dataclass
class SolubilityResult:
    """Результаты анализа растворимости CO2."""

    time_hours: np.ndarray
    pressure_bar: np.ndarray
    temperature_c: np.ndarray
    dissolved_mol: np.ndarray
    max_dissolved_mol: np.ndarray
    gas_mol: np.ndarray
    total_mol: np.ndarray
    saturation_pct: np.ndarray
    injection_indices: List[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Физика (точная копия функций из блокнота)
# ---------------------------------------------------------------------------


def n_from_berthelot(P_bar: float, T_celsius: float, V_gas: float) -> float:
    """Моли CO2 в газовой фазе по уравнению Бертло."""
    P = P_bar * 1e5  # бар → Па
    T = T_celsius + 273.15  # °C → К

    n0 = P * V_gas / (R * T)

    def equation(n):
        n = float(n)
        if n <= 0:
            return 1e10
        Vm = V_gas / n
        if Vm <= b_CO2:
            return 1e10
        P_calc = R * T / (Vm - b_CO2) - a_CO2 / (T * Vm**2)
        return P - P_calc

    try:
        sol, _info, ier, _msg = fsolve(equation, n0, full_output=True)
        if ier != 1:
            return float(n0)
        return float(sol[0])
    except Exception:
        return float(n0)


def henry_const(t_C: float) -> float:
    """
    Константа Генри k_H(T) по трёхпараметрической формуле.
    Возвращает k_H в моль/(кг·бар).
    """
    T = t_C + 273.15
    ln_H = A + B / T + C * math.log(T)
    H = math.exp(ln_H)  # моль/(м³·Па)
    k_H = H * 1e5 / 1000  # моль/(кг·бар)
    return k_H


def calculate_max_solubility(P_bar: float, T_celsius: float, m_water: float) -> float:
    """Максимальное количество растворённого CO2 (моль) по закону Генри."""
    k_H = henry_const(T_celsius)
    C_max = k_H * P_bar  # моль/кг
    n_max = C_max * m_water  # моль
    return n_max


def calculate_gas_phase_moles(P_bar: float, T_celsius: float, V_gas: float) -> float:
    """Моли CO2 в газовой фазе (уравнение Бертло)."""
    return n_from_berthelot(P_bar, T_celsius, V_gas)


def detect_injection_events(
    pressures: np.ndarray,
    threshold: float = 0.5,
    min_time_between_injections: int = 1000,
    min_pressure_threshold: float = 10.0,
) -> List[int]:
    """
    Определяет индексы подкачки газа по резким скачкам давления.

    Args:
        pressures: массив давления в барах
        threshold: минимальный скачок давления (бар) для детектирования подкачки
        min_time_between_injections: минимальное количество точек между подкачками
        min_pressure_threshold: минимальное давление (бар), ниже которого скачки игнорируются
    """
    pressures = np.asarray(pressures, dtype=float)
    injection_indices = []
    last_injection_idx = -min_time_between_injections - 1

    for i in range(1, len(pressures)):
        delta_P = pressures[i] - pressures[i - 1]
        current_P = pressures[i]

        if delta_P > threshold and current_P >= min_pressure_threshold:
            if i - last_injection_idx > min_time_between_injections:
                injection_indices.append(i)
                last_injection_idx = i

    return injection_indices


# ---------------------------------------------------------------------------
# Преобразование единиц давления
# ---------------------------------------------------------------------------


def _to_bar(values: np.ndarray, unit: str) -> np.ndarray:
    """Конвертация массива давления в бары."""
    unit = unit.strip().lower()
    if unit in ("бар", "bar"):
        return values
    if unit in ("кпа", "kpa", ""):
        return values / 100.0
    if unit in ("мпа", "mpa"):
        return values * 10.0
    if unit in ("па", "pa"):
        return values / 1e5
    if unit in ("атм", "atm"):
        return values * 1.01325
    if unit in ("psi",):
        return values * 0.0689476
    if unit in ("мм рт. ст.", "mmhg"):
        return values / 750.062
    logger.warning("Неизвестная единица давления '%s', принимаю кПа", unit)
    return values / 100.0


# ---------------------------------------------------------------------------
# Главная функция анализа
# ---------------------------------------------------------------------------


def analyze_solubility(
    data: ExperimentalData,
    injection_threshold: float = 0.5,
    min_time_between_injections: int = 1000,
    min_pressure_threshold: float = 0.0,
    V_total: float = V_TOTAL_DEFAULT,
    V_water: float = V_WATER_DEFAULT,
    m_water: float = M_WATER_DEFAULT,
) -> SolubilityResult:
    """
    Полный расчёт растворимости CO2 из экспериментальных данных.

    Алгоритм совпадает с analyze_dataframe() из блокнота:
    - давление конвертируется в бары по единицам из data.units
    - аномальные точки с P ≤ 0 фильтруются перед расчётом
    - учитываются события подкачки газа
    - общее количество CO2 накапливается с каждой подкачкой

    Args:
        min_pressure_threshold: минимальное давление (бар) для детектирования подкачек.
            0.0 = автоматически (10% от медианного давления).
    """
    # Находим колонки давления и температуры жидкости
    pressure_col = None
    liquid_col = None
    for name in data.series:
        low = name.lower()
        if any(k in low for k in ("давлен", "pressure")):
            pressure_col = name
        if any(k in low for k in ("жидк", "liquid")):
            liquid_col = name

    if pressure_col is None:
        raise ValueError("Колонка давления не найдена в данных")
    if liquid_col is None:
        raise ValueError("Колонка температуры жидкости не найдена в данных")

    time_hours = np.asarray(data.hours, dtype=float)
    raw_pressure = np.asarray(data.series[pressure_col], dtype=float)
    temperature_c = np.asarray(data.series[liquid_col], dtype=float)

    # Конвертация давления в бары
    pressure_unit = data.units.get(pressure_col, "кПа")
    pressure_bar = _to_bar(raw_pressure, pressure_unit)

    # Фильтрация аномальных точек (P ≤ 0 — выбросы/артефакты датчика)
    valid_mask = pressure_bar > 0.0
    n_total = len(pressure_bar)
    n_valid = int(valid_mask.sum())
    if n_valid < n_total:
        logger.warning(
            "Отфильтровано %d аномальных точек с P ≤ 0 бар из %d",
            n_total - n_valid,
            n_total,
        )
        time_hours = time_hours[valid_mask]
        pressure_bar = pressure_bar[valid_mask]
        temperature_c = temperature_c[valid_mask]

    logger.info(
        "Растворимость: колонка '%s' (единица='%s'), диапазон %.2f–%.2f бар; T %.1f–%.1f °C",
        pressure_col,
        pressure_unit,
        float(pressure_bar.min()),
        float(pressure_bar.max()),
        float(temperature_c.min()),
        float(temperature_c.max()),
    )

    # Автоматический порог детектирования подкачек если не задан
    if min_pressure_threshold == 0.0:
        min_pressure_threshold = float(np.median(pressure_bar)) * 0.3
        logger.info("Авто-порог min_pressure_threshold = %.3f бар", min_pressure_threshold)

    V_gas = V_total - V_water
    n = len(time_hours)

    # Вычисляем моли в газовой фазе и максимальную растворимость для каждой точки
    gas_mol = np.zeros(n)
    max_dissolved = np.zeros(n)
    for i in range(n):
        P = float(pressure_bar[i])
        T = float(temperature_c[i])
        gas_mol[i] = calculate_gas_phase_moles(P, T, V_gas)
        max_dissolved[i] = calculate_max_solubility(P, T, m_water)

    # Детектируем подкачки
    injection_indices = detect_injection_events(
        pressure_bar,
        threshold=injection_threshold,
        min_time_between_injections=min_time_between_injections,
        min_pressure_threshold=min_pressure_threshold,
    )
    injection_set = set(injection_indices)

    # Массовый баланс — точная копия логики analyze_dataframe() из блокнота
    dissolved = np.zeros(n)
    total = np.zeros(n)

    if n > 0:
        # Первая точка: газ только что впущен
        total[0] = gas_mol[0]
        dissolved[0] = 0.0  # ещё не успел раствориться

        for i in range(1, n):
            if i in injection_set:
                # Подкачка: оцениваем добавленный газ
                n_gas_prev = gas_mol[i - 1]
                n_dissolved_prev = dissolved[i - 1]
                n_total_prev = total[i - 1]

                max_dissolution = min(n_gas_prev, max_dissolved[i] - n_dissolved_prev)
                n_gas_without_injection = n_gas_prev - max_dissolution
                n_added = max(0.0, gas_mol[i] - n_gas_without_injection)

                total[i] = n_total_prev + n_added
            else:
                # Закрытая система — общее количество не меняется
                total[i] = total[i - 1]

            n_diss = total[i] - gas_mol[i]
            n_diss = min(n_diss, max_dissolved[i])
            dissolved[i] = max(0.0, n_diss)

    with np.errstate(divide="ignore", invalid="ignore"):
        saturation_pct = np.where(
            max_dissolved > 0,
            np.minimum(dissolved / max_dissolved * 100.0, 100.0),
            0.0,
        )

    logger.info(
        "Расчёт растворимости завершён: %d точек, %d подкачек",
        n,
        len(injection_indices),
    )

    return SolubilityResult(
        time_hours=time_hours,
        pressure_bar=pressure_bar,
        temperature_c=temperature_c,
        dissolved_mol=dissolved,
        max_dissolved_mol=max_dissolved,
        gas_mol=gas_mol,
        total_mol=total,
        saturation_pct=saturation_pct,
        injection_indices=injection_indices,
    )


__all__ = [
    "SolubilityResult",
    "analyze_solubility",
    "henry_const",
    "calculate_max_solubility",
    "calculate_gas_phase_moles",
    "n_from_berthelot",
    "detect_injection_events",
    "V_TOTAL_DEFAULT",
    "V_WATER_DEFAULT",
    "M_WATER_DEFAULT",
]
