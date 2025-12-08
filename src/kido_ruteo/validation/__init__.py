"""Paquete de validación (Fase D)."""

from .checks import (
	aggregate_score,
	check_aforo,
	check_cardinalidad,
	check_checkpoint,
	check_distancia_pct,
	check_flags_validacion,
	check_ratio_x,
	check_tiempo_pct,
)
from .scoring import classify_score, motivo_principal, normalize_weights, weighted_score
from .validation_pipeline import run_validation_pipeline

__all__ = [
	"aggregate_score",
	"check_aforo",
	"check_cardinalidad",
	"check_checkpoint",
	"check_distancia_pct",
	"check_flags_validacion",
	"check_ratio_x",
	"check_tiempo_pct",
	"classify_score",
	"motivo_principal",
	"normalize_weights",
	"weighted_score",
	"run_validation_pipeline",
]
