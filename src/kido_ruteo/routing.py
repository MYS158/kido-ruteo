"""
Módulo de ruteo para KIDO-Ruteo.

Funciones para construcción de grafos y cálculo de rutas óptimas.
"""

import networkx as nx
import geopandas as gpd
import pandas as pd
from typing import List, Tuple, Optional, Dict
from shapely.geometry import Point, LineString


def build_graph_from_zones(zones: gpd.GeoDataFrame) -> nx.Graph:
    """
    Construye grafo de conectividad desde zonas geográficas.
    
    Args:
        zones: GeoDataFrame con geometrías de zonas
        
    Returns:
        Grafo de NetworkX con zonas como nodos
    """
    G = nx.Graph()
    
    # Agregar nodos (zonas)
    for idx, row in zones.iterrows():
        zone_id = row.get('id', row.get('zone_id', idx))
        centroid = row.geometry.centroid
        
        G.add_node(
            zone_id,
            pos=(centroid.x, centroid.y),
            geometry=row.geometry,
            area=row.geometry.area
        )
    
    return G


def add_adjacency_edges(G: nx.Graph, zones: gpd.GeoDataFrame) -> nx.Graph:
    """
    Agrega aristas entre zonas adyacentes en el grafo.
    
    Args:
        G: Grafo de NetworkX
        zones: GeoDataFrame con geometrías de zonas
        
    Returns:
        Grafo con aristas de adyacencia
    """
    zone_ids = list(G.nodes())
    zone_dict = {row.get('id', row.get('zone_id', idx)): row.geometry 
                 for idx, row in zones.iterrows()}
    
    for i, zone_i in enumerate(zone_ids):
        for zone_j in zone_ids[i+1:]:
            if zone_i in zone_dict and zone_j in zone_dict:
                # Verificar adyacencia
                if zone_dict[zone_i].touches(zone_dict[zone_j]):
                    # Calcular peso (distancia entre centroides)
                    centroid_i = zone_dict[zone_i].centroid
                    centroid_j = zone_dict[zone_j].centroid
                    distance = centroid_i.distance(centroid_j)
                    
                    G.add_edge(zone_i, zone_j, weight=distance)
    
    return G


def compute_shortest_path(
    G: nx.Graph,
    origin: int,
    destination: int
) -> Optional[Tuple[List[int], float]]:
    """
    Calcula la ruta más corta entre dos nodos.
    
    Args:
        G: Grafo de NetworkX
        origin: ID de nodo de origen
        destination: ID de nodo de destino
        
    Returns:
        Tupla (ruta, longitud) o None si no existe ruta
    """
    try:
        path = nx.shortest_path(G, source=origin, target=destination, weight='weight')
        length = nx.shortest_path_length(G, source=origin, target=destination, weight='weight')
        return path, length
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def compute_all_shortest_paths(
    G: nx.Graph,
    od_pairs: pd.DataFrame,
    origin_col: str = 'origen',
    dest_col: str = 'destino'
) -> pd.DataFrame:
    """
    Calcula rutas más cortas para todos los pares OD.
    
    Args:
        G: Grafo de NetworkX
        od_pairs: DataFrame con pares origen-destino
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame con rutas calculadas
    """
    results = []
    
    for idx, row in od_pairs.iterrows():
        origin = row[origin_col]
        destination = row[dest_col]
        
        path_result = compute_shortest_path(G, origin, destination)
        
        if path_result is not None:
            path, length = path_result
            results.append({
                'origin': origin,
                'destination': destination,
                'path': path,
                'path_length': length,
                'num_segments': len(path) - 1,
                'success': True
            })
        else:
            results.append({
                'origin': origin,
                'destination': destination,
                'path': None,
                'path_length': None,
                'num_segments': None,
                'success': False
            })
    
    return pd.DataFrame(results)


def compute_k_shortest_paths(
    G: nx.Graph,
    origin: int,
    destination: int,
    k: int = 3
) -> List[Tuple[List[int], float]]:
    """
    Calcula las k rutas más cortas entre dos nodos.
    
    Args:
        G: Grafo de NetworkX
        origin: ID de nodo de origen
        destination: ID de nodo de destino
        k: Número de rutas a calcular
        
    Returns:
        Lista de tuplas (ruta, longitud)
    """
    try:
        paths = list(nx.shortest_simple_paths(G, source=origin, target=destination, weight='weight'))
        
        results = []
        for path in paths[:k]:
            length = sum(G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1))
            results.append((path, length))
        
        return results
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def create_route_linestring(
    path: List[int],
    G: nx.Graph
) -> Optional[LineString]:
    """
    Crea geometría LineString para una ruta.
    
    Args:
        path: Lista de IDs de nodos en la ruta
        G: Grafo con información de posición de nodos
        
    Returns:
        LineString representando la ruta o None si no es válida
    """
    if path is None or len(path) < 2:
        return None
    
    coordinates = []
    for node_id in path:
        if node_id in G.nodes:
            pos = G.nodes[node_id]['pos']
            coordinates.append(pos)
    
    if len(coordinates) >= 2:
        return LineString(coordinates)
    else:
        return None


def compute_route_statistics(
    routes: pd.DataFrame,
    trips_data: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """
    Calcula estadísticas agregadas sobre rutas.
    
    Args:
        routes: DataFrame con rutas calculadas
        trips_data: DataFrame opcional con datos de viajes
        
    Returns:
        Diccionario con estadísticas
    """
    stats = {
        'total_routes': len(routes),
        'successful_routes': routes['success'].sum() if 'success' in routes.columns else 0,
        'mean_path_length': routes['path_length'].mean(),
        'median_path_length': routes['path_length'].median(),
        'mean_segments': routes['num_segments'].mean(),
        'max_path_length': routes['path_length'].max(),
        'min_path_length': routes['path_length'].min()
    }
    
    return stats
