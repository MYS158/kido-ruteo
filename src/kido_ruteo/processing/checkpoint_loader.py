"""
Módulo para cargar y procesar checkpoints desde zonification.geojson.
STRICT MODE: Los checkpoints son la única fuente de verdad para ubicaciones.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import osmnx as ox


def load_checkpoints_from_zonification(zonification_path: str) -> gpd.GeoDataFrame:
    """
    Carga checkpoints desde el archivo zonification.geojson.
    
    Los checkpoints son features con poly_type='Checkpoint'.
    
    Parameters
    ----------
    zonification_path : str
        Ruta al archivo zonification.geojson
        
    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame con:
        - checkpoint_id (int): ID del checkpoint
        - checkpoint_name (str): Nombre del checkpoint (ej: 'E01', 'E02')
        - geometry (Point): Centroide del polígono del checkpoint
    """
    # Cargar el archivo completo
    gdf = gpd.read_file(zonification_path)
    
    # Filtrar solo los checkpoints
    checkpoints = gdf[gdf['poly_type'] == 'Checkpoint'].copy()
    
    if len(checkpoints) == 0:
        raise ValueError(f"No se encontraron checkpoints en {zonification_path}")
    
    # Extraer información relevante
    checkpoints['checkpoint_id'] = checkpoints['ID']
    checkpoints['checkpoint_name'] = checkpoints['NOMGEO']
    
    # Proyectar a sistema de coordenadas apropiado antes de calcular centroides
    checkpoints_projected = checkpoints.to_crs('EPSG:32614')  # UTM Zone 14N
    
    # Calcular centroides (en coordenadas proyectadas)
    checkpoints_projected['geometry'] = checkpoints_projected['geometry'].centroid
    
    # Regresar a coordenadas geográficas para consistencia
    checkpoints_final = checkpoints_projected.to_crs('EPSG:4326')
    
    # Seleccionar solo las columnas necesarias
    result = checkpoints_final[['checkpoint_id', 'checkpoint_name', 'geometry']].copy()
    
    print(f"✓ Cargados {len(result)} checkpoints desde zonification.geojson")
    print(f"  IDs: {sorted(result['checkpoint_id'].tolist())}")
    
    return result


def assign_checkpoint_nodes(checkpoints_gdf: gpd.GeoDataFrame, 
                            graph) -> pd.DataFrame:
    """
    Asigna el nodo más cercano de la red a cada checkpoint.
    
    Parameters
    ----------
    checkpoints_gdf : gpd.GeoDataFrame
        DataFrame con checkpoints (debe tener geometría Point)
    graph : networkx.MultiDiGraph
        Grafo de la red de transporte
        
    Returns
    -------
    pd.DataFrame
        DataFrame con:
        - checkpoint_id (int)
        - checkpoint_name (str)
        - checkpoint_node_id (str): ID del nodo más cercano en el grafo
        - lat (float): Latitud del checkpoint (original)
        - lon (float): Longitud del checkpoint (original)
    """
    import numpy as np
    
    # Proyectar checkpoints al mismo CRS del grafo (EPSG:32614)
    checkpoints_projected = checkpoints_gdf.to_crs('EPSG:32614')
    
    # Extraer nodos del grafo con sus coordenadas proyectadas
    nodes_coords = {}
    for node_id in graph.nodes():
        if 'pos' in graph.nodes[node_id]:
            x, y = graph.nodes[node_id]['pos']
            nodes_coords[node_id] = (x, y)
    
    if len(nodes_coords) == 0:
        raise ValueError("El grafo no tiene nodos con atributo 'pos'")
    
    print(f"  Buscando nodos más cercanos entre {len(nodes_coords)} nodos disponibles...")
    
    result = []
    
    for original_idx, projected_row in checkpoints_projected.iterrows():
        # Obtener la fila correspondiente del GeoDataFrame original
        original_row = checkpoints_gdf.loc[original_idx]
        
        checkpoint_id = original_row['checkpoint_id']
        checkpoint_name = original_row['checkpoint_name']
        point_projected = projected_row['geometry']  # Este está proyectado
        point_original = original_row['geometry']  # Geográfico original
        
        # Calcular distancias a todos los nodos (en coordenadas proyectadas)
        min_dist = float('inf')
        nearest_node = None
        
        for node_id, (node_x, node_y) in nodes_coords.items():
            # Calcular distancia euclidiana en metros
            dist = np.sqrt((point_projected.x - node_x)**2 + (point_projected.y - node_y)**2)
            
            if dist < min_dist:
                min_dist = dist
                nearest_node = node_id
        
        if nearest_node is None:
            raise ValueError(f"No se pudo encontrar nodo cercano para checkpoint {checkpoint_id}")
        
        result.append({
            'checkpoint_id': checkpoint_id,
            'checkpoint_name': checkpoint_name,
            'checkpoint_node_id': nearest_node,
            'lat': point_original.y,
            'lon': point_original.x,
            'distance_m': min_dist
        })
    
    df_result = pd.DataFrame(result)
    
    print(f"✓ Asignados {len(df_result)} checkpoints a nodos de la red")
    print(f"  Distancia promedio al nodo: {df_result['distance_m'].mean():.1f} m")
    
    return df_result


def get_checkpoint_node_mapping(zonification_path: str, graph) -> pd.DataFrame:
    """
    Función de conveniencia que carga checkpoints y los asigna a nodos.
    
    Parameters
    ----------
    zonification_path : str
        Ruta al archivo zonification.geojson
    graph : networkx.MultiDiGraph
        Grafo de la red de transporte
        
    Returns
    -------
    pd.DataFrame
        Mapping checkpoint_id -> checkpoint_node_id
    """
    # 1. Cargar checkpoints
    checkpoints_gdf = load_checkpoints_from_zonification(zonification_path)
    
    # 2. Asignar nodos
    checkpoint_nodes = assign_checkpoint_nodes(checkpoints_gdf, graph)
    
    return checkpoint_nodes
