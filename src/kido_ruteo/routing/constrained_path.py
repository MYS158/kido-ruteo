"""Cálculo de rutas con checkpoint intermedio (MC2)."""
from __future__ import annotations

import logging
from typing import Any

import networkx as nx

from .shortest_path import compute_shortest_path, NoPathFoundError


logger = logging.getLogger(__name__)


def compute_constrained_path(
    graph: nx.DiGraph,
    origin_node: Any,
    checkpoint_node: Any,
    dest_node: Any,
    weight: str = "weight",
) -> dict[str, Any]:
    """Calcula ruta en dos etapas: A → C → B.
    
    Args:
        graph: Grafo dirigido
        origin_node: Nodo de origen (A)
        checkpoint_node: Nodo intermedio obligatorio (C)
        dest_node: Nodo de destino (B)
        weight: Atributo a usar como peso
        
    Returns:
        Diccionario con:
        - path_nodes: lista de nodos concatenados [A...C...B]
        - path_edges: lista de tuplas (u, v)
        - length_m: longitud total en metros
        - time_min: tiempo total en minutos
        - checkpoint_node: nodo checkpoint usado
        - segment_ac: dict con info de A → C
        - segment_cb: dict con info de C → B
        
    Raises:
        NoPathFoundError: Si no existe ruta en algún segmento
        ValueError: Si los nodos no existen
    """
    # Validar nodos
    for node, label in [(origin_node, "origen"), (checkpoint_node, "checkpoint"), (dest_node, "destino")]:
        if node not in graph.nodes():
            raise ValueError(f"El nodo {node} no existe en el grafo")
    
    logger.info(
        "Calculando ruta con checkpoint: %s → %s → %s",
        origin_node,
        checkpoint_node,
        dest_node,
    )
    
    # Segmento 1: A → C
    try:
        segment_ac = compute_shortest_path(
            graph,
            origin_node,
            checkpoint_node,
            weight=weight,
        )
    except NoPathFoundError:
        raise NoPathFoundError(
            f"No existe ruta en segmento A → C entre {origin_node} y {checkpoint_node}"
        )
    
    # Segmento 2: C → B
    try:
        segment_cb = compute_shortest_path(
            graph,
            checkpoint_node,
            dest_node,
            weight=weight,
        )
    except NoPathFoundError:
        raise NoPathFoundError(
            f"No existe ruta en segmento C → B entre {checkpoint_node} y {dest_node}"
        )
    
    # Concatenar rutas (eliminar duplicado del checkpoint)
    path_nodes_ac = segment_ac["path_nodes"]
    path_nodes_cb = segment_cb["path_nodes"]
    
    # Unir sin duplicar el checkpoint
    # Si path_nodes_ac o path_nodes_cb están vacíos (mismo nodo), manejar apropiadamente
    if not path_nodes_ac and not path_nodes_cb:
        path_nodes = []
    elif not path_nodes_ac:
        path_nodes = path_nodes_cb
    elif not path_nodes_cb:
        path_nodes = path_nodes_ac
    else:
        path_nodes = path_nodes_ac + path_nodes_cb[1:]
    
    # Concatenar edges
    path_edges = segment_ac["path_edges"] + segment_cb["path_edges"]
    
    # Sumar métricas
    length_m = segment_ac["length_m"] + segment_cb["length_m"]
    time_min = segment_ac["time_min"] + segment_cb["time_min"]
    
    logger.info(
        "Ruta MC2 calculada: %d nodos, %.2f km, %.2f min (AC: %.1f km, CB: %.1f km)",
        len(path_nodes),
        length_m / 1000.0,
        time_min,
        segment_ac["length_m"] / 1000.0,
        segment_cb["length_m"] / 1000.0,
    )
    
    return {
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "length_m": length_m,
        "time_min": time_min,
        "checkpoint_node": checkpoint_node,
        "segment_ac": segment_ac,
        "segment_cb": segment_cb,
    }


def validate_checkpoint_in_path(
    checkpoint_node: Any,
    mc_path_nodes: list[Any],
) -> bool:
    """Valida que el checkpoint está en la ruta MC.
    
    Args:
        checkpoint_node: Nodo checkpoint
        mc_path_nodes: Lista de nodos de la ruta MC
        
    Returns:
        True si el checkpoint está en la ruta, False en caso contrario
    """
    return checkpoint_node in mc_path_nodes
