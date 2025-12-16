"""
Paso 1 del flujo KIDO: Preparación de datos.

Crea las columnas:
- total_trips_modif
- intrazonal
"""

import pandas as pd
import numpy as np


def create_total_trips_modif(df: pd.DataFrame, trips_col: str = 'total_trips') -> pd.DataFrame:
    """
    Crea columna total_trips_modif según regla KIDO:
    - Si total_trips < 10: total_trips_modif = 1
    - Si total_trips >= 10: total_trips_modif = total_trips
    
    Args:
        df: DataFrame con datos OD
        trips_col: Nombre de columna con trips totales
        
    Returns:
        DataFrame con columna total_trips_modif añadida
    """
    df = df.copy()
    
    df['total_trips_modif'] = df[trips_col].apply(
        lambda x: 1 if x < 10 else x
    )
    
    return df


def create_intrazonal(
    df: pd.DataFrame,
    origin_col: str = 'origin_name',
    dest_col: str = 'destination_name'
) -> pd.DataFrame:
    """
    Crea columna intrazonal según regla KIDO:
    - Si origin_name == destination_name: intrazonal = 1
    - En otro caso: intrazonal = 0
    
    Args:
        df: DataFrame con datos OD
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame con columna intrazonal añadida
    """
    df = df.copy()
    
    df['intrazonal'] = (df[origin_col] == df[dest_col]).astype(int)
    
    return df


def prepare_data(
    df: pd.DataFrame,
    trips_col: str = 'total_trips',
    origin_col: str = 'origin_name',
    dest_col: str = 'destination_name'
) -> pd.DataFrame:
    """
    Ejecuta preparación completa de datos (Paso 1 KIDO).
    
    Args:
        df: DataFrame con datos OD
        trips_col: Nombre de columna con trips
        origin_col: Nombre de columna de origen
        dest_col: Nombre de columna de destino
        
    Returns:
        DataFrame preparado con total_trips_modif e intrazonal
    """
    print("=" * 60)
    print("PASO 1: Preparación de Datos")
    print("=" * 60)
    
    # Crear total_trips_modif
    df = create_total_trips_modif(df, trips_col)
    print(f"✓ Creada columna 'total_trips_modif'")
    print(f"  - Viajes < 10: {(df[trips_col] < 10).sum()} registros → modif = 1")
    print(f"  - Viajes >= 10: {(df[trips_col] >= 10).sum()} registros → modif = original")
    
    # Crear intrazonal
    df = create_intrazonal(df, origin_col, dest_col)
    print(f"✓ Creada columna 'intrazonal'")
    print(f"  - Viajes intrazonales: {df['intrazonal'].sum()}")
    print(f"  - Viajes interzonales: {(df['intrazonal'] == 0).sum()}")
    
    return df


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas a snake_case.
    """
    df = df.copy()
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('-', '_')
    return df
