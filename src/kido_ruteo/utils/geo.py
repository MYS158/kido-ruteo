"""
Utilidades geoespaciales para KIDO-Ruteo.
"""

import geopandas as gpd
from shapely.geometry import Point, LineString
from typing import Tuple


def point_in_polygon(point: Point, polygon) -> bool:
    """
    Verifica si un punto está dentro de un polígono.
    
    Args:
        point: Punto a verificar
        polygon: Polígono
        
    Returns:
        True si el punto está dentro
    """
    return polygon.contains(point)


def calculate_distance_euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calcula distancia euclidiana entre dos puntos.
    
    Args:
        x1, y1: Coordenadas del primer punto
        x2, y2: Coordenadas del segundo punto
        
    Returns:
        Distancia
    """
    return ((x2 - x1)**2 + (y2 - y1)**2)**0.5


def create_linestring_from_coords(coords: list) -> LineString:
    """
    Crea LineString desde lista de coordenadas.
    
    Args:
        coords: Lista de tuplas (x, y)
        
    Returns:
        LineString
    """
    return LineString(coords)


def reproject_gdf(gdf: gpd.GeoDataFrame, target_crs: str = 'EPSG:4326') -> gpd.GeoDataFrame:
    """
    Reproyecta GeoDataFrame a CRS objetivo.
    
    Args:
        gdf: GeoDataFrame
        target_crs: CRS objetivo
        
    Returns:
        GeoDataFrame reproyectado
    """
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:4326')
    
    if gdf.crs.to_string() != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    return gdf
