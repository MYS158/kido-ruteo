"""Clasificación y generación de motivos principales para scores de validación."""
from __future__ import annotations

import logging
from typing import Mapping

import pandas as pd

logger = logging.getLogger(__name__)


def classify_score(score_final: float, thresholds: Mapping[str, float] | None = None) -> str:
    """Clasifica un score numérico a nivel de congruencia.

    Umbrales por defecto (ajustables en config):
    - [0.85, 1.0]: "Muy Alta"
    - [0.70, 0.85): "Alta"
    - [0.55, 0.70): "Media"
    - [0.40, 0.55): "Baja"
    - [0.0, 0.40): "Muy Baja"

    Args:
        score_final: score numérico ∈ [0, 1]
        thresholds: dict opcional con umbrales personalizados

    Returns: nivel de congruencia (str)
    """
    if pd.isna(score_final) or score_final is None:
        return "Sin Datos"

    score = float(score_final)

    if thresholds is None:
        thresholds = {
            "muy_alta": 0.85,
            "alta": 0.70,
            "media": 0.55,
            "baja": 0.40,
        }

    muy_alta_thresh = thresholds.get("muy_alta", 0.85)
    alta_thresh = thresholds.get("alta", 0.70)
    media_thresh = thresholds.get("media", 0.55)
    baja_thresh = thresholds.get("baja", 0.40)

    if score >= muy_alta_thresh:
        return "Muy Alta"
    elif score >= alta_thresh:
        return "Alta"
    elif score >= media_thresh:
        return "Media"
    elif score >= baja_thresh:
        return "Baja"
    else:
        return "Muy Baja"


def motivo_principal(component_scores: Mapping[str, float]) -> str:
    """Identifica el componente con menor score como motivo principal de baja congruencia.

    Args:
        component_scores: dict con scores de componentes

    Returns: nombre del componente con menor score
    """
    if not component_scores:
        return "Sin información"

    valid_scores = {k: v for k, v in component_scores.items() if v is not None and not pd.isna(v)}
    if not valid_scores:
        return "Sin información"

    min_key = min(valid_scores, key=valid_scores.get)
    min_score = valid_scores[min_key]

    # Si todos los scores son altos, no hay motivo de preocupación
    if min_score >= 0.80:
        return "Congruencia Óptima"

    # Mapeo de componentes a motivos
    motivos = {
        "map_matching": "Desviación en Ruteo",
        "checkpoint": "Checkpoint No Pasado",
        "tiempo": "Diferencia Temporal",
        "volumen": "Inconsistencia de Volumen",
        "trips": "Cardinalidad Incorrecta",
        "validez": "Flags de Validación",
    }

    return motivos.get(min_key, f"Bajo score en {min_key}")


__all__ = ["classify_score", "motivo_principal"]
