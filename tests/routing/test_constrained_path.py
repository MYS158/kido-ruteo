"""Tests para constrained_path.py"""
from __future__ import annotations

import networkx as nx
import pytest

from kido_ruteo.routing.constrained_path import (
    compute_constrained_path,
    validate_checkpoint_in_path,
)
from kido_ruteo.routing.shortest_path import NoPathFoundError


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
    """Grafo con múltiples rutas.
    
    1 → 2 → 4
    1 → 3 → 4
    """
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=2.0, length=2000.0, time=2.0)
    G.add_edge(2, 4, weight=3.0, length=3000.0, time=3.0)
    G.add_edge(1, 3, weight=4.0, length=4000.0, time=4.0)
    G.add_edge(3, 4, weight=1.0, length=1000.0, time=1.0)
    return G


@pytest.fixture
def disconnected_graph():
    """Grafo con componentes desconectados."""
    G = nx.DiGraph()
    G.add_edge(1, 2, weight=1.0, length=1000.0, time=1.0)
    G.add_edge(3, 4, weight=1.0, length=1000.0, time=1.0)
    return G


def test_compute_constrained_path_simple(simple_graph):
    """Test: Ruta con checkpoint en el medio 1 → 2 → 4 via 2."""
    result = compute_constrained_path(simple_graph, 1, 2, 4)
    
    # Ruta debe ser 1 → 2 → 3 → 4 (checkpoint en 2)
    assert result["checkpoint_node"] == 2
    assert result["path_nodes"] == [1, 2, 3, 4]
    assert result["path_edges"] == [(1, 2), (2, 3), (3, 4)]
    
    # Verificar métricas totales
    assert result["length_m"] == 4500.0  # 1000 + 2000 + 1500
    assert result["time_min"] == 4.5
    
    # Verificar segmentos
    assert result["segment_ac"]["path_nodes"] == [1, 2]
    assert result["segment_cb"]["path_nodes"] == [2, 3, 4]


def test_compute_constrained_path_no_duplication(simple_graph):
    """Test: El checkpoint no debe estar duplicado en la ruta."""
    result = compute_constrained_path(simple_graph, 1, 3, 4)
    
    # Ruta: 1 → 2 → 3 (AC) + 3 → 4 (CB)
    # El nodo 3 no debe aparecer dos veces
    assert result["path_nodes"] == [1, 2, 3, 4]
    assert result["path_nodes"].count(3) == 1


def test_compute_constrained_path_checkpoint_adjacent(simple_graph):
    """Test: Checkpoint adyacente al origen."""
    result = compute_constrained_path(simple_graph, 1, 2, 4)
    
    # Segmento AC: 1 → 2
    assert result["segment_ac"]["path_nodes"] == [1, 2]
    # Segmento CB: 2 → 3 → 4
    assert result["segment_cb"]["path_nodes"] == [2, 3, 4]
    # Ruta completa: 1 → 2 → 3 → 4
    assert result["path_nodes"] == [1, 2, 3, 4]


def test_compute_constrained_path_origin_equals_checkpoint(simple_graph):
    """Test: Origen = checkpoint (caso especial)."""
    result = compute_constrained_path(simple_graph, 1, 1, 4)
    
    # Segmento AC: vacío (origen = checkpoint)
    assert result["segment_ac"]["path_nodes"] == []
    # Segmento CB: 1 → 2 → 3 → 4
    assert result["segment_cb"]["path_nodes"] == [1, 2, 3, 4]
    # Ruta completa: 1 → 2 → 3 → 4
    assert result["path_nodes"] == [1, 2, 3, 4]


def test_compute_constrained_path_checkpoint_equals_destination(simple_graph):
    """Test: Checkpoint = destino (caso especial)."""
    result = compute_constrained_path(simple_graph, 1, 4, 4)
    
    # Segmento AC: 1 → 2 → 3 → 4
    assert result["segment_ac"]["path_nodes"] == [1, 2, 3, 4]
    # Segmento CB: vacío (checkpoint = destino)
    assert result["segment_cb"]["path_nodes"] == []
    # Ruta completa: 1 → 2 → 3 → 4
    assert result["path_nodes"] == [1, 2, 3, 4]


def test_compute_constrained_path_metrics_sum(simple_graph):
    """Test: Métricas totales deben ser suma de segmentos."""
    result = compute_constrained_path(simple_graph, 1, 3, 4)
    
    # Segmento AC: 1 → 2 → 3 (length=3000, time=3.0)
    assert result["segment_ac"]["length_m"] == 3000.0
    assert result["segment_ac"]["time_min"] == 3.0
    
    # Segmento CB: 3 → 4 (length=1500, time=1.5)
    assert result["segment_cb"]["length_m"] == 1500.0
    assert result["segment_cb"]["time_min"] == 1.5
    
    # Total: 3000 + 1500 = 4500
    assert result["length_m"] == 4500.0
    assert result["time_min"] == 4.5


def test_compute_constrained_path_no_path_ac(disconnected_graph):
    """Test: No hay ruta de A a C."""
    with pytest.raises(NoPathFoundError, match="segmento A → C"):
        compute_constrained_path(disconnected_graph, 1, 3, 4)


def test_compute_constrained_path_no_path_cb(disconnected_graph):
    """Test: No hay ruta de C a B."""
    with pytest.raises(NoPathFoundError, match="segmento C → B"):
        compute_constrained_path(disconnected_graph, 1, 2, 4)


def test_compute_constrained_path_node_not_found(simple_graph):
    """Test: Nodo inexistente."""
    with pytest.raises(ValueError, match="El nodo 999 no existe"):
        compute_constrained_path(simple_graph, 1, 999, 4)


def test_validate_checkpoint_in_path():
    """Test: Validar si checkpoint está en ruta MC."""
    mc_path = [1, 2, 3, 4, 5]
    
    # Checkpoint en la ruta
    assert validate_checkpoint_in_path(3, mc_path) is True
    
    # Checkpoint no en la ruta
    assert validate_checkpoint_in_path(99, mc_path) is False
    
    # Checkpoint en origen
    assert validate_checkpoint_in_path(1, mc_path) is True
    
    # Checkpoint en destino
    assert validate_checkpoint_in_path(5, mc_path) is True


def test_compute_constrained_path_custom_weight(graph_with_branches):
    """Test: Usar atributo de peso personalizado."""
    # Con weight default, debería elegir 1 → 2 → 4 (checkpoint en 2)
    result1 = compute_constrained_path(graph_with_branches, 1, 2, 4, weight="weight")
    assert result1["path_nodes"] == [1, 2, 4]
    
    # Con weight="length", debería seguir eligiendo rutas más cortas
    result2 = compute_constrained_path(graph_with_branches, 1, 2, 4, weight="length")
    assert result2["path_nodes"] == [1, 2, 4]
