"""
Utilidades geográficas para KIDO-Ruteo.

Funciones auxiliares para operaciones geoespaciales.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
from typing import Tuple, List, Optional
import numpy as np


def calculate_centroid(geometry) -> Point:
    """
    Calcula el centroide de una geometría.
    
    Args:
        geometry: Geometría de Shapely
        
    Returns:
        Punto representando el centroide
    """
    return geometry.centroid


def compute_distance(point1: Point, point2: Point) -> float:
    """
    Calcula distancia euclidiana entre dos puntos.
    
    Args:
        point1: Primer punto
        point2: Segundo punto
        
    Returns:
        Distancia en unidades del CRS
    """
    return point1.distance(point2)


def create_line_between_points(origin: Point, destination: Point) -> LineString:
    """
    Crea una línea recta entre dos puntos.
    
    Args:
        origin: Punto de origen
        destination: Punto de destino
        
    Returns:
        LineString conectando los puntos
    """
    return LineString([origin, destination])


def check_adjacency(geom1, geom2) -> bool:
    """
    Verifica si dos geometrías son adyacentes (se tocan).
    
    Args:
        geom1: Primera geometría
        geom2: Segunda geometría
        
    Returns:
        True si son adyacentes, False en caso contrario
    """
    return geom1.touches(geom2)


def buffer_geometry(geometry, distance: float):
    """
    Crea un buffer alrededor de una geometría.
    
    Args:
        geometry: Geometría base
        distance: Distancia del buffer
        
    Returns:
        Geometría con buffer aplicado
    """
    return geometry.buffer(distance)


def find_nearest_zone(
    point: Point,
    zones: gpd.GeoDataFrame,
    zone_id_col: str = 'id'
) -> Optional[int]:
    """
    Encuentra la zona más cercana a un punto dado.
    
    Args:
        point: Punto de consulta
        zones: GeoDataFrame con zonas
        zone_id_col: Nombre de columna con IDs de zona
        
    Returns:
        ID de la zona más cercana, o None si no se encuentra
    """
    if len(zones) == 0:
        return None
    
    # Calcular distancias
    zones['_temp_dist'] = zones.geometry.distance(point)
    
    # Encontrar mínima distancia
    nearest_idx = zones['_temp_dist'].idxmin()
    nearest_zone_id = zones.loc[nearest_idx, zone_id_col]
    
    # Limpiar columna temporal
    zones.drop(columns=['_temp_dist'], inplace=True)
    
    return nearest_zone_id


def reproject_gdf(
    gdf: gpd.GeoDataFrame,
    target_crs: str = "EPSG:4326"
) -> gpd.GeoDataFrame:
    """
    Reproyecta un GeoDataFrame a un CRS objetivo.
    
    Args:
        gdf: GeoDataFrame a reproyectar
        target_crs: CRS objetivo (default: WGS84)
        
    Returns:
        GeoDataFrame reproyectado
    """
    if gdf.crs is None:
        print("⚠️  GeoDataFrame sin CRS definido, asumiendo EPSG:4326")
        gdf.set_crs("EPSG:4326", inplace=True)
    
    if gdf.crs.to_string() != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    return gdf


def validate_geometries(gdf: gpd.GeoDataFrame) -> Tuple[int, List[int]]:
    """
    Valida geometrías en un GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame a validar
        
    Returns:
        Tupla (número_válidas, índices_inválidas)
    """
    invalid_indices = []
    
    for idx, row in gdf.iterrows():
        if not row.geometry.is_valid:
            invalid_indices.append(idx)
    
    num_valid = len(gdf) - len(invalid_indices)
    
    return num_valid, invalid_indices


def compute_area(geometry) -> float:
    """
    Calcula el área de una geometría.
    
    Args:
        geometry: Geometría de Shapely
        
    Returns:
        Área en unidades del CRS al cuadrado
    """
    return geometry.area


def compute_perimeter(geometry) -> float:
    """
    Calcula el perímetro de una geometría.
    
    Args:
        geometry: Geometría de Shapely
        
    Returns:
        Perímetro en unidades del CRS
    """
    return geometry.length
