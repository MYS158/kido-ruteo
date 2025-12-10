"""
Modelo de zonificación para KIDO-Ruteo.
"""

import geopandas as gpd
import pandas as pd
from typing import Optional, List, Dict
from shapely.geometry import Point


class Zoning:
    """
    Representa un sistema de zonificación geográfica.
    """
    
    def __init__(self, zones_gdf: gpd.GeoDataFrame, id_col: str = 'id'):
        """
        Inicializa sistema de zonificación.
        
        Args:
            zones_gdf: GeoDataFrame con geometrías de zonas
            id_col: Nombre de columna con IDs de zona
        """
        self.zones = zones_gdf.copy()
        self.id_col = id_col
        
        # Calcular centroides si no existen
        if 'centroid' not in self.zones.columns:
            self.zones['centroid'] = self.zones.geometry.centroid
    
    def get_zone(self, zone_id: int) -> Optional[gpd.GeoSeries]:
        """
        Obtiene una zona por su ID.
        
        Args:
            zone_id: ID de la zona
            
        Returns:
            GeoSeries con la zona o None si no existe
        """
        mask = self.zones[self.id_col] == zone_id
        if mask.any():
            return self.zones[mask].iloc[0]
        return None
    
    def get_centroid(self, zone_id: int) -> Optional[Point]:
        """
        Obtiene el centroide de una zona.
        
        Args:
            zone_id: ID de la zona
            
        Returns:
            Punto centroide o None si no existe
        """
        zone = self.get_zone(zone_id)
        if zone is not None:
            return zone['centroid']
        return None
    
    def find_zone_by_point(self, point: Point) -> Optional[int]:
        """
        Encuentra la zona que contiene un punto.
        
        Args:
            point: Punto a buscar
            
        Returns:
            ID de la zona o None si no se encuentra
        """
        for idx, row in self.zones.iterrows():
            if row.geometry.contains(point):
                return row[self.id_col]
        return None
    
    def get_adjacent_zones(self, zone_id: int) -> List[int]:
        """
        Encuentra zonas adyacentes a una zona dada.
        
        Args:
            zone_id: ID de la zona
            
        Returns:
            Lista de IDs de zonas adyacentes
        """
        zone = self.get_zone(zone_id)
        if zone is None:
            return []
        
        adjacent = []
        zone_geom = zone.geometry
        
        for idx, row in self.zones.iterrows():
            if row[self.id_col] != zone_id:
                if zone_geom.touches(row.geometry):
                    adjacent.append(row[self.id_col])
        
        return adjacent
    
    def compute_zone_statistics(self) -> pd.DataFrame:
        """
        Calcula estadísticas para todas las zonas.
        
        Returns:
            DataFrame con estadísticas por zona
        """
        stats = []
        
        for idx, row in self.zones.iterrows():
            zone_id = row[self.id_col]
            
            stats.append({
                'zone_id': zone_id,
                'area': row.geometry.area,
                'perimeter': row.geometry.length,
                'centroid_x': row['centroid'].x,
                'centroid_y': row['centroid'].y,
                'num_adjacent': len(self.get_adjacent_zones(zone_id))
            })
        
        return pd.DataFrame(stats)
    
    def validate_zones(self) -> Dict[str, any]:
        """
        Valida integridad del sistema de zonificación.
        
        Returns:
            Diccionario con resultados de validación
        """
        validation = {
            'total_zones': len(self.zones),
            'valid_geometries': self.zones.geometry.is_valid.sum(),
            'invalid_geometries': (~self.zones.geometry.is_valid).sum(),
            'has_crs': self.zones.crs is not None,
            'crs': str(self.zones.crs) if self.zones.crs else None,
            'duplicate_ids': self.zones[self.id_col].duplicated().sum()
        }
        
        validation['is_valid'] = (
            validation['invalid_geometries'] == 0 and
            validation['has_crs'] and
            validation['duplicate_ids'] == 0
        )
        
        return validation
    
    def reproject(self, target_crs: str = 'EPSG:4326') -> 'Zoning':
        """
        Reproyecta zonas a un CRS objetivo.
        
        Args:
            target_crs: CRS objetivo
            
        Returns:
            Nueva instancia de Zoning reproyectada
        """
        reprojected_zones = self.zones.to_crs(target_crs)
        return Zoning(reprojected_zones, self.id_col)
    
    def __len__(self) -> int:
        """Retorna número de zonas."""
        return len(self.zones)
    
    def __repr__(self) -> str:
        """Representación en string."""
        crs_str = str(self.zones.crs) if self.zones.crs else "No CRS"
        return f"Zoning({len(self)} zones, CRS: {crs_str})"
