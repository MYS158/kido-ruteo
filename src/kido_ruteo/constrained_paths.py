"""
Paso 6 del flujo KIDO: Segunda Matriz de Impedancia (MC2) - Constrained Shortest Path.

Las rutas DEBEN pasar por el checkpoint.
Algoritmo: Constrained shortest path o K-shortest path.
"""

import networkx as nx
import pandas as pd
from typing import List, Tuple, Optional
from tqdm import tqdm


def find_checkpoint_nodes(
    zones_gdf,
    zone_centroids: pd.DataFrame,
    checkpoint_type: str = 'checkpoint'
) -> List[str]:
    """
    Identifica nodos que son checkpoints.
    
    Args:
        zones_gdf: GeoDataFrame con zonas (debe tener poly_type)
        zone_centroids: DataFrame con centroides
        checkpoint_type: Valor de poly_type que indica checkpoint
        
    Returns:
        Lista de node_ids de checkpoints
    """
    if 'poly_type' not in zones_gdf.columns:
        print("⚠️  Advertencia: No se encontró columna 'poly_type' en zonas")
        return []
    
    checkpoint_zones = zones_gdf[zones_gdf['poly_type'] == checkpoint_type]
    checkpoint_zone_ids = checkpoint_zones['zone_id'].tolist()
    
    checkpoint_nodes = zone_centroids[
        zone_centroids['zone_id'].isin(checkpoint_zone_ids)
    ]['node_id'].tolist()
    
    return checkpoint_nodes


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
    Calcula matriz de impedancia MC2 (constrained por checkpoint).
    
    Args:
        df_od: DataFrame con pares OD
        G: Grafo de red vial
        checkpoint_nodes: Lista de nodos checkpoint
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        
    Returns:
        DataFrame con MC2
    """
    print("  Calculando constrained shortest paths para matriz MC2...")
    print(f"  Checkpoints disponibles: {len(checkpoint_nodes)}")
    
    results = []
    
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od), desc="MC2 Constrained Path"):
        origin_node = row[origin_node_col]
        dest_node = row[dest_node_col]
        
        if pd.isna(origin_node) or pd.isna(dest_node):
            results.append({
                'origin_id': row['origin_id'],
                'destination_id': row['destination_id'],
                'mc2_path': None,
                'mc2_distance': None,
                'mc2_time': None,
                'mc2_success': False
            })
            continue
        
        path, distance = compute_constrained_shortest_path(
            G, origin_node, dest_node, checkpoint_nodes
        )
        
        # Calcular tiempo
        time = distance / 40.0 if distance is not None else None
        
        results.append({
            'origin_id': row['origin_id'],
            'destination_id': row['destination_id'],
            'mc2_path': path,
            'mc2_distance': distance,
            'mc2_time': time,
            'mc2_success': path is not None
        })
    
    df_mc2 = pd.DataFrame(results)
    
    success_rate = df_mc2['mc2_success'].sum() / len(df_mc2) * 100
    print(f"    ✓ MC2 calculada: {df_mc2['mc2_success'].sum()}/{len(df_mc2)} rutas ({success_rate:.1f}%)")
    
    return df_mc2


def compute_impedance_matrix_mc2(
    df_od: pd.DataFrame,
    G: nx.Graph,
    zones_gdf,
    zone_centroids: pd.DataFrame,
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id'
) -> pd.DataFrame:
    """
    Ejecuta proceso completo de Matriz de Impedancia MC2 (Paso 6 KIDO).
    
    Args:
        df_od: DataFrame con datos OD
        G: Grafo de red vial
        zones_gdf: GeoDataFrame con zonas
        zone_centroids: DataFrame con centroides
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        
    Returns:
        DataFrame con matriz MC2
    """
    print("=" * 60)
    print("PASO 6: Segunda Matriz de Impedancia (MC2) - Constrained Path")
    print("=" * 60)
    
    # Identificar checkpoints
    checkpoint_nodes = find_checkpoint_nodes(zones_gdf, zone_centroids)
    
    if not checkpoint_nodes:
        print("⚠️  No se encontraron checkpoints. MC2 no se puede calcular.")
        return df_od
    
    # Calcular MC2
    df_mc2 = compute_mc2_matrix(df_od, G, checkpoint_nodes, origin_node_col, dest_node_col)
    
    # Merge con datos originales
    df_od_with_mc2 = df_od.merge(df_mc2, on=['origin_id', 'destination_id'], how='left')
    
    print(f"\n✓ Matriz MC2 completada")
    
    return df_od_with_mc2
