"""
Módulo de carga de grafos de red vial.
"""

import networkx as nx
import geopandas as gpd
import osmnx as ox
import os
import logging
from typing import Optional, Sequence, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


def infer_bbox_from_zonification(
    zonification_path: str,
    padding_ratio: float = 0.05,
    min_padding_deg: float = 0.01,
) -> Tuple[float, float, float, float]:
    """Infers an OSM bbox (north, south, east, west) from zonification extent.

    This is meant to cover the full area of interest for OD pairs, since origins,
    destinations, and checkpoints live inside the zonification layer.
    """
    zones = gpd.read_file(zonification_path)
    if zones.empty:
        raise ValueError(f"Zonification is empty: {zonification_path}")

    # Ensure geographic CRS for bbox in degrees
    if zones.crs is None:
        raise ValueError(f"Zonification has no CRS: {zonification_path}")
    if not zones.crs.is_geographic:
        zones = zones.to_crs("EPSG:4326")
    elif str(zones.crs).upper() != "EPSG:4326":
        zones = zones.to_crs("EPSG:4326")

    minx, miny, maxx, maxy = zones.total_bounds  # lon, lat
    span_x = max(maxx - minx, 0.0)
    span_y = max(maxy - miny, 0.0)
    pad_x = max(span_x * padding_ratio, min_padding_deg)
    pad_y = max(span_y * padding_ratio, min_padding_deg)

    west = float(minx - pad_x)
    east = float(maxx + pad_x)
    south = float(miny - pad_y)
    north = float(maxy + pad_y)
    return north, south, east, west


def infer_bbox_from_queries_and_zonification(
    query_paths: Sequence[str],
    zonification_path: str,
    padding_ratio: float = 0.05,
    min_padding_deg: float = 0.01,
    ensure_covers_zonification: bool = True,
) -> Tuple[float, float, float, float]:
    """Infers a bbox from the OD pairs present across multiple query CSVs.

    - Reads each query and extracts origin/destination zone IDs.
    - Subsets the zonification layer to those IDs and computes bounds.
    - Optionally unions with full zonification bounds (default True).
    - Adds padding.

    Returns (north, south, east, west) in EPSG:4326 degrees.
    """
    zones = gpd.read_file(zonification_path)
    if zones.empty:
        raise ValueError(f"Zonification is empty: {zonification_path}")
    if zones.crs is None:
        raise ValueError(f"Zonification has no CRS: {zonification_path}")
    if not zones.crs.is_geographic or str(zones.crs).upper() != "EPSG:4326":
        zones = zones.to_crs("EPSG:4326")

    # Collect used zone IDs from queries
    used_ids: set[int] = set()
    for p in query_paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue

        cols = {c.strip().lower(): c for c in df.columns}
        origin_col = cols.get("origin_id") or cols.get("origin")
        dest_col = cols.get("destination_id") or cols.get("destination")

        if origin_col:
            s = pd.to_numeric(df[origin_col], errors="coerce")
            used_ids.update(int(x) for x in s.dropna().astype(int).tolist())
        if dest_col:
            s = pd.to_numeric(df[dest_col], errors="coerce")
            used_ids.update(int(x) for x in s.dropna().astype(int).tolist())

    # Bounds from subset (if any)
    subset_bounds = None
    if used_ids and "ID" in zones.columns:
        subset = zones[zones["ID"].isin(list(used_ids))]
        if not subset.empty:
            minx, miny, maxx, maxy = subset.total_bounds
            subset_bounds = (minx, miny, maxx, maxy)

    # Full zonification bounds
    z_minx, z_miny, z_maxx, z_maxy = zones.total_bounds

    if subset_bounds is None:
        minx, miny, maxx, maxy = z_minx, z_miny, z_maxx, z_maxy
    else:
        minx, miny, maxx, maxy = subset_bounds
        if ensure_covers_zonification:
            minx = min(minx, z_minx)
            miny = min(miny, z_miny)
            maxx = max(maxx, z_maxx)
            maxy = max(maxy, z_maxy)

    span_x = max(maxx - minx, 0.0)
    span_y = max(maxy - miny, 0.0)
    pad_x = max(span_x * padding_ratio, min_padding_deg)
    pad_y = max(span_y * padding_ratio, min_padding_deg)

    west = float(minx - pad_x)
    east = float(maxx + pad_x)
    south = float(miny - pad_y)
    north = float(maxy + pad_y)
    return north, south, east, west


