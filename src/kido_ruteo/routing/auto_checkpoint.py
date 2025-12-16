"""
Módulo para identificación automática de checkpoints.
"""

import pandas as pd
import geopandas as gpd
from typing import List

def find_checkpoint_nodes(
    zones_gdf: gpd.GeoDataFrame,
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
