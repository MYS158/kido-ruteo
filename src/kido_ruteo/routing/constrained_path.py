"""
Módulo para cálculo de Constrained Shortest Path (MC2).
"""

import networkx as nx
import pandas as pd
from typing import List, Tuple, Optional
from tqdm import tqdm

def compute_constrained_shortest_path(
    G: nx.Graph,
    origin_node: str,
    dest_node: str,
    checkpoint_nodes: List[str]
) -> Tuple[Optional[List[str]], Optional[float]]:
    """
    Calcula shortest path que DEBE pasar por algún checkpoint.
    
    Estrategia: Para cada checkpoint, calcular origen->checkpoint->destino
    y seleccionar la ruta más corta.
    
    Args:
        G: Grafo de red vial
        origin_node: Nodo origen
        dest_node: Nodo destino
        checkpoint_nodes: Lista de nodos checkpoint
        
    Returns:
        Tupla (path, distance) o (None, None) si no hay ruta
    """
    best_path = None
    best_distance = float('inf')
    
    for checkpoint in checkpoint_nodes:
        try:
            # Ruta origen -> checkpoint
            path1 = nx.shortest_path(G, source=origin_node, target=checkpoint, weight='weight')
            dist1 = nx.shortest_path_length(G, source=origin_node, target=checkpoint, weight='weight')
            
            # Ruta checkpoint -> destino
            path2 = nx.shortest_path(G, source=checkpoint, target=dest_node, weight='weight')
            dist2 = nx.shortest_path_length(G, source=checkpoint, target=dest_node, weight='weight')
            
            # Combinar rutas (evitar duplicar checkpoint)
            combined_path = path1 + path2[1:]
            combined_distance = dist1 + dist2
            
            if combined_distance < best_distance:
                best_distance = combined_distance
                best_path = combined_path
        
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue
    
    if best_path is not None:
        return best_path, best_distance
    else:
        return None, None

def compute_mc2_matrix(
    df_od: pd.DataFrame,
    G: nx.Graph,
    checkpoint_nodes: List[str],
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id'
) -> pd.DataFrame:
    """
    Calcula matriz de impedancia MC2 para todos los pares OD.
    
    Args:
        df_od: DataFrame con pares OD
        G: Grafo de red vial
        checkpoint_nodes: Lista de nodos checkpoint
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        
    Returns:
        DataFrame con columnas dist_mc2, path_mc2
    """
    print("  Calculando matriz MC2 (Constrained Path)...")
    
    results = []
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od)):
        origin = row.get(origin_node_col)
        dest = row.get(dest_node_col)
        
        if pd.isna(origin) or pd.isna(dest):
            results.append({
                'dist_mc2': None,
                'path_mc2': None
            })
            continue
            
        path, dist = compute_constrained_shortest_path(G, origin, dest, checkpoint_nodes)
        
        results.append({
            'dist_mc2': dist,
            'path_mc2': str(path) if path else None
        })
        
    return pd.concat([df_od, pd.DataFrame(results)], axis=1)
