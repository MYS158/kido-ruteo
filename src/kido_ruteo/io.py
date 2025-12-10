"""
Módulo de entrada/salida para KIDO-Ruteo v2.0.

Carga datos desde estructura kido-data2/:
- Consultas/General/*.csv
- Consultas/Checkpoint/*.csv
- Geojson/*.geojson
- Cardinalidad/*.csv
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Union, List, Optional


def load_od_general(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga archivo CSV de consultas generales.
    
    Fuente: kido-data2/Consultas/General/*.csv
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con datos OD generales
    """
    df = pd.read_csv(file_path)
    return df


def load_od_checkpoint(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga archivo CSV de consultas con checkpoint.
    
    Fuente: kido-data2/Consultas/Checkpoint/*.csv
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con datos OD de checkpoint
    """
    df = pd.read_csv(file_path)
    return df


def load_red_vial(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Carga red vial desde GeoJSON.
    
    Fuente: kido-data2/Geojson/red.geojson
    
    Args:
        file_path: Ruta al archivo GeoJSON
        
    Returns:
        GeoDataFrame con red vial
    """
    gdf = gpd.read_file(file_path)
    return gdf


def load_zonificacion(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Carga zonificación desde GeoJSON.
    
    Debe contener columna 'poly_type' para identificar checkpoints.
    
    Fuente: kido-data2/Geojson/zonificacion.geojson
    
    Args:
        file_path: Ruta al archivo GeoJSON
        
    Returns:
        GeoDataFrame con zonas
    """
    gdf = gpd.read_file(file_path)
    
    if 'poly_type' not in gdf.columns:
        print("⚠️  Advertencia: No se encontró columna 'poly_type' en zonificación")
    
    return gdf


def load_cardinalidad(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga archivo de cardinalidad (sentidos viales).
    
    Fuente: kido-data2/Cardinalidad/cardinalidad.csv
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con información de cardinalidad
    """
    df = pd.read_csv(file_path)
    return df


def load_all_od_files(directory: Union[str, Path], tipo: str = 'general') -> pd.DataFrame:
    """
    Carga y concatena todos los archivos OD de un directorio.
    
    Args:
        directory: Directorio con archivos CSV
        tipo: Tipo de consulta ('general' o 'checkpoint')
        
    Returns:
        DataFrame concatenado con todos los datos OD
    """
    directory = Path(directory)
    csv_files = list(directory.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No se encontraron archivos CSV en {directory}")
    
    dfs = []
    for file_path in csv_files:
        df = pd.read_csv(file_path)
        df['source_file'] = file_path.name
        df['tipo_consulta'] = tipo
        dfs.append(df)
    
    return pd.concat(dfs, ignore_index=True)


def save_interim(df: pd.DataFrame, filename: str, output_dir: str = 'data/interim') -> None:
    """
    Guarda DataFrame en directorio interim.
    
    Args:
        df: DataFrame a guardar
        filename: Nombre del archivo (sin extensión)
        output_dir: Directorio de salida
    """
    output_path = Path(output_dir) / f"{filename}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✓ Guardado: {output_path}")


def save_processed(df: pd.DataFrame, filename: str, output_dir: str = 'data/processed') -> None:
    """
    Guarda DataFrame en directorio processed.
    
    Args:
        df: DataFrame a guardar
        filename: Nombre del archivo (sin extensión)
        output_dir: Directorio de salida
    """
    output_path = Path(output_dir) / f"{filename}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✓ Guardado: {output_path}")


def save_geojson(gdf: gpd.GeoDataFrame, filename: str, output_dir: str = 'data/processed') -> None:
    """
    Guarda GeoDataFrame como GeoJSON.
    
    Args:
        gdf: GeoDataFrame a guardar
        filename: Nombre del archivo (sin extensión)
        output_dir: Directorio de salida
    """
    output_path = Path(output_dir) / f"{filename}.geojson"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"✓ Guardado: {output_path}")
