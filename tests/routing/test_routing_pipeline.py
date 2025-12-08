"""Tests para routing_pipeline.py"""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from kido_ruteo.routing.routing_pipeline import (
    run_routing_pipeline,
    _process_od_pair,
)


@pytest.fixture
def network_dir_complete():
    """Directorio de red completo para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear edges.gpkg: 1 → 2 → 3 → 4 → 5
        edges_data = {
            "u": [1, 2, 3, 4, 1, 3],
            "v": [2, 3, 4, 5, 3, 5],
            "length": [1000.0, 2000.0, 1500.0, 1000.0, 3000.0, 2500.0],
            "speed": [60.0, 50.0, 40.0, 60.0, 30.0, 50.0],
            "primary_class": ["motorway", "primary", "secondary", "primary", "tertiary", "secondary"],
            "geometry": [
                LineString([(0, 0), (1, 0)]),
                LineString([(1, 0), (2, 0)]),
                LineString([(2, 0), (3, 0)]),
                LineString([(3, 0), (4, 0)]),
                LineString([(0, 0), (2, 0)]),
                LineString([(2, 0), (4, 0)]),
            ],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        # Crear nodes.gpkg
        nodes_data = {
            "node_id": [1, 2, 3, 4, 5],
            "geometry": [
                Point(0, 0),
                Point(1, 0),
                Point(2, 0),
                Point(3, 0),
                Point(4, 0),
            ],
        }
        gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
        gdf_nodes.to_file(tmp_path / "nodes.gpkg", driver="GPKG")
        
        yield tmp_path, gdf_nodes, gdf_edges


@pytest.fixture
def df_od_simple():
    """DataFrame OD simple."""
    return pd.DataFrame({
        "origin_node_id": [1, 1, 2],
        "destination_node_id": [5, 4, 5],
    })


@pytest.fixture
def df_manual_checkpoints():
    """DataFrame con checkpoints manuales."""
    return pd.DataFrame({
        "origin_zone_id": [1, 2],
        "destination_zone_id": [5, 5],
        "checkpoint_node_id": [3, 4],
    })


def test_run_routing_pipeline_basic(network_dir_complete, df_od_simple):
    """Test: Pipeline básico sin checkpoints manuales."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=df_od_simple,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="auto",
    )
    
    # Verificar que se procesaron todos los pares
    assert len(df_results) == len(df_od_simple)
    
    # Verificar columnas requeridas
    expected_cols = {
        "origin_node_id",
        "destination_node_id",
        "auto_checkpoint",
        "checkpoint_source",
        "mc_length_m",
        "mc_time_min",
        "mc2_length_m",
        "mc2_time_min",
        "ratio_x",
        "path_nodes_mc",
        "path_nodes_mc2",
    }
    assert expected_cols.issubset(set(df_results.columns))
    
    # Verificar que checkpoint_source es "auto"
    assert (df_results["checkpoint_source"] == "auto").all()


def test_run_routing_pipeline_with_manual_checkpoints(
    network_dir_complete,
    df_od_simple,
    df_manual_checkpoints,
):
    """Test: Pipeline con checkpoints manuales."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=df_od_simple,
        df_manual_checkpoints=df_manual_checkpoints,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="manual",
    )
    
    # Par 1 → 5 debe tener checkpoint manual en 3
    row_1_5 = df_results[
        (df_results["origin_node_id"] == 1) & (df_results["destination_node_id"] == 5)
    ].iloc[0]
    
    assert row_1_5["checkpoint_source"] == "manual"
    assert row_1_5["manual_checkpoint"] == 3
    
    # Par 2 → 5 debe tener checkpoint manual en 4
    row_2_5 = df_results[
        (df_results["origin_node_id"] == 2) & (df_results["destination_node_id"] == 5)
    ].iloc[0]
    
    assert row_2_5["checkpoint_source"] == "manual"
    assert row_2_5["manual_checkpoint"] == 4


def test_run_routing_pipeline_ratio_x_calculation(network_dir_complete, df_od_simple):
    """Test: Cálculo correcto de ratio X."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=df_od_simple,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    # Verificar que ratio_x = mc2_length / mc_length
    for idx, row in df_results.iterrows():
        if "error" not in row or pd.isna(row.get("error")):
            expected_ratio = row["mc2_length_m"] / row["mc_length_m"]
            assert abs(row["ratio_x"] - expected_ratio) < 0.001


