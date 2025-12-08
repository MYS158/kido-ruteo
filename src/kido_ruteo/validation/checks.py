"""Funciones de validación y chequeos lógicos para la Fase D."""
from __future__ import annotations

import logging
from typing import Any, Mapping

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def check_ratio_x(ratio: float | None, tolerance: float = 0.15, smoothing: float = 0.1) -> float:
    """Score para ratio X (MC2 length / MC length).

    - ratio ≈ 1.0 → score alto
    - Deviaciones > tolerance → penalización

    Returns: score ∈ [0, 1]
    """
    if ratio is None or pd.isna(ratio):
        return 0.5
    if ratio <= 0:
        return 0.0

    # Desviación respecto a 1.0
    deviation = abs(ratio - 1.0)

    # Sin desviación → score máximo
    if deviation <= 0.01:
        return 1.0

    # Score lineal con smoothing
    if deviation <= tolerance:
        return 1.0 - (deviation / tolerance) * (1.0 - smoothing)
    else:
        return max(0.0, smoothing - (deviation - tolerance) * smoothing)


def check_distancia_pct(diff_pct: float | None, tolerance: float = 0.15, smoothing: float = 0.1) -> float:
    """Score para diferencia porcentual de distancia.

    - diff_pct ≈ 0% → score alto
    - |diff_pct| > tolerance → penalización

    Returns: score ∈ [0, 1]
    """
    if diff_pct is None or pd.isna(diff_pct):
        return 0.5

    diff_abs = abs(diff_pct)

    # Sin diferencia → score máximo
    if diff_abs <= 0.01:
        return 1.0

    # Score lineal con smoothing
    if diff_abs <= tolerance:
        return 1.0 - (diff_abs / tolerance) * (1.0 - smoothing)
    else:
        return max(0.0, smoothing - (diff_abs - tolerance) * smoothing)


def check_tiempo_pct(diff_pct: float | None, tolerance: float = 0.2, smoothing: float = 0.1) -> float:
    """Score para diferencia porcentual de tiempo.

    Returns: score ∈ [0, 1]
    """
    if diff_pct is None or pd.isna(diff_pct):
        return 0.5

    diff_abs = abs(diff_pct)

    if diff_abs <= 0.01:
        return 1.0

    if diff_abs <= tolerance:
        return 1.0 - (diff_abs / tolerance) * (1.0 - smoothing)
    else:
        return max(0.0, smoothing - (diff_abs - tolerance) * smoothing)


def check_checkpoint(passed: bool | None, required: bool = True) -> float:
    """Score para validación de checkpoint.

    - Si se requiere y pasó → 1.0
    - Si se requiere y no pasó → 0.0
    - Si no es requerido → 1.0
    - Si es None (desconocido) → 0.5 si requerido, 1.0 si no

    Returns: score ∈ [0, 1]
    """
    if passed is None:
        return 0.5 if required else 1.0
    return 1.0 if passed else (0.0 if required else 1.0)


def check_aforo(
    diff_pct: float | None, aforo_ok: bool | None, tolerance: float = 0.15, smoothing: float = 0.1
) -> float:
    """Score para validación de volumen/aforo.

    Combina:
    - diff_pct: diferencia porcentual del volumen respecto a aforo observado
    - aforo_ok: bandera booleana de consistencia

    Returns: score ∈ [0, 1]
    """
    # Verificar bandera explícita primero
    if isinstance(aforo_ok, bool):
        return 1.0 if aforo_ok else 0.3

    # Si no hay diff_pct, usar score neutral
    if diff_pct is None or pd.isna(diff_pct):
        return 0.5

    diff_abs = abs(diff_pct)

    if diff_abs <= 0.01:
        return 1.0

    if diff_abs <= tolerance:
        return 1.0 - (diff_abs / tolerance) * (1.0 - smoothing)
    else:
        return max(0.0, smoothing - (diff_abs - tolerance) * smoothing)


def check_cardinalidad(cardinalidad_ok: bool | None) -> float:
    """Score para cardinalidad (número de viajes).

    Returns: 1.0 si OK, 0.0 si no OK, 0.5 si desconocido
    """
    if cardinalidad_ok is None or pd.isna(cardinalidad_ok):
        return 0.5
    if isinstance(cardinalidad_ok, str):
        return 1.0 if cardinalidad_ok.strip().lower() in {"true", "1", "yes"} else 0.0
    return 1.0 if cardinalidad_ok else 0.0


def check_flags_validacion(flags: str | list[str] | None) -> float:
    """Score basado en flags de validación.

    Flags pueden ser strings separados por coma, lista, o null.
    Score alto si no hay flags (validez completa).

    Returns: score ∈ [0, 1]
    """
    if flags is None or (isinstance(flags, str) and (not flags or flags.strip() == "")):
        return 1.0

    if isinstance(flags, str):
        flag_list = [f.strip() for f in flags.split(",")]
    elif isinstance(flags, list):
        flag_list = flags
    else:
        return 0.5

    # Sin flags o lista vacía → score máximo
    if not flag_list or all(not f for f in flag_list):
        return 1.0

    # Penalización por cantidad de flags
    score = max(0.0, 1.0 - (len(flag_list) * 0.2))
    return score


def aggregate_score(component_scores: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    """Calcula score agregado ponderado.

    Args:
        component_scores: dict con scores de componentes (map_matching, checkpoint, etc.)
        weights: dict con pesos (por defecto iguales)

    Returns: score final ∈ [0, 1]
    """
    if not component_scores:
        return 0.5

    if weights is None:
        weights = {k: 1.0 / len(component_scores) for k in component_scores}

    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.5

    score = sum(
        component_scores.get(k, 0.5) * weights.get(k, 0.0) for k in component_scores
    ) / total_weight

    return float(np.clip(score, 0.0, 1.0))


__all__ = [
    "check_ratio_x",
    "check_distancia_pct",
    "check_tiempo_pct",
    "check_checkpoint",
    "check_aforo",
    "check_cardinalidad",
    "check_flags_validacion",
    "aggregate_score",
]
