"""Tests para shortest_path.py"""
from __future__ import annotations

import networkx as nx
import pytest

from kido_ruteo.routing.shortest_path import (
    compute_shortest_path,
    compute_path_length,
    NoPathFoundError,
)


@pytest.fixture
def simple_graph():
    """Grafo simple: 1 → 2 → 3 → 4."""
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=1.0, length=1000.0, time=1.0)
    G.add_edge(2, 3, weight=2.0, length=2000.0, time=2.0)
    G.add_edge(3, 4, weight=1.5, length=1500.0, time=1.5)
    return G


@pytest.fixture
def graph_with_branches():
    """Grafo con dos rutas alternativas.
    
    Ruta directa: 1 → 2 → 4 (weight=5)
    Ruta larga: 1 → 3 → 4 (weight=8)
    """
    G = nx.DiGraph()
    # Ruta corta
    G.add_edge(1, 2, weight=2.0, length=2000.0, time=2.0)
    G.add_edge(2, 4, weight=3.0, length=3000.0, time=3.0)
    # Ruta larga
    G.add_edge(1, 3, weight=4.0, length=4000.0, time=4.0)
    G.add_edge(3, 4, weight=4.0, length=4000.0, time=4.0)
    return G


@pytest.fixture
def disconnected_graph():
    """Grafo con componentes desconectados: 1 → 2, 3 → 4."""
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=1.0, length=1000.0, time=1.0)
    G.add_edge(3, 4, weight=1.0, length=1000.0, time=1.0)
    return G


def test_compute_shortest_path_simple(simple_graph):
    """Test: Ruta simple 1 → 4."""
    result = compute_shortest_path(simple_graph, 1, 4)
    
    assert result["path_nodes"] == [1, 2, 3, 4]
    assert result["path_edges"] == [(1, 2), (2, 3), (3, 4)]
    
    # Verificar métricas
    assert result["length_m"] == 4500.0  # 1000 + 2000 + 1500
    assert result["time_min"] == 4.5  # 1.0 + 2.0 + 1.5


def test_compute_shortest_path_adjacent_nodes(simple_graph):
    """Test: Ruta entre nodos adyacentes 1 → 2."""
    result = compute_shortest_path(simple_graph, 1, 2)
    
    assert result["path_nodes"] == [1, 2]
    assert result["path_edges"] == [(1, 2)]
    assert result["length_m"] == 1000.0
    assert result["time_min"] == 1.0


def test_compute_shortest_path_same_node(simple_graph):
    """Test: Origen = destino debe devolver ruta vacía."""
    result = compute_shortest_path(simple_graph, 2, 2)
    
    assert result["path_nodes"] == []
    assert result["path_edges"] == []
    assert result["length_m"] == 0.0
    assert result["time_min"] == 0.0


def test_compute_shortest_path_chooses_shorter(graph_with_branches):
    """Test: Debe elegir la ruta más corta."""
    result = compute_shortest_path(graph_with_branches, 1, 4)
    
    # Debe elegir ruta 1 → 2 → 4 (weight=5)
    assert result["path_nodes"] == [1, 2, 4]
    assert result["path_edges"] == [(1, 2), (2, 4)]
    assert result["length_m"] == 5000.0
    assert result["time_min"] == 5.0


def test_compute_shortest_path_no_path(disconnected_graph):
    """Test: No hay ruta entre componentes desconectados."""
    with pytest.raises(NoPathFoundError, match="No existe ruta entre 1 y 4"):
        compute_shortest_path(disconnected_graph, 1, 4)


def test_compute_shortest_path_node_not_found(simple_graph):
    """Test: Nodo inexistente debe lanzar ValueError."""
    with pytest.raises(ValueError, match="Nodo destino 999 no existe"):
        compute_shortest_path(simple_graph, 1, 999)
    
    with pytest.raises(ValueError, match="Nodo origen 888 no existe"):
        compute_shortest_path(simple_graph, 888, 4)


def test_compute_shortest_path_custom_weight(simple_graph):
    """Test: Usar atributo de peso personalizado."""
    # Agregar atributo custom_weight
    for u, v in simple_graph.edges:
        simple_graph.edges[u, v]["custom_weight"] = simple_graph.edges[u, v]["weight"] * 2
    
    result = compute_shortest_path(simple_graph, 1, 4, weight="custom_weight")
    
    # Debe seguir encontrando la misma ruta
    assert result["path_nodes"] == [1, 2, 3, 4]


def test_compute_path_length(simple_graph):
    """Test: Calcular métricas para una ruta dada."""
    path = [1, 2, 3]
    result = compute_path_length(simple_graph, path)
    
    assert result["length_m"] == 3000.0  # 1000 + 2000
    assert result["time_min"] == 3.0  # 1.0 + 2.0


def test_compute_path_length_single_node(simple_graph):
    """Test: Ruta de un solo nodo."""
    path = [1]
    result = compute_path_length(simple_graph, path)
    
    assert result["length_m"] == 0.0
    assert result["time_min"] == 0.0


def test_compute_path_length_invalid_edge(simple_graph):
    """Test: Ruta con edge inexistente."""
    path = [1, 3]  # No hay edge directo 1 → 3
    
    with pytest.raises(KeyError):
        compute_path_length(simple_graph, path)
