import pandas as pd
import numpy as np

def match_capacity_to_od(df_od: pd.DataFrame, df_capacity: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza datos de OD/Ruteo con datos de Capacidad basados en Checkpoint y Sentido.
    
    STRICT MODE:
    - Match EXACTO de (Checkpoint, Sentido).
    - NO fallback a Sentido '0'.
    - NO agregación de capacidades.
    
    Args:
        df_od: DataFrame con info de ruteo (debe tener 'checkpoint_id' y 'sense_code')
        df_capacity: DataFrame con info de capacidad (debe tener 'Checkpoint' y 'Sentido')
        
    Returns:
        DataFrame con columnas de capacidad unidas. Si no hay match, columnas serán NaN.
    """
    # Si no hay checkpoint_id, no podemos cruzar capacidad.
    if 'checkpoint_id' not in df_od.columns:
        return df_od

    # Asegurar tipos para las llaves de cruce
    df_od['checkpoint_id'] = df_od['checkpoint_id'].astype(str)
    df_capacity = df_capacity.copy()
    df_capacity['Checkpoint'] = df_capacity['Checkpoint'].astype(str)
    df_capacity['Sentido'] = df_capacity['Sentido'].astype(str)
    
    # 1. Cruce (Merge) Exacto
    # Intentamos coincidir Checkpoint y Sentido exacto (ej. '1-3' con '1-3')
    merged = pd.merge(
        df_od,
        df_capacity,
        left_on=['checkpoint_id', 'sense_code'],
        right_on=['Checkpoint', 'Sentido'],
        how='left',
        suffixes=('', '_cap'),
        validate='many_to_one'
    )
    
    # Renombrar columnas de capacidad para coincidir con requerimientos de salida
    rename_map = {
        'FA': 'capacity_fa',
        'M': 'cap_moto',
        'A': 'cap_auto',
        'B': 'cap_bus',
        'CU': 'cap_cu',
        'CAI': 'cap_cai',
        'CAII': 'cap_caii',
        'TOTAL': 'cap_total',
        'Focup_M': 'focup_moto',
        'Focup_A': 'focup_auto',
        'Focup_B': 'focup_bus',
        'Focup_CU': 'focup_cu',
        'Focup_CAI': 'focup_cai',
        'Focup_CAII': 'focup_caii'
    }
    
    merged = merged.rename(columns=rename_map)
    
    # Crear bandera de disponibilidad de capacidad
    merged['cap_available'] = merged['cap_total'].notna()
    
    # Crear bandera de sentido válido
    # Si hay capacidad, es válido.
    merged['sense_valid'] = merged['cap_available']
    
    return merged
    
    # Crear bandera de disponibilidad de capacidad
    merged['cap_available'] = merged['cap_total'].notna()
    
    # Crear bandera de sentido válido
    # Si hay capacidad (incluso generada para '0'), es válido.
    merged['sense_valid'] = merged['cap_available']
    
    return merged
