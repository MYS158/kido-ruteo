"""
Paso 2b del flujo KIDO: Selección de centroides por zona.

En cada zona, elige como centroide el nodo con mayor centralidad.
Genera coordenadas x-o, y-o, x-d, y-d.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Tuple


def assign_nodes_to_zones(
    df_centrality: pd.DataFrame,
    zones_gdf: gpd.GeoDataFrame,
    zone_id_col: str = 'zone_id'
) -> pd.DataFrame:
    """
    Asigna cada nodo a su zona correspondiente.
    
    Args:
        df_centrality: DataFrame con nodos y centralidades
        zones_gdf: GeoDataFrame con zonas
        zone_id_col: Nombre de columna con ID de zona
        
    Returns:
        DataFrame con nodos y zone_id asignado
    """
    print("  Asignando nodos a zonas...")
    
    df_centrality = df_centrality.copy()
    df_centrality['zone_id'] = None
    
    # Crear GeoDataFrame de nodos
    geometry = [Point(row['x'], row['y']) for _, row in df_centrality.iterrows()]
    nodes_gdf = gpd.GeoDataFrame(df_centrality, geometry=geometry, crs=zones_gdf.crs)
    
    # Spatial join
    nodes_with_zones = gpd.sjoin(nodes_gdf, zones_gdf[[zone_id_col, 'geometry']], 
                                   how='left', predicate='within')
    
    df_centrality['zone_id'] = nodes_with_zones[zone_id_col]
    
    assigned = df_centrality['zone_id'].notna().sum()
    print(f"    ✓ {assigned}/{len(df_centrality)} nodos asignados a zonas")
    
    return df_centrality


def select_zone_centroids(
    df_nodes_with_zones: pd.DataFrame,
    metric: str = 'betweenness'
) -> pd.DataFrame:
    """
    Selecciona el centroide de cada zona (nodo con mayor centralidad).
    
    Args:
        df_nodes_with_zones: DataFrame con nodos, zonas y centralidades
        metric: Métrica de centralidad a usar ('betweenness', 'closeness', 'degree')
        
    Returns:
        DataFrame con centroides seleccionados por zona
    """
    print(f"  Seleccionando centroides por zona (métrica: {metric})...")
    
    # Eliminar nodos sin zona asignada
    df_valid = df_nodes_with_zones[df_nodes_with_zones['zone_id'].notna()].copy()
    
    # Seleccionar nodo con máxima centralidad por zona
    idx_max = df_valid.groupby('zone_id')[metric].idxmax()
    centroids = df_valid.loc[idx_max].copy()
    
    centroids = centroids.rename(columns={
        'x': 'centroid_x',
        'y': 'centroid_y',
        metric: 'centrality_score'
    })
    
    print(f"    ✓ {len(centroids)} centroides seleccionados")
    
    return centroids[['zone_id', 'node_id', 'centroid_x', 'centroid_y', 'centrality_score']]


def add_centroid_coordinates_to_od(
    df_od: pd.DataFrame,
    df_centroids: pd.DataFrame,
    origin_col: str = 'origin_id',
    dest_col: str = 'destination_id'
) -> pd.DataFrame:
    """
    Añade coordenadas de centroides (x-o, y-o, x-d, y-d) a datos OD.
    
    Args:
        df_od: DataFrame con datos OD
        df_centroids: DataFrame con centroides por zona
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame OD con coordenadas de centroides añadidas
    """
    print("  Añadiendo coordenadas de centroides a datos OD...")
    
    df_od = df_od.copy()
    
    # Merge para origen
    df_od = df_od.merge(
        df_centroids[['zone_id', 'centroid_x', 'centroid_y', 'node_id']],
        left_on=origin_col,
        right_on='zone_id',
        how='left',
        suffixes=('', '_origin')
    )
    df_od = df_od.rename(columns={
        'centroid_x': 'x_o',
        'centroid_y': 'y_o',
        'node_id': 'origin_node_id'
    })
    df_od = df_od.drop(columns=['zone_id'], errors='ignore')
    
    # Merge para destino
    df_od = df_od.merge(
        df_centroids[['zone_id', 'centroid_x', 'centroid_y', 'node_id']],
        left_on=dest_col,
        right_on='zone_id',
        how='left',
        suffixes=('', '_dest')
    )
    df_od = df_od.rename(columns={
        'centroid_x': 'x_d',
        'centroid_y': 'y_d',
        'node_id': 'destination_node_id'
    })
    df_od = df_od.drop(columns=['zone_id'], errors='ignore')
    
    # Verificar asignación
    assigned_origins = df_od['x_o'].notna().sum()
    assigned_dests = df_od['x_d'].notna().sum()
    
    print(f"    ✓ Orígenes con centroide: {assigned_origins}/{len(df_od)}")
    print(f"    ✓ Destinos con centroide: {assigned_dests}/{len(df_od)}")
    
    return df_od


def compute_centroids(
    df_od: pd.DataFrame,
    df_centrality: pd.DataFrame,
    zones_gdf: gpd.GeoDataFrame,
    origin_col: str = 'origin_id',
    dest_col: str = 'destination_id',
    zone_id_col: str = 'zone_id',
    metric: str = 'betweenness'
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta proceso completo de selección de centroides (Paso 2B KIDO).
    
    Args:
        df_od: DataFrame con datos OD
        df_centrality: DataFrame con centralidades de nodos
        zones_gdf: GeoDataFrame con zonas
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        zone_id_col: Nombre de columna de ID de zona
        metric: Métrica de centralidad para selección
        
    Returns:
        Tupla (df_od_with_coords, df_centroids)
    """
    print("=" * 60)
    print("PASO 2B: Selección de Centroides")
    print("=" * 60)
    
    # Asignar nodos a zonas
    df_nodes_with_zones = assign_nodes_to_zones(df_centrality, zones_gdf, zone_id_col)
    
    # Seleccionar centroides
    df_centroids = select_zone_centroids(df_nodes_with_zones, metric)
    
    # Añadir coordenadas a datos OD
    df_od_with_coords = add_centroid_coordinates_to_od(df_od, df_centroids, origin_col, dest_col)
    
    print(f"\n✓ Proceso completado")
    
    return df_od_with_coords, df_centroids
