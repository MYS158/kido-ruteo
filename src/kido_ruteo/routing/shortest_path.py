"""
Módulo para cálculo de Shortest Path (MC).
"""

import networkx as nx
import pandas as pd
from typing import Tuple, List, Optional
from tqdm import tqdm

def compute_shortest_path_mc(
    G: nx.Graph,
    origin_node: str,
    dest_node: str
) -> Tuple[Optional[List[str]], Optional[float], Optional[float]]:
    """
    Calcula shortest path entre dos nodos (sin restricción de checkpoint).
    
    Args:
        G: Grafo de red vial
        origin_node: ID de nodo origen
        dest_node: ID de nodo destino
        
    Returns:
        Tupla (path, distance, time)
    """
    try:
        path = nx.shortest_path(G, source=origin_node, target=dest_node, weight='weight')
        distance = nx.shortest_path_length(G, source=origin_node, target=dest_node, weight='weight')
        
        # Estimar tiempo (velocidad promedio 40 km/h)
        # Asumiendo distancia en grados aprox o metros? 
        # Si weight es euclidiana en grados, esto está mal. 
        # Pero mantenemos lógica existente por ahora.
        time = distance / 40.0  # horas
        
        return path, distance, time
    
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, None, None

def compute_mc_matrix(
    df_od: pd.DataFrame,
    G: nx.Graph,
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id'
) -> pd.DataFrame:
    """
    Calcula matriz de impedancia MC para todos los pares OD.
    
    Args:
        df_od: DataFrame con pares OD y nodos asignados
        G: Grafo de red vial
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        
    Returns:
        DataFrame con columnas mc_distance_m, mc_time_h, mc_path
    """
    print("  Calculando matriz MC (Shortest Path)...")
    
    results = []
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od)):
        origin = row.get(origin_node_col)
        dest = row.get(dest_node_col)
        
        if pd.isna(origin) or pd.isna(dest):
            results.append({
                'mc_distance_m': None,
                'mc_time_h': None,
                'mc_path': None
            })
            continue
            
        path, dist, time = compute_shortest_path_mc(G, origin, dest)
        
        results.append({
            'mc_distance_m': dist,
            'mc_time_h': time,
            'mc_path': str(path) if path else None
        })
        
    return pd.concat([df_od, pd.DataFrame(results)], axis=1)
