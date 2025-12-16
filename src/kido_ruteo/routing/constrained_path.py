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
    checkpoint_node: str
) -> Tuple[Optional[List[str]], Optional[float]]:
    """
    Calcula shortest path que DEBE pasar por un checkpoint específico.
    
    Args:
        G: Grafo de red vial
        origin_node: Nodo origen
        dest_node: Nodo destino
        checkpoint_node: Nodo checkpoint (obligatorio)
        
    Returns:
        Tupla (path, distance) o (None, None) si no hay ruta
    """
    try:
        # Ruta origen -> checkpoint
        path1 = nx.shortest_path(G, source=origin_node, target=checkpoint_node, weight='weight')
        dist1 = nx.shortest_path_length(G, source=origin_node, target=checkpoint_node, weight='weight')
        
        # Ruta checkpoint -> destino
        path2 = nx.shortest_path(G, source=checkpoint_node, target=dest_node, weight='weight')
        dist2 = nx.shortest_path_length(G, source=checkpoint_node, target=dest_node, weight='weight')
        
        # Combinar rutas (evitar duplicar checkpoint)
        combined_path = path1 + path2[1:]
        combined_distance = dist1 + dist2
        
        return combined_path, combined_distance
    
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, None

def compute_mc2_matrix(
    df_od: pd.DataFrame,
    G: nx.Graph,
    checkpoint_col: str = 'checkpoint_id',
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id'
) -> pd.DataFrame:
    """
    Calcula matriz de impedancia MC2 para todos los pares OD.
    Usa el checkpoint específico de cada fila.
    
    Args:
        df_od: DataFrame con pares OD
        G: Grafo de red vial
        checkpoint_col: Columna con el ID del checkpoint
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        
    Returns:
        DataFrame con columnas dist_mc2, path_mc2 agregadas
    """
    print("  Calculando matriz MC2 (Constrained Path)...")
    
    # Listas para resultados
    dist_mc2 = []
    path_mc2 = []
    
    # Iterar sobre el DataFrame
    # Usamos tqdm para barra de progreso
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od)):
        origin = row.get(origin_node_col)
        dest = row.get(dest_node_col)
        checkpoint = row.get(checkpoint_col)
        
        # Validar datos necesarios
        if pd.isna(origin) or pd.isna(dest) or pd.isna(checkpoint):
            dist_mc2.append(None)
            path_mc2.append(None)
            continue
            
        # Asegurar que checkpoint sea string (si los nodos del grafo son strings)
        checkpoint = str(checkpoint)
        
        # Calcular ruta
        path, dist = compute_constrained_shortest_path(G, origin, dest, checkpoint)
        
        dist_mc2.append(dist)
        path_mc2.append(str(path) if path else None)
        
    # Asignar resultados al DataFrame
    df_od['mc2_distance_m'] = dist_mc2
    # df_od['mc2_path'] = path_mc2 # Opcional, si se requiere el path
        
    return df_od
