"""Cálculo de caminos más cortos (MC) usando NetworkX."""
from __future__ import annotations

import logging
from typing import Any

import networkx as nx


logger = logging.getLogger(__name__)


class NoPathFoundError(Exception):
    """Excepción cuando no existe ruta entre origen y destino."""
    pass


def compute_shortest_path(
    graph: nx.DiGraph,
    origin_node: Any,
    dest_node: Any,
    weight: str = "weight",
) -> dict[str, Any]:
    """Calcula camino más corto entre origen y destino.
    
    Args:
        graph: Grafo dirigido con edges que tienen atributo weight
        origin_node: Nodo de origen
        dest_node: Nodo de destino
        weight: Atributo a usar como peso (default: "weight" = tiempo)
        
    Returns:
        Diccionario con:
        - path_nodes: lista de nodos en la ruta
        - path_edges: lista de tuplas (u, v) de edges
        - length_m: longitud total en metros
        - time_min: tiempo total en minutos
        
    Raises:
        NoPathFoundError: Si no existe ruta entre origen y destino
        ValueError: Si los nodos no existen en el grafo
    """
    # Validar que los nodos existen
    if origin_node not in graph.nodes():
        raise ValueError(f"Nodo origen {origin_node} no existe en el grafo")
    
    if dest_node not in graph.nodes():
        raise ValueError(f"Nodo destino {dest_node} no existe en el grafo")
    
    # Caso especial: mismo nodo
    if origin_node == dest_node:
        # Retornar una ruta degenerada con el nodo repetido para que capas posteriores
        # (auto checkpoint, constrained path) puedan operar sin fallar por lista vacía.
        return {
            "path_nodes": [origin_node],
            "path_edges": [],
            "length_m": 0.0,
            "time_min": 0.0,
        }
    
    # Calcular camino más corto
    try:
        path_nodes = nx.shortest_path(
            graph,
            source=origin_node,
            target=dest_node,
            weight=weight,
        )
    except nx.NetworkXNoPath:
        raise NoPathFoundError(
            f"No existe ruta entre {origin_node} y {dest_node}"
        )
    except nx.NodeNotFound as exc:
        raise ValueError(f"Nodo no encontrado: {exc}")
    
    # Construir lista de edges
    path_edges = [(path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)]
    
    # Calcular métricas totales
    length_m = 0.0
    time_min = 0.0
    
    for u, v in path_edges:
        edge_data = graph[u][v]
        length_m += edge_data.get("length", 0.0)
        time_min += edge_data.get("weight", 0.0)
    
    logger.info(
        "Ruta calculada: %s → %s (%d nodos, %.2f km, %.2f min)",
        origin_node,
        dest_node,
        len(path_nodes),
        length_m / 1000.0,
        time_min,
    )
    
    return {
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "length_m": length_m,
        "time_min": time_min,
    }


def compute_path_length(
    graph: nx.DiGraph,
    path_nodes: list[Any],
) -> dict[str, float]:
    """Calcula longitud y tiempo de una ruta dada.
    
    Args:
        graph: Grafo dirigido
        path_nodes: Lista de nodos de la ruta
        
    Returns:
        Diccionario con length_m y time_min
    """
    length_m = 0.0
    time_min = 0.0
    
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        if graph.has_edge(u, v):
            edge_data = graph[u][v]
            length_m += edge_data.get("length", 0.0)
            time_min += edge_data.get("weight", 0.0)
        else:
            logger.error("Edge (%s, %s) no existe en el grafo", u, v)
            raise KeyError(f"Edge ({u}, {v}) no existe en el grafo")
    
    return {
        "length_m": length_m,
        "time_min": time_min,
    }