def ensure_graph_from_geojson_or_osm(
    geojson_path: str,
    zonification_path: Optional[str] = None,
    osm_bbox: Optional[Sequence[float]] = None,
    network_type: str = "drive",
) -> nx.Graph:
    """Load graph from GeoJSON, downloading from OSM if the file is missing.

    Priority for bbox:
      1) explicit osm_bbox [north, south, east, west]
      2) infer from zonification extent (requires zonification_path)
    """
    if osm_bbox is not None:
        if len(osm_bbox) != 4:
            raise ValueError("osm_bbox must be [north, south, east, west]")
        north, south, east, west = map(float, osm_bbox)
    else:
        if not zonification_path:
            raise ValueError(
                "Network file is missing and no osm_bbox provided; "
                "zonification_path is required to infer a bbox."
            )
        north, south, east, west = infer_bbox_from_zonification(zonification_path)

    # If the file exists, validate that it covers the required bbox.
    # This prevents silently using a too-small or wrongly-generated network.
    if os.path.exists(geojson_path):
        try:
            red_gdf = gpd.read_file(geojson_path)
            if red_gdf.empty:
                raise ValueError("Existing network GeoJSON is empty")
            if red_gdf.crs is None:
                raise ValueError("Existing network GeoJSON has no CRS")

            red_4326 = red_gdf
            if (not red_4326.crs.is_geographic) or (str(red_4326.crs).upper() != "EPSG:4326"):
                red_4326 = red_4326.to_crs("EPSG:4326")

            file_west, file_south, file_east, file_north = map(float, red_4326.total_bounds)
            covers = (
                (file_west <= west)
                and (file_south <= south)
                and (file_east >= east)
                and (file_north >= north)
            )

            if covers:
                return load_graph_from_geojson(geojson_path)

            logger.warning(
                "La red existente en %s NO cubre el bbox requerido. "
                "Red: (west=%s, south=%s, east=%s, north=%s) vs requerido: (west=%s, south=%s, east=%s, north=%s). "
                "Se re-descargará desde OSM.",
                geojson_path,
                file_west,
                file_south,
                file_east,
                file_north,
                west,
                south,
                east,
                north,
            )
        except Exception as e:
            logger.warning(
                "No se pudo validar la red existente en %s (%s). Se re-descargará desde OSM.",
                geojson_path,
                e,
            )

    logger.warning(
        "No se encontró archivo de red en %s. Descargando desde OSM (bbox: %s, %s, %s, %s) y guardando GeoJSON...",
        geojson_path,
        north,
        south,
        east,
        west,
    )
    G_osm = download_graph_from_bbox(north=north, south=south, east=east, west=west, network_type=network_type)
    save_graph_to_geojson(G_osm, geojson_path)
    return load_graph_from_geojson(geojson_path)

def load_graph_from_geojson(geojson_path: str) -> nx.Graph:
    """
    Carga un grafo desde un archivo GeoJSON de red vial.
    
    Args:
        geojson_path: Ruta al archivo GeoJSON
        
    Returns:
        Grafo de NetworkX
    """
    if not os.path.exists(geojson_path):
        raise FileNotFoundError(f"No se encontró el archivo de red: {geojson_path}")
        
    red_gdf = gpd.read_file(geojson_path)
    
    # Proyectar a UTM (metros) si es geográfico
    if red_gdf.crs and red_gdf.crs.is_geographic:
        try:
            utm_crs = red_gdf.estimate_utm_crs()
            red_gdf = red_gdf.to_crs(utm_crs)
            logger.info(f"Red reproyectada a {utm_crs} para cálculo de distancias en metros.")
        except Exception as e:
            logger.warning(f"No se pudo reproyectar la red: {e}. Las distancias podrían estar en grados.")
            
    return build_network_graph(red_gdf)

def download_graph_from_bbox(north: float, south: float, east: float, west: float, network_type: str = 'drive') -> nx.Graph:
    """
    Descarga el grafo de red vial desde OpenStreetMap usando un Bounding Box.
    
    Args:
        north: Latitud norte
        south: Latitud sur
        east: Longitud este
        west: Longitud oeste
        network_type: Tipo de red ('drive', 'walk', etc.)
        
    Returns:
        Grafo de NetworkX
    """
    # OSMnx v2.x espera bbox en orden (left, bottom, right, top) == (west, south, east, north)
    logger.info(f"Descargando red vial de OSM (bbox: west={west}, south={south}, east={east}, north={north})...")
    G = ox.graph_from_bbox(bbox=(west, south, east, north), network_type=network_type)
    logger.info(f"Grafo descargado: {len(G.nodes)} nodos, {len(G.edges)} aristas.")
    return G

def save_graph_to_geojson(G: nx.Graph, output_path: str):
    """
    Guarda el grafo como GeoJSON (nodos y aristas).
    Nota: OSMnx guarda graphml por defecto, pero aquí convertimos a gdf para geojson.
    """
    # Convertir a GeoDataFrames
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
    
    # Guardar aristas (que es lo que usa build_network_graph usualmente)
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdf_edges.to_file(output_path, driver='GeoJSON')
    logger.info(f"Red guardada en: {output_path}")

def build_network_graph(red_gdf: gpd.GeoDataFrame) -> nx.Graph:
    """
    Construye grafo de red vial desde GeoDataFrame.
    
    Args:
        red_gdf: GeoDataFrame con red vial
        
    Returns:
        Grafo de NetworkX
    """
    G = nx.Graph()
    # Guardar CRS si existe
    if hasattr(red_gdf, 'crs'):
        G.graph['crs'] = red_gdf.crs
    
    for idx, row in red_gdf.iterrows():
        geom = row.geometry
        
        # Extraer nodos de la geometría (LineString)
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            
            # Agregar nodos
            for coord in coords:
                node_id = f"{coord[0]:.6f},{coord[1]:.6f}"
                if not G.has_node(node_id):
                    G.add_node(node_id, pos=coord)
            
            # Agregar aristas entre nodos consecutivos
            for i in range(len(coords) - 1):
                node_i = f"{coords[i][0]:.6f},{coords[i][1]:.6f}"
                node_j = f"{coords[i+1][0]:.6f},{coords[i+1][1]:.6f}"
                
                # Calcular peso (distancia euclidiana)
                dist = ((coords[i][0] - coords[i+1][0])**2 + 
                       (coords[i][1] - coords[i+1][1])**2)**0.5
                
                G.add_edge(node_i, node_j, weight=dist)
    
    return G
