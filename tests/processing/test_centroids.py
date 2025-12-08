"""Tests para cálculo de centroides por subred (NO geométricos)."""
from __future__ import annotations

import pytest

pytest.importorskip("pandas")
pytest.importorskip("geopandas")

try:
    import networkx as nx
except (ImportError, AttributeError) as exc:
    pytest.skip(f"NetworkX no disponible o incompatible: {exc}", allow_module_level=True)

from shapely.geometry import Point, Polygon, LineString
import pandas as pd
import geopandas as gpd

from kido_ruteo.processing.centroids import (
    compute_subgraph_centroid,
    compute_all_zone_centroids,
)


@pytest.fixture
def simple_network():
    """Red sintética donde un nodo es claramente más central."""
    # Crear nodos en forma de estrella
    nodes = gpd.GeoDataFrame(
        {
            "node_id": ["A", "B", "C", "D", "E"],
            "geometry": [
                Point(0, 0),  # Centro - más central
                Point(1, 0),  # Norte
                Point(0, 1),  # Este
                Point(-1, 0),  # Sur
                Point(0, -1),  # Oeste
            ],
        },
        crs="EPSG:4326",
    )

    # Crear edges en estrella (todos conectados al centro A)
    edges = gpd.GeoDataFrame(
        {
            "from_node": ["A", "A", "A", "A"],
            "to_node": ["B", "C", "D", "E"],
            "geometry": [
                LineString([Point(0, 0), Point(1, 0)]),
                LineString([Point(0, 0), Point(0, 1)]),
                LineString([Point(0, 0), Point(-1, 0)]),
                LineString([Point(0, 0), Point(0, -1)]),
            ],
        },
        crs="EPSG:4326",
    )

    return nodes, edges


@pytest.fixture
def zone_polygon():
    """Polígono que contiene todos los nodos."""
    return Polygon([(-2, -2), (2, -2), (2, 2), (-2, 2)])


def test_degree_centrality_selects_hub(simple_network, zone_polygon):
    """Nodo central (hub) debe ser elegido con método degree."""
    nodes, edges = simple_network

    result = compute_subgraph_centroid(
        zone_id="Z1",
        zone_geom=zone_polygon,
        gdf_nodes=nodes,
        gdf_edges=edges,
        method="degree",
    )

    assert result["zone_id"] == "Z1"
    assert result["centroid_node_id"] == "A"  # Centro con grado 4
    assert result["centrality"] == 4.0  # 4 edges conectados
    assert result["method"] == "degree"
    assert result["nodes_in_zone"] == 5


def test_betweenness_centrality_selects_hub(simple_network, zone_polygon):
    """Nodo central debe tener mayor betweenness (o igual si todos son 0)."""
    nodes, edges = simple_network

    result = compute_subgraph_centroid(
        zone_id="Z1",
        zone_geom=zone_polygon,
        gdf_nodes=nodes,
        gdf_edges=edges,
        method="betweenness",
    )

    assert result["zone_id"] == "Z1"
    assert result["centroid_node_id"] == "A"
    assert result["centrality"] >= 0  # Betweenness puede ser 0 en grafos simples
    assert result["method"] == "betweenness"


def test_empty_zone_falls_back_to_geometric(simple_network):
    """Zona sin nodos debe usar centroide geométrico."""
    nodes, edges = simple_network
    empty_zone = Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])

    result = compute_subgraph_centroid(
        zone_id="Z_empty",
        zone_geom=empty_zone,
        gdf_nodes=nodes,
        gdf_edges=edges,
        method="degree",
    )

    assert result["zone_id"] == "Z_empty"
    assert result["centroid_node_id"] is None
    assert result["method"] == "geometric_fallback"
    assert result["nodes_in_zone"] == 0
    assert 10 < result["x"] < 11
    assert 10 < result["y"] < 11


def test_compute_all_zone_centroids(simple_network):
    """Calcular centroides para múltiples zonas."""
    nodes, edges = simple_network

    zones = gpd.GeoDataFrame(
        {
            "zone_id": ["Z1", "Z2"],
            "geometry": [
                Polygon([(-2, -2), (2, -2), (2, 2), (-2, 2)]),  # Contiene todos
                Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)]),  # Solo B y C
            ],
        },
        crs="EPSG:4326",
    )

    result_gdf = compute_all_zone_centroids(
        zonas_gdf=zones,
        gdf_nodes=nodes,
        gdf_edges=edges,
        method="degree",
    )

    assert len(result_gdf) == 2
    assert result_gdf.iloc[0]["zone_id"] == "Z1"
    assert result_gdf.iloc[1]["zone_id"] == "Z2"
    assert result_gdf.crs == zones.crs


def test_single_node_zone(simple_network):
    """Zona con un solo nodo debe elegir ese nodo."""
    nodes, edges = simple_network
    single_node_zone = Polygon([(0.5, -0.5), (1.5, -0.5), (1.5, 0.5), (0.5, 0.5)])

    result = compute_subgraph_centroid(
        zone_id="Z_single",
        zone_geom=single_node_zone,
        gdf_nodes=nodes,
        gdf_edges=edges,
        method="degree",
    )

    assert result["centroid_node_id"] == "B"
    assert result["nodes_in_zone"] == 1
