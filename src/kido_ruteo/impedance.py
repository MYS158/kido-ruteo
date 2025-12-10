"""
Paso 5 del flujo KIDO: Matriz de Impedancia (MC) - Shortest Path.

Genera matriz OD completa con:
- Tiempo, distancia, costo
- Algoritmo: shortest path (SIN restricción de checkpoint)
- Identificador zona_menor-zona_mayor
- Rutas para 80% de viajes
"""

import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
from typing import Tuple, List
from tqdm import tqdm


def generate_complete_od_matrix(zones: List[int]) -> pd.DataFrame:
    """
    Genera matriz OD completa (todos los pares posibles).
    
    Args:
        zones: Lista de IDs de zonas
        
    Returns:
        DataFrame con todos los pares OD
    """
    od_pairs = []
    for origin in zones:
        for dest in zones:
            od_pairs.append({
                'origin_id': origin,
                'destination_id': dest
            })
    
    return pd.DataFrame(od_pairs)


def create_zone_pair_id(df: pd.DataFrame, origin_col: str = 'origin_id', dest_col: str = 'destination_id') -> pd.DataFrame:
    """
    Crea identificador zona_menor-zona_mayor.
    
    Args:
        df: DataFrame con pares OD
        origin_col: Columna de origen
        dest_col: Columna de destino
        
    Returns:
        DataFrame con columna zone_pair_id
    """
    df = df.copy()
    
    df['zone_menor'] = df[[origin_col, dest_col]].min(axis=1)
    df['zone_mayor'] = df[[origin_col, dest_col]].max(axis=1)
    df['zone_pair_id'] = df['zone_menor'].astype(str) + '-' + df['zone_mayor'].astype(str)
    
    return df


def compute_shortest_path_mc(
    G: nx.Graph,
    origin_node: str,
    dest_node: str
) -> Tuple[List[str], float, float]:
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
        DataFrame con MC (tiempo, distancia, costo)
    """
    print("  Calculando shortest paths para matriz MC...")
    
    results = []
    
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od), desc="MC Shortest Path"):
        origin_node = row[origin_node_col]
        dest_node = row[dest_node_col]
        
        if pd.isna(origin_node) or pd.isna(dest_node):
            results.append({
                'origin_id': row['origin_id'],
                'destination_id': row['destination_id'],
                'mc_path': None,
                'mc_distance': None,
                'mc_time': None,
                'mc_cost': None,
                'mc_success': False
            })
            continue
        
        path, distance, time = compute_shortest_path_mc(G, origin_node, dest_node)
        
        # Calcular costo (por ejemplo, basado en distancia)
        cost = distance * 0.5 if distance is not None else None
        
        results.append({
            'origin_id': row['origin_id'],
            'destination_id': row['destination_id'],
            'mc_path': path,
            'mc_distance': distance,
            'mc_time': time,
            'mc_cost': cost,
            'mc_success': path is not None
        })
    
    df_mc = pd.DataFrame(results)
    
    success_rate = df_mc['mc_success'].sum() / len(df_mc) * 100
    print(f"    ✓ MC calculada: {df_mc['mc_success'].sum()}/{len(df_mc)} rutas ({success_rate:.1f}%)")
    
    return df_mc


def identify_top_80_percent_trips(
    df_od_with_mc: pd.DataFrame,
    trips_col: str = 'total_trips_modif'
) -> pd.DataFrame:
    """
    Identifica pares OD que cubren el 80% de viajes totales.
    
    Args:
        df_od_with_mc: DataFrame con MC y viajes
        trips_col: Columna con número de viajes
        
    Returns:
        DataFrame con columna is_top_80
    """
    df_od_with_mc = df_od_with_mc.copy()
    
    # Ordenar por viajes descendente
    df_sorted = df_od_with_mc.sort_values(trips_col, ascending=False)
    
    # Calcular acumulado
    total_trips = df_sorted[trips_col].sum()
    df_sorted['cumsum_trips'] = df_sorted[trips_col].cumsum()
    df_sorted['cumsum_pct'] = df_sorted['cumsum_trips'] / total_trips
    
    # Marcar top 80%
    df_sorted['is_top_80'] = df_sorted['cumsum_pct'] <= 0.80
    
    # Merge de vuelta
    df_od_with_mc['is_top_80'] = False
    df_od_with_mc.loc[df_sorted.index, 'is_top_80'] = df_sorted['is_top_80']
    
    top_80_count = df_od_with_mc['is_top_80'].sum()
    print(f"  ✓ Identificados {top_80_count} pares que cubren el 80% de viajes")
    
    return df_od_with_mc


def export_routes_geojson(
    df_mc_top80: pd.DataFrame,
    G: nx.Graph,
    output_path: str = 'data/processed/rutas_mc.geojson'
) -> None:
    """
    Exporta rutas MC como GeoJSON (solo top 80%).
    
    Args:
        df_mc_top80: DataFrame con rutas MC top 80%
        G: Grafo con posiciones de nodos
        output_path: Ruta de salida
    """
    print(f"  Exportando rutas a {output_path}...")
    
    features = []
    
    for idx, row in df_mc_top80[df_mc_top80['is_top_80'] & df_mc_top80['mc_success']].iterrows():
        path = row['mc_path']
        
        if path is None or len(path) < 2:
            continue
        
        # Obtener coordenadas de nodos
        coords = [G.nodes[node]['pos'] for node in path if node in G.nodes]
        
        if len(coords) >= 2:
            geometry = LineString(coords)
            features.append({
                'origin_id': row['origin_id'],
                'destination_id': row['destination_id'],
                'mc_distance': row['mc_distance'],
                'mc_time': row['mc_time'],
                'geometry': geometry
            })
    
    gdf = gpd.GeoDataFrame(features)
    gdf.to_file(output_path, driver='GeoJSON')
    
    print(f"    ✓ {len(gdf)} rutas exportadas")


def compute_impedance_matrix_mc(
    df_od: pd.DataFrame,
    G: nx.Graph,
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id',
    trips_col: str = 'total_trips_modif'
) -> pd.DataFrame:
    """
    Ejecuta proceso completo de Matriz de Impedancia MC (Paso 5 KIDO).
    
    Args:
        df_od: DataFrame con datos OD
        G: Grafo de red vial
        origin_node_col: Columna con nodo origen
        dest_node_col: Columna con nodo destino
        trips_col: Columna con viajes
        
    Returns:
        DataFrame con matriz MC completa
    """
    print("=" * 60)
    print("PASO 5: Matriz de Impedancia (MC) - Shortest Path")
    print("=" * 60)
    
    # Crear identificador de pares
    df_od = create_zone_pair_id(df_od)
    
    # Calcular MC
    df_mc = compute_mc_matrix(df_od, G, origin_node_col, dest_node_col)
    
    # Merge con datos originales
    df_od_with_mc = df_od.merge(df_mc, on=['origin_id', 'destination_id'], how='left')
    
    # Identificar top 80%
    df_od_with_mc = identify_top_80_percent_trips(df_od_with_mc, trips_col)
    
    # Exportar rutas
    export_routes_geojson(df_od_with_mc, G)
    
    print(f"\n✓ Matriz MC completada")
    
    return df_od_with_mc
