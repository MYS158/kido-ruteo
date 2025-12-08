"""Cálculo de centroides representativos por subred (NO geométricos).

Los centroides se calculan basándose en la centralidad de nodos dentro de la
zona, usando el subgrafo de red vial intersectante.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal

import pandas as pd

try:
    import geopandas as gpd
    import networkx as nx
    from shapely.geometry import Point
except ImportError:  # pragma: no cover
    gpd = None
    nx = None
    Point = None


logger = logging.getLogger(__name__)

CentralityMethod = Literal["degree", "betweenness", "closeness", "eigenvector"]


def compute_subgraph_centroid(
    zone_id: str,
    zone_geom: Any,
    gdf_nodes: Any,
    gdf_edges: Any,
    method: CentralityMethod = "degree",
) -> Dict[str, Any]:
    """Calcula el nodo centroide representativo de una zona usando análisis de subred.

    Reglas:
    1. Filtrar nodos dentro del polígono de la zona.
    2. Construir subgrafo con edges que intersectan la zona.
    3. Calcular centralidad según método (degree, betweenness, closeness, eigenvector).
    4. Seleccionar el nodo con mayor centralidad como centroide.

    Args:
        zone_id: Identificador único de la zona.
        zone_geom: Geometría (Polygon/MultiPolygon) de la zona.
        gdf_nodes: GeoDataFrame con nodos de la red (requiere columnas: node_id, geometry).
        gdf_edges: GeoDataFrame con arcos de la red (requiere columnas: from_node, to_node, geometry).
        method: Método de centralidad a usar.

    Returns:
        Dict con:
            - zone_id: ID de la zona
            - centroid_node_id: ID del nodo centroide
            - x: Longitud del centroide
            - y: Latitud del centroide
            - centrality: Score de centralidad
            - method: Método usado
            - nodes_in_zone: Número de nodos en la zona
    """
    if gpd is None or nx is None:
        raise ImportError("GeoPandas y NetworkX son requeridos para cálculo de centroides")

    # Filtrar nodos dentro de la zona
    nodes_in_zone = gdf_nodes[gdf_nodes.geometry.within(zone_geom)].copy()

    if nodes_in_zone.empty:
        logger.warning("Zona %s no tiene nodos, usando centroide geométrico", zone_id)
        centroid_point = zone_geom.centroid
        return {
            "zone_id": zone_id,
            "centroid_node_id": None,
            "x": centroid_point.x,
            "y": centroid_point.y,
            "centrality": 0.0,
            "method": "geometric_fallback",
            "nodes_in_zone": 0,
        }

    # Filtrar edges que intersectan la zona
    edges_in_zone = gdf_edges[gdf_edges.geometry.intersects(zone_geom)].copy()

    if edges_in_zone.empty:
        logger.warning("Zona %s no tiene edges, usando primer nodo como centroide", zone_id)
        first_node = nodes_in_zone.iloc[0]
        node_id = first_node.get("node_id", first_node.name)
        return {
            "zone_id": zone_id,
            "centroid_node_id": node_id,
            "x": first_node.geometry.x,
            "y": first_node.geometry.y,
            "centrality": 0.0,
            "method": "single_node_fallback",
            "nodes_in_zone": len(nodes_in_zone),
        }

    # Construir subgrafo
    G = nx.DiGraph()

    # Agregar nodos
    for idx, node in nodes_in_zone.iterrows():
        node_id = node.get("node_id", idx)
        G.add_node(node_id, x=node.geometry.x, y=node.geometry.y)

    # Agregar edges
    for idx, edge in edges_in_zone.iterrows():
        from_node = edge.get("from_node", edge.get("u", edge.get("source")))
        to_node = edge.get("to_node", edge.get("v", edge.get("target")))
        if from_node in G.nodes and to_node in G.nodes:
            length = edge.get("length", edge.geometry.length if hasattr(edge.geometry, "length") else 1.0)
            G.add_edge(from_node, to_node, length=length)

    if G.number_of_nodes() == 0:
        logger.error("Zona %s: subgrafo sin nodos válidos", zone_id)
        centroid_point = zone_geom.centroid
        return {
            "zone_id": zone_id,
            "centroid_node_id": None,
            "x": centroid_point.x,
            "y": centroid_point.y,
            "centrality": 0.0,
            "method": "error_fallback",
            "nodes_in_zone": len(nodes_in_zone),
        }

    # Calcular centralidad
    try:
        if method == "degree":
            centrality = dict(G.degree())
        elif method == "betweenness":
            centrality = nx.betweenness_centrality(G, weight="length")
        elif method == "closeness":
            centrality = nx.closeness_centrality(G, distance="length")
        elif method == "eigenvector":
            try:
                centrality = nx.eigenvector_centrality(G, weight="length", max_iter=100)
            except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
                logger.warning("Eigenvector centrality falló para zona %s, usando degree", zone_id)
                centrality = dict(G.degree())
                method = "degree"
        else:
            raise ValueError(f"Método de centralidad no soportado: {method}")

        # Seleccionar nodo con mayor centralidad
        best_node_id = max(centrality, key=centrality.get)
        best_centrality = centrality[best_node_id]

        # Obtener coordenadas del nodo
        node_data = G.nodes[best_node_id]
        x, y = node_data["x"], node_data["y"]

        logger.info(
            "Zona %s: centroide=%s, centralidad=%.4f, método=%s, nodos=%d",
            zone_id,
            best_node_id,
            best_centrality,
            method,
            len(nodes_in_zone),
        )

        return {
            "zone_id": zone_id,
            "centroid_node_id": best_node_id,
            "x": x,
            "y": y,
            "centrality": float(best_centrality),
            "method": method,
            "nodes_in_zone": len(nodes_in_zone),
        }

    except Exception as exc:
        logger.error("Error calculando centralidad para zona %s: %s", zone_id, exc)
        first_node = nodes_in_zone.iloc[0]
        node_id = first_node.get("node_id", first_node.name)
        return {
            "zone_id": zone_id,
            "centroid_node_id": node_id,
            "x": first_node.geometry.x,
            "y": first_node.geometry.y,
            "centrality": 0.0,
            "method": "error_fallback",
            "nodes_in_zone": len(nodes_in_zone),
        }


def compute_all_zone_centroids(
    zonas_gdf: Any,
    gdf_nodes: Any,
    gdf_edges: Any,
    method: CentralityMethod = "degree",
) -> Any:
    """Itera sobre todas las zonas y calcula centroides por subred.

    Args:
        zonas_gdf: GeoDataFrame con zonas (requiere columnas: zone_id o name, geometry).
        gdf_nodes: GeoDataFrame con nodos de la red.
        gdf_edges: GeoDataFrame con arcos de la red.
        method: Método de centralidad.

    Returns:
        GeoDataFrame con columnas:
            - zone_id
            - centroid_node_id
            - geometry (Point del centroide)
            - centrality
            - method
            - nodes_in_zone
    """
    if gpd is None:
        raise ImportError("GeoPandas requerido para compute_all_zone_centroids")

    results: List[Dict[str, Any]] = []

    for idx, zone in zonas_gdf.iterrows():
        zone_id = zone.get("zone_id", zone.get("name", zone.get("id", idx)))
        zone_geom = zone.geometry

        centroid_data = compute_subgraph_centroid(
            zone_id=str(zone_id),
            zone_geom=zone_geom,
            gdf_nodes=gdf_nodes,
            gdf_edges=gdf_edges,
            method=method,
        )

        results.append(centroid_data)

    # Crear GeoDataFrame
    df = pd.DataFrame(results)
    geometry = [Point(row["x"], row["y"]) for _, row in df.iterrows()]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=zonas_gdf.crs)

    logger.info("Calculados %d centroides usando método %s", len(gdf), method)

    return gdf


def save_centroids(gdf_centroids: Any, output_path: Path) -> None:
    """Guarda centroides a archivo GeoPackage."""
    if gpd is None:
        raise ImportError("GeoPandas requerido para save_centroids")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf_centroids.to_file(output_path, driver="GPKG", layer="centroids")
    logger.info("Centroides guardados en %s", output_path)


def load_centroids(input_path: Path) -> Any:
    """Carga centroides desde archivo GeoPackage."""
    if gpd is None:
        raise ImportError("GeoPandas requerido para load_centroids")

    if not input_path.exists():
        raise FileNotFoundError(f"Archivo de centroides no encontrado: {input_path}")

    gdf = gpd.read_file(input_path, layer="centroids")
    logger.info("Centroides cargados desde %s: %d registros", input_path, len(gdf))
    return gdf
