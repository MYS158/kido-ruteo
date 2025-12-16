"""
Módulo de carga de grafos de red vial.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
import os

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
    return build_network_graph(red_gdf)

def build_network_graph(red_gdf: gpd.GeoDataFrame) -> nx.Graph:
    """
    Construye grafo de red vial desde GeoDataFrame.
    
    Args:
        red_gdf: GeoDataFrame con red vial
        
    Returns:
        Grafo de NetworkX
    """
    G = nx.Graph()
    
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
