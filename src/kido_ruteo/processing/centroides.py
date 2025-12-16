import geopandas as gpd
import pandas as pd
import networkx as nx
from shapely.geometry import Point
from scipy.spatial import cKDTree
import numpy as np

def assign_nodes_to_zones(zones_gdf: gpd.GeoDataFrame, G: nx.Graph) -> gpd.GeoDataFrame:
    """
    Asigna un nodo del grafo como centroide a cada zona.
    """
    # Verificar CRS del grafo
    graph_crs = G.graph.get('crs')
    
    # Si el grafo tiene CRS y es diferente al de zonas, reproyectar zonas
    if graph_crs is not None and zones_gdf.crs != graph_crs:
        zones_gdf = zones_gdf.to_crs(graph_crs)

    # Extraer nodos del grafo como GeoDataFrame
    node_ids = list(G.nodes())
    node_coords = [G.nodes[n]['pos'] for n in node_ids]
    nodes_gdf = gpd.GeoDataFrame(
        {'node_id': node_ids},
        geometry=[Point(x, y) for x, y in node_coords],
        crs=graph_crs if graph_crs else zones_gdf.crs
    )
    
    # Spatial join o Nearest Neighbor
    # Para simplificar, usamos el centroide geométrico de la zona y buscamos el nodo más cercano
    
    zones_gdf['centroid_geom'] = zones_gdf.geometry.centroid
    
    # Construir KDTree de nodos
    node_points = np.array([(p.x, p.y) for p in nodes_gdf.geometry])
    tree = cKDTree(node_points)
    
    def get_nearest_node(geom):
        dist, idx = tree.query((geom.x, geom.y))
        return nodes_gdf.iloc[idx]['node_id']
    
    zones_gdf['nearest_node_id'] = zones_gdf['centroid_geom'].apply(get_nearest_node)
    
    return zones_gdf

def add_centroid_coordinates_to_od(df_od: pd.DataFrame, zones_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Agrega las coordenadas (o node_ids) de origen y destino al DataFrame OD.
    """
    # Mapeo de ID de zona a Node ID
    # Asumimos que zones_gdf tiene una columna 'ID' que matchea con origin_id/destination_id
    
    zone_to_node = zones_gdf.set_index('ID')['nearest_node_id'].to_dict()
    
    # Asegurar tipos
    df_od['origin_id'] = pd.to_numeric(df_od['origin_id'], errors='coerce')
    df_od['destination_id'] = pd.to_numeric(df_od['destination_id'], errors='coerce')
    
    df_od['origin_node_id'] = df_od['origin_id'].map(zone_to_node)
    df_od['destination_node_id'] = df_od['destination_id'].map(zone_to_node)
    
    # Mapear checkpoint si existe
    if 'checkpoint_id' in df_od.columns:
        df_od['checkpoint_id'] = pd.to_numeric(df_od['checkpoint_id'], errors='coerce')
        df_od['checkpoint_node_id'] = df_od['checkpoint_id'].map(zone_to_node)
    
    # Filtrar filas donde no se encontró nodo (zonas sin mapeo)
    # Opcional: df_od.dropna(subset=['origin_node_id', 'destination_node_id'], inplace=True)
    
    return df_od
