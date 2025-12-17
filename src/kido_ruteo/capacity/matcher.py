import pandas as pd
import numpy as np

def match_capacity_to_od(df_od: pd.DataFrame, df_capacity: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza datos de OD/Ruteo con datos de Capacidad basados en Checkpoint y Sentido.
    
    STRICT MODE:
    - Match EXACTO de (checkpoint_id, sense_code) con (Checkpoint, Sentido)
    - NO fallback a Sentido '0'
    - NO agregación de capacidades
    - Si no hay match exacto → todas las capacidades = NaN
    
    Args:
        df_od: DataFrame con 'checkpoint_id' y 'sense_code' (derivado geométricamente)
        df_capacity: DataFrame con 'Checkpoint', 'Sentido', y capacidades por categoría
        
    Returns:
        DataFrame con columnas cap_au, cap_cu, cap_cai, cap_caii, cap_total
        Si no hay match: todas las capacidades = NaN
    """
    # Si no hay checkpoint_id, no podemos cruzar capacidad
    if 'checkpoint_id' not in df_od.columns:
        # Agregar columnas vacías
        df_od['cap_au'] = np.nan
        df_od['cap_cu'] = np.nan
        df_od['cap_cai'] = np.nan
        df_od['cap_caii'] = np.nan
        df_od['cap_total'] = np.nan
        return df_od

    # Asegurar tipos string para las llaves de cruce
    df_od['checkpoint_id'] = df_od['checkpoint_id'].astype(str)
    if 'sense_code' not in df_od.columns:
        df_od['sense_code'] = None
    
    df_capacity = df_capacity.copy()
    df_capacity['Checkpoint'] = df_capacity['Checkpoint'].astype(str)
    df_capacity['Sentido'] = df_capacity['Sentido'].astype(str)
    
    # Seleccionar solo columnas necesarias de capacity
    # summary_capacity.csv tiene: A, CU, CAI, CAII (sin AU en el nombre)
    capacity_cols = ['Checkpoint', 'Sentido', 'A', 'CU', 'CAI', 'CAII']
    df_capacity_slim = df_capacity[capacity_cols].copy()
    
    # MERGE EXACTO: (checkpoint_id, sense_code) con (Checkpoint, Sentido)
    merged = pd.merge(
        df_od,
        df_capacity_slim,
        left_on=['checkpoint_id', 'sense_code'],
        right_on=['Checkpoint', 'Sentido'],
        how='left',
        suffixes=('', '_cap'),
        validate='many_to_one'
    )
    
    # Renombrar columnas de capacidad según especificación
    # A → cap_au (Auto/Automóvil)
    rename_map = {
        'A': 'cap_au',
        'CU': 'cap_cu',
        'CAI': 'cap_cai',
        'CAII': 'cap_caii'
    }
    
    merged = merged.rename(columns=rename_map)
    
    # Calcular cap_total como suma de capacidades por categoría
    # Si todas son NaN (no match), cap_total será 0 → convertir a NaN
    merged['cap_total'] = (
        merged['cap_au'].fillna(0) +
        merged['cap_cu'].fillna(0) +
        merged['cap_cai'].fillna(0) +
        merged['cap_caii'].fillna(0)
    )
    
    # Si NO hubo match (todas las capacidades son NaN), cap_total debe ser NaN
    all_cap_nan = (
        merged['cap_au'].isna() & 
        merged['cap_cu'].isna() & 
        merged['cap_cai'].isna() & 
        merged['cap_caii'].isna()
    )
    merged.loc[all_cap_nan, 'cap_total'] = np.nan
    
    # Eliminar columnas auxiliares del merge
    if 'Checkpoint' in merged.columns:
        merged = merged.drop(columns=['Checkpoint'])
    if 'Sentido' in merged.columns:
        merged = merged.drop(columns=['Sentido'])
    
    return merged
