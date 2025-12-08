"""Carga y construcción de grafo dirigido desde archivos de red vial."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import pandas as pd


logger = logging.getLogger(__name__)


def load_graph_from_network_dir(network_path: str | Path) -> nx.DiGraph:
    """Carga grafo dirigido desde directorio de red vial.
    
    Args:
        network_path: Ruta al directorio con edges.gpkg, nodes.gpkg
        
    Returns:
        nx.DiGraph con edges que incluyen atributos:
        - length: longitud en metros
        - speed: velocidad en km/h
        - weight: tiempo en minutos (length / speed * 60 / 1000)
        - primary_class: clase de vía
        - geometry: geometría del edge
        
    Raises:
        FileNotFoundError: Si no existen edges o nodes
        ValueError: Si faltan columnas requeridas
    """
    network_path = Path(network_path)
    
    if not network_path.exists():
        raise FileNotFoundError(f"Directorio de red no existe: {network_path}")
    
    # Cargar edges
    edges_file = network_path / "edges.gpkg"
    if not edges_file.exists():
        raise FileNotFoundError(f"No se encontró edges.gpkg en {network_path}")
    
    logger.info("Cargando edges desde %s", edges_file)
    gdf_edges = gpd.read_file(edges_file)
    
    # Validar columnas requeridas
    required_edge_cols = {"u", "v", "length"}
    missing_cols = required_edge_cols - set(gdf_edges.columns)
    if missing_cols:
        raise ValueError(f"Faltan columnas requeridas en edges: {missing_cols}")
    
    # Cargar nodes (opcional, para validación)
    nodes_file = network_path / "nodes.gpkg"
    if nodes_file.exists():
        logger.info("Cargando nodes desde %s", nodes_file)
        gdf_nodes = gpd.read_file(nodes_file)
    else:
        logger.warning("No se encontró nodes.gpkg, se omite validación de nodos")
        gdf_nodes = None
    
    # Construir grafo dirigido
    logger.info("Construyendo grafo dirigido con %d edges", len(gdf_edges))
    G = nx.DiGraph()
    
    for idx, row in gdf_edges.iterrows():
        u = row["u"]
        v = row["v"]
        length = float(row["length"])
        
        # Speed por defecto si no existe
        speed = float(row.get("speed", 50.0))  # 50 km/h por defecto
        
        # Calcular peso: tiempo en minutos
        # weight = (length_m / 1000) / speed_km/h * 60
        weight = (length / 1000.0) / speed * 60.0
        
        # Atributos del edge
        edge_attrs: dict[str, Any] = {
            "length": length,
            "speed": speed,
            "weight": weight,
        }
        
        # Agregar atributos opcionales
        if "primary_class" in row:
            edge_attrs["primary_class"] = row["primary_class"]
        
        if "geometry" in row:
            edge_attrs["geometry"] = row["geometry"]
        
        # Agregar edge al grafo
        G.add_edge(u, v, **edge_attrs)
    
    logger.info(
        "Grafo construido: %d nodos, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    
    # Validar conectividad básica
    if G.number_of_nodes() == 0:
        raise ValueError("El grafo está vacío: no se agregaron nodos")
    
    if G.number_of_edges() == 0:
        raise ValueError("Grafo sin edges: no se puede rutear")
    
    return G


def validate_node_exists(graph: nx.DiGraph, node_id: Any) -> bool:
    """Valida que un nodo existe en el grafo.
    
    Args:
        graph: Grafo dirigido
        node_id: ID del nodo a validar
        
    Returns:
        True si el nodo existe, False en caso contrario
    """
    return node_id in graph.nodes()


def get_graph_stats(graph: nx.DiGraph) -> dict[str, Any]:
    """Obtiene estadísticas del grafo.
    
    Args:
        graph: Grafo dirigido
        
    Returns:
        Diccionario con estadísticas del grafo
    """
    return {
        "num_nodes": graph.number_of_nodes(),
        "num_edges": graph.number_of_edges(),
        "is_directed": graph.is_directed(),
        "is_connected": nx.is_weakly_connected(graph),
    }


def validate_node_exists(graph: nx.DiGraph, node_id: Any) -> None:
    """Valida que un nodo exista en el grafo.
    
    Args:
        graph: Grafo dirigido
        node_id: ID del nodo a validar
        
    Raises:
        ValueError: Si el nodo no existe
    """
    if node_id not in graph.nodes:
        raise ValueError(f"El nodo {node_id} no existe en el grafo")
