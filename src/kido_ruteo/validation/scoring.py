"""Funciones de scoring y clasificación para validación de viajes.

Sigue los umbrales y pesos definidos en ``config/validation.yaml``.
"""
from __future__ import annotations

from typing import Mapping


def normalize_weights(pesos: Mapping[str, float]) -> dict[str, float]:
    """Normaliza los pesos para que sumen 1.0.

    Args:
        pesos: Mapeo componente → peso crudo.

    Returns:
        Pesos normalizados. Si la suma es 0, devuelve pesos originales sin normalizar.
    """
    total = float(sum(pesos.values()))
    if total <= 0:
        return dict(pesos)
    return {k: float(v) / total for k, v in pesos.items()}


def weighted_score(component_scores: Mapping[str, float], pesos: Mapping[str, float]) -> float:
    """Calcula el score final como suma ponderada.

    Args:
        component_scores: Scores individuales en [0, 1].
        pesos: Pesos por componente.

    Returns:
        Score final en [0, 1]. Si la suma de pesos es cero retorna 0.0.
    """
    normalized = normalize_weights(pesos)
    if not normalized:
        return 0.0

    score = 0.0
    for key, weight in normalized.items():
        score += float(component_scores.get(key, 0.0)) * weight
    return max(0.0, min(1.0, score))


def classify_score(score_final: float, umbrales: Mapping[str, float]) -> int:
    """Clasifica el score en niveles 1-4 según umbrales.

    Reglas (incluyentes):
    - Nivel 1: score >= umbral seguro
    - Nivel 2: score >= umbral probable
    - Nivel 3: score >= umbral poco_probable
    - Nivel 4: score < umbral poco_probable
    """
    seguro = float(umbrales.get("seguro", 0.85))
    probable = float(umbrales.get("probable", 0.60))
    poco_probable = float(umbrales.get("poco_probable", 0.35))

    if score_final >= seguro:
        return 1
    if score_final >= probable:
        return 2
    if score_final >= poco_probable:
        return 3
    return 4


def motivo_principal(component_scores: Mapping[str, float]) -> str:
    """Devuelve el componente con peor desempeño (menor score).

    Args:
        component_scores: Scores por componente.
    Returns:
        Nombre del componente con score mínimo. Si está vacío, retorna "desconocido".
    """
    if not component_scores:
        return "desconocido"
    min_key = min(component_scores, key=lambda k: component_scores.get(k, 0.0))
    return str(min_key)


__all__ = [
    "normalize_weights",
    "weighted_score",
    "classify_score",
    "motivo_principal",
]
