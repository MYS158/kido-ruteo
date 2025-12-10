"""
Módulo de entrada/salida para KIDO-Ruteo.

Funciones para cargar y guardar datos desde diferentes fuentes.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Union, List, Optional, Dict
import json


def load_geojson(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Carga un archivo GeoJSON con geometrías de zonas.
    
    Args:
        file_path: Ruta al archivo GeoJSON
        
    Returns:
        GeoDataFrame con las zonas cargadas
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si el archivo no es un GeoJSON válido
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    try:
        gdf = gpd.read_file(file_path)
        return gdf
    except Exception as e:
        raise ValueError(f"Error al leer GeoJSON: {e}")


def load_od_general(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga archivo CSV con datos OD generales.
    
    Fuente: data/raw/kido-data2/Consultas/General/*.csv
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con datos OD
        
    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    df = pd.read_csv(file_path)
    return df


def load_od_checkpoint(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga archivo CSV con datos OD de checkpoint.
    
    Fuente: data/raw/kido-data2/Consultas/Checkpoint/*.csv
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        DataFrame con datos OD de checkpoint
        
    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    df = pd.read_csv(file_path)
    return df


def load_zoning_metadata(file_path: Union[str, Path]) -> Dict:
    """
    Carga archivo QMD con metadatos de zonificación.
    
    Fuente: data/raw/kido-data2/Zoning/*.qmd
    
    Args:
        file_path: Ruta al archivo QMD
        
    Returns:
        Diccionario con metadatos parseados
        
    Raises:
        FileNotFoundError: Si el archivo no existe
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    # TODO: Implementar parser específico para formato QMD
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return {"raw_content": content}


def load_all_geojson(directory: Union[str, Path]) -> List[gpd.GeoDataFrame]:
    """
    Carga todos los archivos GeoJSON de un directorio.
    
    Args:
        directory: Ruta al directorio con archivos GeoJSON
        
    Returns:
        Lista de GeoDataFrames
    """
    directory = Path(directory)
    geojson_files = list(directory.glob("*.geojson"))
    
    gdfs = []
    for file_path in geojson_files:
        try:
            gdf = load_geojson(file_path)
            gdfs.append(gdf)
        except Exception as e:
            print(f"⚠️  Error al cargar {file_path.name}: {e}")
    
    return gdfs


def load_all_od_files(directory: Union[str, Path]) -> pd.DataFrame:
    """
    Carga y concatena todos los archivos CSV OD de un directorio.
    
    Args:
        directory: Ruta al directorio con archivos CSV
        
    Returns:
        DataFrame concatenado con todos los datos OD
    """
    directory = Path(directory)
    csv_files = list(directory.glob("*.csv"))
    
    dfs = []
    for file_path in csv_files:
        try:
            df = pd.read_csv(file_path)
            df['source_file'] = file_path.name
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  Error al cargar {file_path.name}: {e}")
    
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()


def save_dataframe(
    df: pd.DataFrame,
    file_path: Union[str, Path],
    file_format: str = 'csv'
) -> None:
    """
    Guarda un DataFrame en el formato especificado.
    
    Args:
        df: DataFrame a guardar
        file_path: Ruta de destino
        file_format: Formato del archivo ('csv', 'parquet', 'excel')
        
    Raises:
        ValueError: Si el formato no es soportado
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if file_format == 'csv':
        df.to_csv(file_path, index=False)
    elif file_format == 'parquet':
        df.to_parquet(file_path, index=False)
    elif file_format == 'excel':
        df.to_excel(file_path, index=False)
    else:
        raise ValueError(f"Formato no soportado: {file_format}")


def save_geodataframe(
    gdf: gpd.GeoDataFrame,
    file_path: Union[str, Path],
    driver: str = 'GeoJSON'
) -> None:
    """
    Guarda un GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame a guardar
        file_path: Ruta de destino
        driver: Driver de formato ('GeoJSON', 'GPKG', 'ESRI Shapefile')
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    gdf.to_file(file_path, driver=driver)
