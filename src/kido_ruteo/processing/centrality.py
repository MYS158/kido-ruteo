"""
Paso 2a del flujo KIDO: Cálculo de centralidad de nodos.

Calcula centralidad de nodos de la red vial para selección de centroides.
"""

import networkx as nx
import geopandas as gpd
import pandas as pd
from typing import Dict, Tuple


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


def compute_betweenness_centrality(G: nx.Graph) -> Dict[str, float]:
    """
    Calcula centralidad de intermediación (betweenness) para todos los nodos.
    
    Args:
        G: Grafo de red vial
        
    Returns:
        Diccionario {node_id: centrality_score}
    """
    print("  Calculando betweenness centrality...")
    centrality = nx.betweenness_centrality(G, weight='weight')
    return centrality


def compute_closeness_centrality(G: nx.Graph) -> Dict[str, float]:
    """
    Calcula centralidad de cercanía (closeness) para todos los nodos.
    
    Args:
        G: Grafo de red vial
        
    Returns:
        Diccionario {node_id: centrality_score}
    """
    print("  Calculando closeness centrality...")
    
    # Verificar si el grafo está conectado
    if not nx.is_connected(G):
        # Usar componente conexa más grande
        largest_cc = max(nx.connected_components(G), key=len)
        G_connected = G.subgraph(largest_cc).copy()
        centrality = nx.closeness_centrality(G_connected, distance='weight')
    else:
        centrality = nx.closeness_centrality(G, distance='weight')
    
    return centrality


def compute_degree_centrality(G: nx.Graph) -> Dict[str, float]:
    """
    Calcula centralidad de grado (degree) para todos los nodos.
    
    Args:
        G: Grafo de red vial
        
    Returns:
        Diccionario {node_id: centrality_score}
    """
    print("  Calculando degree centrality...")
    centrality = nx.degree_centrality(G)
    return centrality
