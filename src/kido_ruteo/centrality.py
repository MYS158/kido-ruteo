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


def compute_all_centralities(red_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Calcula todas las métricas de centralidad para la red vial.
    
    Args:
        red_gdf: GeoDataFrame con red vial
        
    Returns:
        DataFrame con node_id y scores de centralidad
    """
    print("=" * 60)
    print("PASO 2A: Cálculo de Centralidad de Nodos")
    print("=" * 60)
    
    # Construir grafo
    print("Construyendo grafo de red vial...")
    G = build_network_graph(red_gdf)
    print(f"  ✓ Grafo construido: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    
    # Calcular centralidades
    betweenness = compute_betweenness_centrality(G)
    closeness = compute_closeness_centrality(G)
    degree = compute_degree_centrality(G)
    
    # Convertir a DataFrame
    centrality_data = []
    for node_id in G.nodes():
        pos = G.nodes[node_id]['pos']
        centrality_data.append({
            'node_id': node_id,
            'x': pos[0],
            'y': pos[1],
            'betweenness': betweenness.get(node_id, 0),
            'closeness': closeness.get(node_id, 0),
            'degree': degree.get(node_id, 0)
        })
    
    df_centrality = pd.DataFrame(centrality_data)
    
    print(f"\n✓ Centralidades calculadas para {len(df_centrality)} nodos")
    print(f"  - Betweenness: [{df_centrality['betweenness'].min():.4f}, {df_centrality['betweenness'].max():.4f}]")
    print(f"  - Closeness: [{df_centrality['closeness'].min():.4f}, {df_centrality['closeness'].max():.4f}]")
    print(f"  - Degree: [{df_centrality['degree'].min():.4f}, {df_centrality['degree'].max():.4f}]")
    
    return df_centrality
