"""Valores por defecto para la configuración YAML de kido-ruteo.

Se incluyen estructuras completas para paths, routing y validation. Estos
valores se combinan con los YAML del usuario, llenando campos faltantes.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


# Defaults para paths.yaml
PATHS_DEFAULT: dict[str, Any] = {
    "data_raw": "data/raw/",
    "data_interim": "data/interim/",
    "data_processed": "data/processed/",
    "network": "data/raw/network/",
    "logs": "data/processed/logs/",
    "outputs": {
        "geojson": "data/processed/geojson/",
        "matrices": "data/processed/matrices/",
    },
}

# Defaults para insumos (inputs)
INPUTS_DEFAULT: dict[str, Any] = {
    "od_dir": "data/raw/od/",
    "od_files": [
        "od_viaductos_1018.csv",
        "od_viaductos_1019.csv",
    ],
    "geografia_zonas": "data/raw/geografia/kido_zonas.geojson",
    "aforo_factors": "data/raw/aforo/aforo_factors.xlsx",
}

# Defaults para routing.yaml
ROUTING_DEFAULT: dict[str, Any] = {
    "routing": {
        "algoritmo": "shortest_path",
        "weight": "weight",
        "velocidad_default": 40,
        "max_k_routes": 3,
        "fix_disconnected_nodes": True,
        "max_snap_distance_m": 400,
        "ponderadores": {"tiempo": 1.0, "distancia": 0.0, "costo": 0.0},
        "restricciones": {
            "debe_pasar_por_checkpoint": True,
            "permitir_tolvas": False,
            "permitir_no_pavimentado": False,
            "penalizacion_checkpoint_seg": 120,
        },
        "checkpoint": {
            "mode": "auto",
            "percent_lower": 0.40,
            "percent_upper": 0.60,
        },
    },
    "network": {
        "nodos": "data/raw/network/nodes.gpkg",
        "arcos": "data/raw/network/edges.gpkg",
        "centroides": "data/network/centroids.gpkg",
        "geometrias_aux": "data/raw/network/auxiliary.gpkg",
    },
    "centroids": {
        "method": "degree",
        "recompute": False,
        "output": "data/network/centroids.gpkg",
    },
    "manual_selection": {
        "enabled": True,
        "file": "data/raw/inputs/manual_pair_checkpoints.csv",
        "matching_keys": ["origin_zone_id", "destination_zone_id"],
    },
    "mc": {
        "habilitado": True,
        "sample_pct": 1.0,
        "campos_salida": ["origen", "destino", "tiempo_seg", "distancia_m"],
    },
    "mc2": {
        "habilitado": True,
        "sample_pct": 0.8,
        "checkpoints": {"campo_id": "checkpoint_id", "campo_geom": "geometry"},
        "k_rutas": 3,
        "estrategia": "constrained",
        "campos_salida": [
            "origen",
            "destino",
            "tiempo_seg",
            "distancia_m",
            "checkpoint_id",
        ],
    },
}

# Defaults para validation.yaml
VALIDATION_DEFAULT: dict[str, Any] = {
    "pesos_componentes": {
        "map_matching": 0.25,
        "checkpoint": 0.20,
        "tiempo": 0.20,
        "volumen": 0.15,
        "trips": 0.10,
        "validez": 0.10,
    },
    "umbrales_congruencia": {
        "seguro": 0.85,
        "probable": 0.60,
        "poco_probable": 0.35,
        "imposible": 0.0,
    },
    "calibracion": {
        "tolerancia_tiempo_pct": 0.20,
        "tolerancia_volumen_pct": 0.15,
        "tolerancia_distancia_pct": 0.15,
        "smoothing_factor": 0.1,
    },
    "checks_logicos": {
        "velocidad_min_kph": 5,
        "velocidad_max_kph": 120,
        "requiere_checkpoint": True,
    },
    "campos_salida": {
        "incluir_geojson": True,
        "incluir_csv": True,
        "incluir_resumen": True,
    },
}

def _deep_merge(user: Mapping[str, Any] | None, default: Mapping[str, Any]) -> dict[str, Any]:
    """Combina recursivamente un dict de usuario sobre los valores por defecto."""
    base: dict[str, Any] = deepcopy(default)
    if not user:
        return base

    for key, value in user.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), Mapping):
            base[key] = _deep_merge(value, base[key])
        else:
            base[key] = deepcopy(value)
    return base

def merge_paths(user: Mapping[str, Any] | None) -> dict[str, Any]:
    """Devuelve paths con defaults rellenando faltantes."""
    return _deep_merge(user, PATHS_DEFAULT)

def merge_routing(user: Mapping[str, Any] | None) -> dict[str, Any]:
    """Devuelve routing con defaults rellenando faltantes."""
    return _deep_merge(user, ROUTING_DEFAULT)

def merge_validation(user: Mapping[str, Any] | None) -> dict[str, Any]:
    """Devuelve validation con defaults rellenando faltantes."""
    return _deep_merge(user, VALIDATION_DEFAULT)

def merge_inputs(user: Mapping[str, Any] | None) -> dict[str, Any]:
    """Devuelve inputs con defaults rellenando faltantes."""
    return _deep_merge(user, INPUTS_DEFAULT)

def merge_all(
    paths: Mapping[str, Any] | None = None,
    routing: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Combina los tres bloques con sus defaults respectivos."""
    return {
        "paths": merge_paths(paths),
        "routing": merge_routing(routing),
        "validation": merge_validation(validation),
        "inputs": merge_inputs(inputs),
    }
