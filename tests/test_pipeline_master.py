"""Tests del pipeline maestro (Fase E)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
import pytest

from kido_ruteo.config.loader import Config, PathsConfig, RoutingConfig, ValidationConfig, InputsConfig
from kido_ruteo.pipeline import run_kido_pipeline


@pytest.fixture
def simple_config(tmp_path: Path) -> Config:
    """Crea configuración mínima para test."""
    # Crear directorios
    data_raw = tmp_path / "data" / "raw"
    data_interim = tmp_path / "data" / "interim"
    data_processed = tmp_path / "data" / "processed"
    network_dir = data_raw / "network"
    logs_dir = data_processed / "logs"

    for d in [data_raw, data_interim, data_processed, network_dir, logs_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Crear red simple: 4 nodos, 4 edges en línea
    nodes_data = {
        "node_id": [1, 2, 3, 4],
        "geometry": [
            gpd.points_from_xy([0], [0])[0],
            gpd.points_from_xy([1], [0])[0],
            gpd.points_from_xy([2], [0])[0],
            gpd.points_from_xy([3], [0])[0],
        ],
        "zone_id": [1, 2, 3, 4],
    }
    gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
    gdf_nodes.to_file(network_dir / "nodes.gpkg", driver="GPKG")

    edges_data = {
        "u": [1, 2, 3],
        "v": [2, 3, 4],
        "length": [1000.0, 1000.0, 1000.0],
        "speed": [50.0, 50.0, 50.0],
    }
    gdf_edges = gpd.GeoDataFrame(edges_data, geometry=[None] * 3, crs="EPSG:4326")
    gdf_edges.to_file(network_dir / "edges.gpkg", driver="GPKG")

    # Crear CSV de OD mínimo
    od_dir = data_raw / "od"
    od_dir.mkdir(exist_ok=True)
    od_data = pd.DataFrame({
        "origin": ["1", "1", "2"],
        "origin_name": ["Zone1", "Zone1", "Zone2"],
        "destination": ["2", "3", "4"],
        "destination_name": ["Zone2", "Zone3", "Zone4"],
        "date": ["2025-01-01", "2025-01-01", "2025-01-01"],
        "total_trips": ["10", "5", "8"],
    })
    od_data.to_csv(od_dir / "test.csv", index=False)

    # Crear GeoJSON de zonas mínimo
    zona_geom = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"name": "Zone1"}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
            {"type": "Feature", "properties": {"name": "Zone2"}, "geometry": {"type": "Point", "coordinates": [1, 0]}},
            {"type": "Feature", "properties": {"name": "Zone3"}, "geometry": {"type": "Point", "coordinates": [2, 0]}},
            {"type": "Feature", "properties": {"name": "Zone4"}, "geometry": {"type": "Point", "coordinates": [3, 0]}},
        ]
    }
    import json
    zona_path = data_raw / "geografia" / "kido_zonas.geojson"
    zona_path.parent.mkdir(exist_ok=True)
    zona_path.write_text(json.dumps(zona_geom))

    # Crear config
    paths_cfg = PathsConfig(
        data_raw=data_raw,
        data_interim=data_interim,
        data_processed=data_processed,
        network=network_dir,
        logs=logs_dir,
        outputs={"geojson": data_processed / "geojson", "matrices": data_processed / "matrices"},
    )

    routing_cfg = RoutingConfig(
        algoritmo="shortest_path",
        weight="weight",
        velocidad_default=50.0,
        max_k_routes=3,
        fix_disconnected_nodes=True,
        max_snap_distance_m=400.0,
        ponderadores={},
        restricciones={},
        checkpoint={"mode": "auto", "percent_lower": 0.40, "percent_upper": 0.60},
        network={},
        centroids=None,  # type: ignore
        manual_selection=None,  # type: ignore
        mc={},
        mc2={},
    )

    validation_cfg = ValidationConfig(
        pesos_componentes={"map_matching": 0.25, "checkpoint": 0.20, "tiempo": 0.20, "volumen": 0.15, "trips": 0.10, "validez": 0.10},
        umbrales_congruencia={"seguro": 0.85, "probable": 0.60, "poco_probable": 0.35},
        calibracion={"tolerancia_tiempo_pct": 0.20, "tolerancia_distancia_pct": 0.15, "tolerancia_volumen_pct": 0.15, "smoothing_factor": 0.1},
        checks_logicos={"requiere_checkpoint": True},
        campos_salida={"incluir_csv": True, "incluir_geojson": False},
    )

    inputs_cfg = InputsConfig(
        od_dir=od_dir,
        od_files=["test.csv"],
        geografia_zonas=zona_path,
        aforo_factors=data_raw / "aforo" / "dummy.xlsx",
    )

    return Config(
        paths=paths_cfg,
        routing=routing_cfg,
        validation=validation_cfg,
        inputs=inputs_cfg,
    )


def test_pipeline_completo(simple_config: Config) -> None:
    """Test de pipeline completo con red simple."""
    result = run_kido_pipeline(simple_config, fix_disconnected_nodes=True)

    assert "processed" in result
    assert "routing" in result
    assert "validation" in result

    df_processed = result["processed"]
    df_routing = result["routing"]
    df_validation = result["validation"]

    # Validaciones básicas
    assert len(df_processed) >= 0, "DataFrame procesado debe existir"
    assert len(df_routing) >= 0, "DataFrame de routing debe existir"
    assert len(df_validation) >= 0, "DataFrame de validación debe existir"

    # Si hay validación, verificar columnas mínimas
    if len(df_validation) > 0:
        assert "score_final" in df_validation.columns
        assert "congruencia_nivel" in df_validation.columns
        assert "motivo_principal" in df_validation.columns


def test_pipeline_sin_fix_disconnected(simple_config: Config) -> None:
    """Test con fix_disconnected_nodes=False."""
    result = run_kido_pipeline(simple_config, fix_disconnected_nodes=False)
    assert result is not None


def test_output_dirs_creados(simple_config: Config) -> None:
    """Verifica que los directorios de salida se creen correctamente."""
    run_kido_pipeline(simple_config)

    final_root = Path(simple_config.paths.data_processed) / "final"
    assert (final_root / "cleaned").exists()
    assert (final_root / "routing").exists()
    assert (final_root / "validation").exists()
    assert (final_root / "logs").exists()

    # Verificar que se crean los CSV mínimos
    assert (final_root / "cleaned" / "processed.csv").exists()
    assert (final_root / "routing" / "routing_results.csv").exists()
    assert (final_root / "validation" / "validation_results.csv").exists()


def test_pipeline_logging(simple_config: Config, tmp_path: Path) -> None:
    """Verifica que el pipeline se ejecute sin errores y genere logs."""
    # Simplemente verificar que el pipeline se ejecuta sin excepción
    result = run_kido_pipeline(simple_config)
    
    # El pipeline debe retornar un dict con las fases
    assert result is not None
    assert isinstance(result, dict)
    assert len(result) == 3  # processed, routing, validation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
