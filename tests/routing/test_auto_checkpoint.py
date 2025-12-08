"""Tests para auto_checkpoint.py"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from kido_ruteo.routing.auto_checkpoint import (
    compute_auto_checkpoint,
    get_candidate_nodes,
    _filter_primary_nodes,
)


@pytest.fixture
def gdf_nodes_simple():
    """GeoDataFrame de nodos simple."""
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
    return gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")


@pytest.fixture
def gdf_edges_with_classes():
    """GeoDataFrame de edges con primary_class."""
    edges_data = {
        "u": [1, 2, 3, 4],
        "v": [2, 3, 4, 5],
        "primary_class": ["motorway", "secondary", "primary", "tertiary"],
        "geometry": [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
            LineString([(3, 0), (4, 0)]),
        ],
    }
    return gpd.GeoDataFrame(edges_data, crs="EPSG:4326")


@pytest.fixture
def gdf_edges_no_primary():
    """GeoDataFrame de edges sin vías primarias."""
    edges_data = {
        "u": [1, 2, 3, 4],
        "v": [2, 3, 4, 5],
        "primary_class": ["tertiary", "residential", "tertiary", "residential"],
        "geometry": [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
            LineString([(3, 0), (4, 0)]),
        ],
    }
    return gpd.GeoDataFrame(edges_data, crs="EPSG:4326")


def test_compute_auto_checkpoint_middle_range(gdf_nodes_simple, gdf_edges_with_classes):
    """Test: Checkpoint en rango 40-60% con vía primaria."""
    mc_nodes = [1, 2, 3, 4, 5]
    
    result = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_with_classes)
    
    assert result["checkpoint_node"] in [2, 3, 4]  # Rango 40-60% excluye 1 y 5
    assert result["checkpoint_source"] == "auto"
    assert "checkpoint_index" in result
    
    # Con primary_class, debe preferir nodo 3 o 4 (primary/motorway)
    assert result["checkpoint_node"] in [3, 4]


def test_compute_auto_checkpoint_no_primary_roads(gdf_nodes_simple, gdf_edges_no_primary):
    """Test: Sin vías primarias, debe elegir del rango completo."""
    mc_nodes = [1, 2, 3, 4, 5]
    
    result = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_no_primary)
    
    # Debe elegir del rango 40-60% (nodos 2, 3, 4)
    assert result["checkpoint_node"] in [2, 3, 4]
    assert result["checkpoint_source"] == "auto"


def test_compute_auto_checkpoint_short_route(gdf_nodes_simple, gdf_edges_with_classes):
    """Test: Ruta corta (<3 nodos) debe elegir el nodo del medio."""
    mc_nodes = [1, 2]
    
    result = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_with_classes)
    
    # Con 2 nodos, no hay nodo intermedio válido, debe devolver None o el índice 1
    # Según implementación, podría ser nodo 2 (el último)
    assert result["checkpoint_node"] in [1, 2]
    assert result["checkpoint_source"] == "auto"


def test_compute_auto_checkpoint_three_nodes(gdf_nodes_simple, gdf_edges_with_classes):
    """Test: Ruta de 3 nodos debe elegir el del medio."""
    mc_nodes = [1, 2, 3]
    
    result = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_with_classes)
    
    # Con 3 nodos, el del medio es el índice 1 (nodo 2)
    assert result["checkpoint_node"] == 2
    assert result["checkpoint_index"] == 1
    assert result["checkpoint_source"] == "auto"


def test_compute_auto_checkpoint_custom_percentiles(gdf_nodes_simple, gdf_edges_with_classes):
    """Test: Usar percentiles personalizados."""
    mc_nodes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # Percentil 30-70%
    result = compute_auto_checkpoint(
        mc_nodes,
        gdf_nodes_simple,
        gdf_edges_with_classes,
        percent_lower=0.30,
        percent_upper=0.70,
    )
    
    # Rango 30-70% de 10 nodos = índices 3-7 (nodos 4-8)
    assert result["checkpoint_node"] in [4, 5, 6, 7, 8]
    assert result["checkpoint_source"] == "auto"


def test_get_candidate_nodes():
    """Test: Obtener nodos candidatos en rango de percentiles."""
    mc_nodes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    candidates, idx_lower, idx_upper = get_candidate_nodes(mc_nodes, 0.40, 0.60)
    
    # 40% de 10 = 4, 60% de 10 = 6
    # Excluye origen (0) y destino (9)
    assert idx_lower == 4
    assert idx_upper == 6
    assert candidates == [4, 5]  # Índices 4-5


def test_get_candidate_nodes_short_route():
    """Test: Ruta corta debe devolver al menos un candidato."""
    mc_nodes = [1, 2, 3]
    
    candidates, idx_lower, idx_upper = get_candidate_nodes(mc_nodes, 0.40, 0.60)
    
    # Debe haber al menos un candidato
    assert len(candidates) >= 1
    # Para ruta de 3 nodos, devuelve el índice medio (n//2 = 1)
    assert candidates == [1]


def test_filter_primary_nodes(gdf_edges_with_classes):
    """Test: Filtrar nodos en vías primarias."""
    mc_nodes = [1, 2, 3, 4, 5]
    candidate_indices = [1, 2, 3]  # Nodos 2, 3, 4
    
    primary_indices = _filter_primary_nodes(candidate_indices, mc_nodes, gdf_edges_with_classes)
    
    # Nodos 2 y 4 tienen edges con motorway/primary
    # Nodo 3 tiene edge con primary (incoming y outgoing)
    assert 2 in primary_indices  # Edge 2→3 es primary o 1→2 es motorway


def test_filter_primary_nodes_none_found(gdf_edges_no_primary):
    """Test: Sin vías primarias, debe devolver lista vacía."""
    mc_nodes = [1, 2, 3, 4, 5]
    candidate_indices = [1, 2, 3]
    
    primary_indices = _filter_primary_nodes(candidate_indices, mc_nodes, gdf_edges_no_primary)
    
    # No hay vías primarias
    assert len(primary_indices) == 0


def test_compute_auto_checkpoint_deterministic(gdf_nodes_simple, gdf_edges_with_classes):
    """Test: Resultado debe ser determinístico."""
    mc_nodes = [1, 2, 3, 4, 5]
    
    result1 = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_with_classes)
    result2 = compute_auto_checkpoint(mc_nodes, gdf_nodes_simple, gdf_edges_with_classes)
    
    assert result1["checkpoint_node"] == result2["checkpoint_node"]
    assert result1["checkpoint_index"] == result2["checkpoint_index"]
