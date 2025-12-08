"""API pública del módulo de validación (Fase D)."""

from .validation_pipeline import run_validation_pipeline
from .checks import (
	check_ratio_x,
	check_tiempo_pct,
	check_distancia_pct,
	check_checkpoint,
	check_cardinalidad,
	check_aforo,
	check_flags_validacion,
	aggregate_score,
)
from .scoring import classify_score, motivo_principal

__all__ = [
	"run_validation_pipeline",
	"check_ratio_x",
	"check_tiempo_pct",
	"check_distancia_pct",
	"check_checkpoint",
	"check_cardinalidad",
	"check_aforo",
	"check_flags_validacion",
	"aggregate_score",
	"classify_score",
	"motivo_principal",
]
