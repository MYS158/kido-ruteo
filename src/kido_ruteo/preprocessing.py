"""
Módulo de preprocesamiento para KIDO-Ruteo.

Funciones para limpieza, normalización y validación de datos.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas a snake_case.
    
    Args:
        df: DataFrame con columnas a normalizar
        
    Returns:
        DataFrame con columnas normalizadas
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(' ', '_')
        .str.replace('-', '_')
        .str.replace('.', '_')
        .str.strip()
    )
    return df


def validate_od_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Valida que un DataFrame OD tenga las columnas requeridas.
    
    Args:
        df: DataFrame a validar
        
    Returns:
        Tupla (es_válido, columnas_faltantes)
    """
    required_patterns = ['origen', 'destino']
    missing = []
    
    for pattern in required_patterns:
        if not any(pattern in col.lower() for col in df.columns):
            missing.append(pattern)
    
    is_valid = len(missing) == 0
    return is_valid, missing


def clean_od_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia datos OD eliminando valores nulos e inválidos.
    
    Args:
        df: DataFrame con datos OD
        
    Returns:
        DataFrame limpio
    """
    df = df.copy()
    
    # Eliminar filas con origen o destino nulo
    origin_cols = [col for col in df.columns if 'origen' in col.lower() or 'origin' in col.lower()]
    dest_cols = [col for col in df.columns if 'destino' in col.lower() or 'destination' in col.lower()]
    
    for col in origin_cols + dest_cols:
        df = df[df[col].notna()]
    
    # Eliminar viajes negativos
    trips_cols = [col for col in df.columns if 'viajes' in col.lower() or 'trips' in col.lower()]
    for col in trips_cols:
        if col in df.columns:
            df = df[df[col] >= 0]
    
    return df


def convert_od_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte tipos de datos en matrices OD.
    
    Args:
        df: DataFrame con datos OD
        
    Returns:
        DataFrame con tipos correctos
    """
    df = df.copy()
    
    # Convertir IDs a enteros
    id_patterns = ['id', 'origen', 'origin', 'destino', 'destination', 'zone']
    for col in df.columns:
        if any(pattern in col.lower() for pattern in id_patterns):
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            except:
                pass
    
    # Convertir métricas numéricas a float
    numeric_patterns = ['viajes', 'trips', 'distancia', 'distance', 'tiempo', 'time', 'flujo', 'flow']
    for col in df.columns:
        if any(pattern in col.lower() for pattern in numeric_patterns):
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
            except:
                pass
    
    return df


def aggregate_od_matrix(
    df: pd.DataFrame,
    origin_col: str = 'origen',
    dest_col: str = 'destino',
    value_col: str = 'viajes',
    agg_func: str = 'sum'
) -> pd.DataFrame:
    """
    Agrega matriz OD por pares origen-destino.
    
    Args:
        df: DataFrame con datos OD
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        value_col: Nombre de columna a agregar
        agg_func: Función de agregación ('sum', 'mean', 'count')
        
    Returns:
        DataFrame agregado
    """
    agg_dict = {value_col: agg_func}
    
    df_agg = (
        df.groupby([origin_col, dest_col])
        .agg(agg_dict)
        .reset_index()
    )
    
    return df_agg


def filter_zero_trips(
    df: pd.DataFrame,
    trips_col: str = 'viajes',
    keep_zeros: bool = False
) -> pd.DataFrame:
    """
    Filtra o mantiene registros con viajes cero.
    
    Args:
        df: DataFrame con datos OD
        trips_col: Nombre de columna de viajes
        keep_zeros: Si True, mantiene ceros; si False, los elimina
        
    Returns:
        DataFrame filtrado
    """
    if keep_zeros:
        return df
    else:
        return df[df[trips_col] > 0].copy()


def detect_outliers(
    df: pd.DataFrame,
    column: str,
    method: str = 'iqr',
    threshold: float = 1.5
) -> pd.Series:
    """
    Detecta outliers en una columna numérica.
    
    Args:
        df: DataFrame a analizar
        column: Nombre de columna
        method: Método de detección ('iqr', 'zscore')
        threshold: Umbral para considerar outlier
        
    Returns:
        Serie booleana indicando outliers
    """
    if method == 'iqr':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        
        is_outlier = (df[column] < lower_bound) | (df[column] > upper_bound)
    
    elif method == 'zscore':
        mean = df[column].mean()
        std = df[column].std()
        z_scores = np.abs((df[column] - mean) / std)
        
        is_outlier = z_scores > threshold
    
    else:
        raise ValueError(f"Método no soportado: {method}")
    
    return is_outlier


def impute_missing_values(
    df: pd.DataFrame,
    column: str,
    method: str = 'mean'
) -> pd.DataFrame:
    """
    Imputa valores faltantes en una columna.
    
    Args:
        df: DataFrame a procesar
        column: Nombre de columna
        method: Método de imputación ('mean', 'median', 'mode', 'zero')
        
    Returns:
        DataFrame con valores imputados
    """
    df = df.copy()
    
    if method == 'mean':
        fill_value = df[column].mean()
    elif method == 'median':
        fill_value = df[column].median()
    elif method == 'mode':
        fill_value = df[column].mode()[0] if not df[column].mode().empty else 0
    elif method == 'zero':
        fill_value = 0
    else:
        raise ValueError(f"Método no soportado: {method}")
    
    df[column].fillna(fill_value, inplace=True)
    
    return df
