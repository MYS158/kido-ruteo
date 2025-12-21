import pandas as pd
import numpy as np

def match_capacity_to_od(df_od: pd.DataFrame, df_capacity: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza datos de OD/Ruteo con datos de Capacidad basados en Checkpoint y Sentido.
    
    STRICT MODE:
    - Match EXACTO de (checkpoint_id, sense_code) con (Checkpoint, Sentido)
    - NO fallback a Sentido '0'
    - NO agregación en este paso (la agregación, si existe, ocurre en loader)
    - Si no hay match exacto → todas las capacidades/factores quedan NaN
    
    Args:
        df_od: DataFrame con 'checkpoint_id' y 'sense_code' (derivado geométricamente)
        df_capacity: DataFrame con 'Checkpoint', 'Sentido', y capacidades por categoría
        
    Returns:
        DataFrame con columnas:
        - cap_M, cap_A, cap_B, cap_CU, cap_CAI, cap_CAII, cap_total
        - fa
        - focup_M, focup_A, focup_B, focup_CU, focup_CAI, focup_CAII
        Si no hay match: todo queda NaN
    """
    # Si no hay checkpoint_id, no podemos cruzar capacidad
    if 'checkpoint_id' not in df_od.columns:
        df_od = df_od.copy()
        for col in [
            'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
            'fa',
            'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
        ]:
            df_od[col] = np.nan
        return df_od

    df_od = df_od.copy()
    df_capacity = df_capacity.copy()

    # Llaves de cruce: (checkpoint_id, sense_code) con (Checkpoint, Sentido)
    # STRICT MODE: NO convertir NaN a strings; NaN debe permanecer NaN
    df_od['checkpoint_id'] = df_od['checkpoint_id'].astype('string')
    if 'sense_code' not in df_od.columns:
        df_od['sense_code'] = pd.Series([pd.NA] * len(df_od), dtype='string')
    else:
        df_od['sense_code'] = df_od['sense_code'].astype('string')

    df_capacity['Checkpoint'] = df_capacity['Checkpoint'].astype('string')
    df_capacity['Sentido'] = df_capacity['Sentido'].astype('string')
    
    # Seleccionar solo columnas necesarias de capacity (ya agregada)
    capacity_cols = [
        'Checkpoint', 'Sentido',
        'FA',
        'M', 'A', 'B', 'CU', 'CAI', 'CAII',
        'Focup_M', 'Focup_A', 'Focup_B', 'Focup_CU', 'Focup_CAI', 'Focup_CAII',
    ]
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
    
    # Renombrar columnas de capacidad/factores a un esquema interno estable
    rename_map = {
        'FA': 'fa',
        'M': 'cap_M',
        'A': 'cap_A',
        'B': 'cap_B',
        'CU': 'cap_CU',
        'CAI': 'cap_CAI',
        'CAII': 'cap_CAII',
        'Focup_M': 'focup_M',
        'Focup_A': 'focup_A',
        'Focup_B': 'focup_B',
        'Focup_CU': 'focup_CU',
        'Focup_CAI': 'focup_CAI',
        'Focup_CAII': 'focup_CAII',
    }
    
    merged = merged.rename(columns=rename_map)
    
    # Calcular cap_total SOLO si todas las categorías están presentes.
    # STRICT MODE: si falta cualquier capacidad -> cap_total = NaN (no sumas parciales).
    cap_cols = ['cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII']
    merged['cap_total'] = merged[cap_cols].sum(axis=1, min_count=len(cap_cols))
    
    # Eliminar columnas auxiliares del merge
    if 'Checkpoint' in merged.columns:
        merged = merged.drop(columns=['Checkpoint'])
    if 'Sentido' in merged.columns:
        merged = merged.drop(columns=['Sentido'])
    
    return merged
