"""Checks y funciones de scoring granular para validación de viajes."""
from __future__ import annotations

import math
from typing import Any, Mapping


def _metric_score(diff_pct: float | None, tolerancia: float, smoothing_factor: float) -> float:
    """Devuelve score en [0,1] basado en diferencia porcentual y tolerancia.

    - diff_pct se interpreta como valor absoluto (ej. 0.10 = 10%).
    - Si diff_pct <= tolerancia → score = 1.0
    - Si diff_pct > tolerancia → decae linealmente con smoothing_factor hasta 0.
    """
    if diff_pct is None or math.isnan(diff_pct):
        return 0.0

    diff = abs(float(diff_pct))
    if diff <= tolerancia:
        return 1.0

    # Decaimiento lineal con margen adicional definido por smoothing_factor
    extra = diff - tolerancia
    denom = tolerancia + smoothing_factor if tolerancia + smoothing_factor > 0 else 1.0
    score = 1.0 - (extra / denom)
    return max(0.0, min(1.0, score))


def check_ratio_x(ratio_x: float | None, tolerancia_distancia_pct: float, smoothing_factor: float) -> float:
    """Evalúa la congruencia de Ratio X (mc2/mc)."""
    if ratio_x is None or math.isnan(ratio_x):
        return 0.0
    diff_pct = abs(float(ratio_x) - 1.0)
    return _metric_score(diff_pct, tolerancia_distancia_pct, smoothing_factor)


def check_tiempo_pct(time_diff_pct: float | None, tolerancia_tiempo_pct: float, smoothing_factor: float) -> float:
    """Evalúa diferencia porcentual de tiempo."""
    return _metric_score(time_diff_pct, tolerancia_tiempo_pct, smoothing_factor)


def check_distancia_pct(distance_diff_pct: float | None, tolerancia_distancia_pct: float, smoothing_factor: float) -> float:
    """Evalúa diferencia porcentual de distancia."""
    return _metric_score(distance_diff_pct, tolerancia_distancia_pct, smoothing_factor)


def check_checkpoint(checkpoint_passed: bool | None, requiere_checkpoint: bool = True) -> float:
    """Evalúa si se cumplió el checkpoint obligatorio."""
    if checkpoint_passed is True:
        return 1.0
    if checkpoint_passed is False and requiere_checkpoint:
        return 0.0
    return 1.0  # Si no es requerido o no hay info, no penaliza


def check_cardinalidad(cardinalidad_ok: bool | None) -> float:
    """Evalúa consistencia de cardinalidad/sentido de viaje."""
    if cardinalidad_ok is True:
        return 1.0
    if cardinalidad_ok is False:
        return 0.0
    return 0.5  # Desconocido → score intermedio


def check_aforo(
    aforo_diff_pct: float | None,
    aforo_ok: bool | None,
    tolerancia_volumen_pct: float,
    smoothing_factor: float,
) -> float:
    """Evalúa consistencia con aforo (volumen observado vs esperado)."""
    if aforo_diff_pct is not None and not math.isnan(aforo_diff_pct):
        return _metric_score(aforo_diff_pct, tolerancia_volumen_pct, smoothing_factor)

    if aforo_ok is True:
        return 1.0
    if aforo_ok is False:
        return 0.0
    return 0.5


def check_flags_validacion(flags: Any) -> float:
    """Evalúa flags de validación limpiados en Fase B.

    Reglas:
    - Si contiene 'critical'/'error' → 0.0
    - Si contiene 'warning'/'warn' → 0.5
    - Si vacío o None → 1.0
    """
    if flags is None:
        return 1.0

    # Normalizar a lista de strings
    if isinstance(flags, str):
        tokens = [flag.strip().lower() for flag in flags.split(";") if flag.strip()]
    elif isinstance(flags, (list, tuple, set)):
        tokens = [str(flag).strip().lower() for flag in flags]
    elif isinstance(flags, bool):
        return 0.0 if flags is True else 1.0
    else:
        tokens = [str(flags).lower()]

    if any(token in {"critical", "error", "invalid", "critico"} for token in tokens):
        return 0.0
    if any(token in {"warning", "warn", "alerta"} for token in tokens):
        return 0.5
    return 1.0 if tokens else 1.0


def aggregate_score(component_scores: Mapping[str, float], pesos_componentes: Mapping[str, float]) -> float:
    """Suma ponderada de componentes (wrapper para pruebas unitarias)."""
    total_pesos = float(sum(pesos_componentes.values()))
    if total_pesos <= 0:
        return 0.0
    score = 0.0
    for name, peso in pesos_componentes.items():
        score += float(component_scores.get(name, 0.0)) * float(peso)
    return max(0.0, min(1.0, score / total_pesos))


__all__ = [
    "check_ratio_x",
    "check_tiempo_pct",
    "check_distancia_pct",
    "check_checkpoint",
    "check_cardinalidad",
    "check_aforo",
    "check_flags_validacion",
    "aggregate_score",
]
