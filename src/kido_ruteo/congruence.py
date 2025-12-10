"""
Módulo de congruencia para KIDO-Ruteo.

Funciones para calcular métricas E1 y E2 de congruencia de viajes.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, Tuple, Optional
from shapely.geometry import Point


def compute_e1_score(
    route_length: float,
    straight_distance: float
) -> float:
    """
    Calcula métrica E1: desviación de ruta respecto a línea recta.
    
    E1 = (longitud_ruta - distancia_recta) / distancia_recta
    
    Args:
        route_length: Longitud de la ruta calculada
        straight_distance: Distancia en línea recta
        
    Returns:
        Score E1 (valores más cercanos a 0 son mejores)
    """
    if straight_distance == 0:
        return 0.0
    
    return (route_length - straight_distance) / straight_distance


def compute_e1_for_routes(
    routes: pd.DataFrame,
    zones: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Calcula E1 para todas las rutas.
    
    Args:
        routes: DataFrame con rutas calculadas
        zones: GeoDataFrame con zonas y centroides
        
    Returns:
        DataFrame con scores E1 añadidos
    """
    # Crear mapeo de zonas a centroides
    zone_centroids = {}
    for idx, row in zones.iterrows():
        zone_id = row.get('id', row.get('zone_id', idx))
        zone_centroids[zone_id] = row.geometry.centroid
    
    e1_scores = []
    
    for idx, route in routes.iterrows():
        origin = route['origin']
        destination = route['destination']
        route_length = route.get('path_length')
        
        if route_length is None or origin not in zone_centroids or destination not in zone_centroids:
            e1_scores.append(None)
            continue
        
        # Calcular distancia en línea recta
        straight_dist = zone_centroids[origin].distance(zone_centroids[destination])
        
        # Calcular E1
        e1 = compute_e1_score(route_length, straight_dist)
        e1_scores.append(e1)
    
    routes = routes.copy()
    routes['e1_score'] = e1_scores
    routes['e1_category'] = pd.cut(
        routes['e1_score'],
        bins=[-np.inf, 0.2, 0.5, 1.0, np.inf],
        labels=['Excelente', 'Bueno', 'Regular', 'Malo']
    )
    
    return routes


def compute_e2_score(
    trips: float,
    route_length: float
) -> float:
    """
    Calcula métrica E2: eficiencia de flujo en la ruta.
    
    E2 = viajes / longitud_ruta
    
    Args:
        trips: Número de viajes observados
        route_length: Longitud de la ruta
        
    Returns:
        Score E2 (valores más altos indican mayor eficiencia)
    """
    if route_length == 0 or pd.isna(route_length):
        return 0.0
    
    return trips / route_length


def compute_e2_for_routes(
    routes: pd.DataFrame,
    od_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula E2 para todas las rutas.
    
    Args:
        routes: DataFrame con rutas calculadas
        od_data: DataFrame con datos OD incluyendo viajes
        
    Returns:
        DataFrame con scores E2 añadidos
    """
    # Identificar columna de viajes
    trips_col = None
    for col in ['viajes', 'trips', 'flujo', 'flow']:
        if col in od_data.columns:
            trips_col = col
            break
    
    if trips_col is None:
        raise ValueError("No se encontró columna de viajes en od_data")
    
    # Merge routes con od_data
    merged = routes.merge(
        od_data,
        left_on=['origin', 'destination'],
        right_on=['origen', 'destino'],
        how='left'
    )
    
    # Calcular E2
    e2_scores = []
    for idx, row in merged.iterrows():
        trips = row.get(trips_col)
        route_length = row.get('path_length')
        
        if pd.isna(trips) or pd.isna(route_length):
            e2_scores.append(None)
        else:
            e2 = compute_e2_score(trips, route_length)
            e2_scores.append(e2)
    
    merged['e2_score'] = e2_scores
    
    return merged


def classify_congruence(
    e1_score: Optional[float],
    e2_score: Optional[float],
    e1_thresholds: Tuple[float, float] = (0.3, 0.7),
    e2_thresholds: Tuple[float, float] = (10, 50)
) -> str:
    """
    Clasifica la congruencia de una ruta basándose en E1 y E2.
    
    Args:
        e1_score: Score E1 (desviación de ruta)
        e2_score: Score E2 (eficiencia de flujo)
        e1_thresholds: Umbrales (bajo, alto) para E1
        e2_thresholds: Umbrales (bajo, alto) para E2
        
    Returns:
        Clasificación: 'Alta', 'Media', 'Baja', 'Indeterminada'
    """
    if e1_score is None or e2_score is None:
        return 'Indeterminada'
    
    e1_low, e1_high = e1_thresholds
    e2_low, e2_high = e2_thresholds
    
    # E1 bajo (bueno) y E2 alto (bueno) = Congruencia Alta
    if e1_score < e1_low and e2_score > e2_high:
        return 'Alta'
    
    # E1 alto (malo) o E2 bajo (malo) = Congruencia Baja
    elif e1_score > e1_high or e2_score < e2_low:
        return 'Baja'
    
    # Casos intermedios
    else:
        return 'Media'


def generate_congruence_report(
    routes: pd.DataFrame,
    zones: gpd.GeoDataFrame,
    od_data: pd.DataFrame
) -> pd.DataFrame:
    """
    Genera reporte completo de congruencia con E1 y E2.
    
    Args:
        routes: DataFrame con rutas calculadas
        zones: GeoDataFrame con zonas
        od_data: DataFrame con datos OD
        
    Returns:
        DataFrame con reporte de congruencia
    """
    # Calcular E1
    routes_with_e1 = compute_e1_for_routes(routes, zones)
    
    # Calcular E2
    routes_with_e2 = compute_e2_for_routes(routes_with_e1, od_data)
    
    # Clasificar congruencia
    routes_with_e2['congruence_class'] = routes_with_e2.apply(
        lambda row: classify_congruence(row['e1_score'], row['e2_score']),
        axis=1
    )
    
    return routes_with_e2


def compute_aggregate_statistics(
    congruence_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Calcula estadísticas agregadas de congruencia.
    
    Args:
        congruence_df: DataFrame con scores de congruencia
        
    Returns:
        Diccionario con estadísticas
    """
    stats = {
        'mean_e1': congruence_df['e1_score'].mean(),
        'median_e1': congruence_df['e1_score'].median(),
        'std_e1': congruence_df['e1_score'].std(),
        'mean_e2': congruence_df['e2_score'].mean(),
        'median_e2': congruence_df['e2_score'].median(),
        'std_e2': congruence_df['e2_score'].std(),
        'pct_high_congruence': (congruence_df['congruence_class'] == 'Alta').sum() / len(congruence_df) * 100,
        'pct_medium_congruence': (congruence_df['congruence_class'] == 'Media').sum() / len(congruence_df) * 100,
        'pct_low_congruence': (congruence_df['congruence_class'] == 'Baja').sum() / len(congruence_df) * 100
    }
    
    return stats
