"""
Módulo de carga de grafos de red vial.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
import os
import logging

logger = logging.getLogger(__name__)

def load_graph_from_geojson(geojson_path: str) -> nx.Graph:
    """
    Carga un grafo desde un archivo GeoJSON de red vial.
    
    Args:
        geojson_path: Ruta al archivo GeoJSON
        
    Returns:
        Grafo de NetworkX
    """
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"No se encontró el archivo de red: {geojson_path}")
        
    red_gdf = gpd.read_file(geojson_path)
    
    # Proyectar a UTM (metros) si es geográfico
    if red_gdf.crs and red_gdf.crs.is_geographic:
        try:
            utm_crs = red_gdf.estimate_utm_crs()
            red_gdf = red_gdf.to_crs(utm_crs)
            logger.info(f"Red reproyectada a {utm_crs} para cálculo de distancias en metros.")
        except Exception as e:
            logger.warning(f"No se pudo reproyectar la red: {e}. Las distancias podrían estar en grados.")
            
    return build_network_graph(red_gdf)

def download_graph_from_bbox(north: float, south: float, east: float, west: float, network_type: str = 'drive') -> nx.Graph:
    """
    Descarga el grafo de red vial desde OpenStreetMap usando un Bounding Box.
    
    Args:
        north: Latitud norte
        south: Latitud sur
        east: Longitud este
        west: Longitud oeste
        network_type: Tipo de red ('drive', 'walk', etc.)
        
    Returns:
        Grafo de NetworkX
    """
    logger.info(f"Descargando red vial de OSM (bbox: {north}, {south}, {east}, {west})...")
    G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type=network_type)
    logger.info(f"Grafo descargado: {len(G.nodes)} nodos, {len(G.edges)} aristas.")
    return G

def save_graph_to_geojson(G: nx.Graph, output_path: str):
    """
    Guarda el grafo como GeoJSON (nodos y aristas).
    Nota: OSMnx guarda graphml por defecto, pero aquí convertimos a gdf para geojson.
    """
    # Convertir a GeoDataFrames
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
    
    # Guardar aristas (que es lo que usa build_network_graph usualmente)
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdf_edges.to_file(output_path, driver='GeoJSON')
    logger.info(f"Red guardada en: {output_path}")

def build_network_graph(red_gdf: gpd.GeoDataFrame) -> nx.Graph:
    """
    Construye grafo de red vial desde GeoDataFrame.
    
    Args:
        red_gdf: GeoDataFrame con red vial
        
    Returns:
        Grafo de NetworkX
    """
    G = nx.Graph()
    # Guardar CRS si existe
    if hasattr(red_gdf, 'crs'):
        G.graph['crs'] = red_gdf.crs
    
    for idx, row in red_gdf.iterrows():
        geom = row.geometry
        
        # Extraer nodos de la geometría (LineString)
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            
            # Agregar nodos
            for coord in coords:
                node_id = f"{coord[0]:.6f},{coord[1]:.6f}"
                if not G.has_node(node_id):
                    G.add_node(node_id, pos=coord)
            
            # Agregar aristas entre nodos consecutivos
            for i in range(len(coords) - 1):
                node_i = f"{coords[i][0]:.6f},{coords[i][1]:.6f}"
                node_j = f"{coords[i+1][0]:.6f},{coords[i+1][1]:.6f}"
                
                # Calcular peso (distancia euclidiana)
                dist = ((coords[i][0] - coords[i+1][0])**2 + 
                       (coords[i][1] - coords[i+1][1])**2)**0.5
                
                G.add_edge(node_i, node_j, weight=dist)
    
    return G
