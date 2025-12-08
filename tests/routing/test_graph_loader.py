"""Tests para graph_loader.py"""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import networkx as nx
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from kido_ruteo.routing.graph_loader import (
    load_graph_from_network_dir,
    validate_node_exists,
    get_graph_stats,
)


@pytest.fixture
def network_dir_simple():
    """Crea un directorio temporal con archivos GPKG de prueba."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear edges.gpkg simple: A → B → C
        edges_data = {
            "u": [1, 2],
            "v": [2, 3],
            "length": [1000.0, 2000.0],  # metros
            "speed": [60.0, 40.0],  # km/h
            "primary_class": ["primary", "secondary"],
            "geometry": [
                LineString([(0, 0), (1, 0)]),
                LineString([(1, 0), (2, 0)]),
            ],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        # Crear nodes.gpkg
        nodes_data = {
            "node_id": [1, 2, 3],
            "geometry": [Point(0, 0), Point(1, 0), Point(2, 0)],
        }
        gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
        gdf_nodes.to_file(tmp_path / "nodes.gpkg", driver="GPKG")
        
        yield tmp_path


@pytest.fixture
def network_dir_no_speed():
    """Red sin columna speed (debe usar default 50 km/h)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        edges_data = {
            "u": [1, 2],
            "v": [2, 3],
            "length": [1000.0, 2000.0],
            "geometry": [
                LineString([(0, 0), (1, 0)]),
                LineString([(1, 0), (2, 0)]),
            ],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        yield tmp_path


def test_load_graph_basic(network_dir_simple):
    """Test: Cargar grafo básico desde GPKG."""
    graph = load_graph_from_network_dir(network_dir_simple)
    
    assert isinstance(graph, nx.DiGraph)
    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2
    
    # Verificar nodos
    assert 1 in graph.nodes
    assert 2 in graph.nodes
    assert 3 in graph.nodes
    
    # Verificar edges
    assert graph.has_edge(1, 2)
    assert graph.has_edge(2, 3)


def test_load_graph_edge_attributes(network_dir_simple):
    """Test: Verificar atributos de edges."""
    graph = load_graph_from_network_dir(network_dir_simple)
    
    # Edge 1 → 2
    edge_12 = graph.edges[1, 2]
    assert edge_12["length"] == 1000.0
    assert edge_12["speed"] == 60.0
    assert edge_12["primary_class"] == "primary"
    
    # Weight debe ser tiempo en minutos: (1000/1000) / 60 * 60 = 1.0 min
    expected_weight_12 = (1000.0 / 1000.0) / 60.0 * 60.0
    assert abs(edge_12["weight"] - expected_weight_12) < 0.01
    
    # Edge 2 → 3
    edge_23 = graph.edges[2, 3]
    assert edge_23["length"] == 2000.0
    assert edge_23["speed"] == 40.0
    
    # Weight: (2000/1000) / 40 * 60 = 3.0 min
    expected_weight_23 = (2000.0 / 1000.0) / 40.0 * 60.0
    assert abs(edge_23["weight"] - expected_weight_23) < 0.01


def test_load_graph_no_speed_column(network_dir_no_speed):
    """Test: Si no hay columna speed, debe usar 50 km/h default."""
    graph = load_graph_from_network_dir(network_dir_no_speed)
    
    # Edge 1 → 2: length=1000, speed=50 (default)
    edge_12 = graph.edges[1, 2]
    assert "weight" in edge_12
    
    # Weight: (1000/1000) / 50 * 60 = 1.2 min
    expected_weight = (1000.0 / 1000.0) / 50.0 * 60.0
    assert abs(edge_12["weight"] - expected_weight) < 0.01


def test_load_graph_missing_file():
    """Test: Error si no existe edges.gpkg."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError, match="edges.gpkg"):
            load_graph_from_network_dir(tmpdir)


def test_load_graph_missing_columns():
    """Test: Error si faltan columnas requeridas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear edges.gpkg sin columna 'v'
        edges_data = {
            "u": [1, 2],
            "length": [1000.0, 2000.0],
            "geometry": [
                LineString([(0, 0), (1, 0)]),
                LineString([(1, 0), (2, 0)]),
            ],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        with pytest.raises(ValueError, match="Faltan columnas requeridas"):
            load_graph_from_network_dir(tmp_path)


def test_load_graph_empty():
    """Test: Error si edges.gpkg está vacío."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear edges.gpkg vacío
        edges_data = {
            "u": [],
            "v": [],
            "length": [],
            "geometry": [],
        }
        gdf_edges = gpd.GeoDataFrame(edges_data, crs="EPSG:4326")
        gdf_edges.to_file(tmp_path / "edges.gpkg", driver="GPKG")
        
        with pytest.raises(ValueError, match="El grafo está vacío"):
            load_graph_from_network_dir(tmp_path)


def test_validate_node_exists(network_dir_simple):
    """Test: Validar existencia de nodos."""
    graph = load_graph_from_network_dir(network_dir_simple)
    
    # Nodo existente no debe lanzar error
    validate_node_exists(graph, 1)
    validate_node_exists(graph, 2)
    validate_node_exists(graph, 3)
    
    # Nodo inexistente debe lanzar error
    with pytest.raises(ValueError, match="El nodo 999 no existe"):
        validate_node_exists(graph, 999)


def test_get_graph_stats(network_dir_simple):
    """Test: Obtener estadísticas del grafo."""
    graph = load_graph_from_network_dir(network_dir_simple)
    stats = get_graph_stats(graph)
    
    assert stats["num_nodes"] == 3
    assert stats["num_edges"] == 2
    assert stats["is_directed"] is True
    assert stats["is_connected"] is True


def test_load_graph_directed(network_dir_simple):
    """Test: El grafo cargado debe ser dirigido."""
    graph = load_graph_from_network_dir(network_dir_simple)
    assert graph.is_directed()