def test_run_routing_pipeline_saves_to_output_dir(network_dir_complete, df_od_simple):
    """Test: Guardar resultados en output_dir."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    with tempfile.TemporaryDirectory() as output_dir:
        df_results = run_routing_pipeline(
            network_path=network_path,
            df_od=df_od_simple,
            gdf_nodes=gdf_nodes,
            gdf_edges=gdf_edges,
            output_dir=output_dir,
        )
        
        # Verificar que se creó el archivo
        output_file = Path(output_dir) / "routing_results.csv"
        assert output_file.exists()
        
        # Verificar que se puede leer
        df_loaded = pd.read_csv(output_file)
        assert len(df_loaded) == len(df_results)


def test_run_routing_pipeline_missing_od_columns():
    """Test: Error si faltan columnas en df_od."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear red mínima
        edges_data = {
            "u": [1],
            "v": [2],
            "length": [1000.0],
            "geometry": [LineString([(0, 0), (1, 0)])],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        # DataFrame OD sin columnas requeridas
        df_od = pd.DataFrame({"origin": [1], "destination": [2]})
        
        with pytest.raises(ValueError, match="Faltan columnas en df_od"):
            run_routing_pipeline(network_path=tmp_path, df_od=df_od)


def test_run_routing_pipeline_handles_errors(network_dir_complete):
    """Test: Manejo de errores en pares individuales."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    # DataFrame con un par inválido (nodo inexistente)
    df_od = pd.DataFrame({
        "origin_node_id": [1, 999],
        "destination_node_id": [5, 5],
    })
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=df_od,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
    )
    
    # Primer par debe procesarse correctamente
    assert pd.isna(df_results.iloc[0].get("error")) or df_results.iloc[0].get("error") is None
    
    # Segundo par debe tener error
    assert pd.notna(df_results.iloc[1]["error"])
    assert "no válido" in str(df_results.iloc[1]["error"]).lower() or "no existe" in str(df_results.iloc[1]["error"]).lower()


def test_process_od_pair_auto_checkpoint(network_dir_complete):
    """Test: Procesamiento de par individual con checkpoint auto."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    from kido_ruteo.routing.graph_loader import load_graph_from_network_dir
    
    graph = load_graph_from_network_dir(network_path)
    
    result = _process_od_pair(
        graph=graph,
        origin=1,
        destination=5,
        df_manual_checkpoints=None,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        weight="weight",
        checkpoint_mode="auto",
        percent_lower=0.40,
        percent_upper=0.60,
    )
    
    assert "origin_node_id" in result
    assert "destination_node_id" in result
    assert result["origin_node_id"] == 1
    assert result["destination_node_id"] == 5
    assert "auto_checkpoint" in result
    assert result["checkpoint_source"] == "auto"
    assert "mc_length_m" in result
    assert "mc2_length_m" in result
    assert "ratio_x" in result


def test_run_routing_pipeline_custom_percentiles(network_dir_complete, df_od_simple):
    """Test: Usar percentiles personalizados."""
    network_path, gdf_nodes, gdf_edges = network_dir_complete
    
    df_results = run_routing_pipeline(
        network_path=network_path,
        df_od=df_od_simple,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        percent_lower=0.30,
        percent_upper=0.70,
    )
    
    # Verificar que se procesaron todos los pares
    assert len(df_results) == len(df_od_simple)
    assert "auto_checkpoint" in df_results.columns
