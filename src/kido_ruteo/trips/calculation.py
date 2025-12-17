import pandas as pd
import numpy as np

def calculate_vehicle_trips(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los viajes vehiculares basándose en la distribución observada en el aforo (capacidad).
    
    STRICT MODE - Reglas obligatorias:
    1. Demand adjustment: trips_person_adjusted = trips_person * FA
    2. Category split: share_X = cap_X / TOTAL
    3. Vehicle conversion: veh_X = (trips_person_adjusted * share_X) / Focup_X
    
    CRITICAL:
    - Si capacidad es NaN → veh_* = NaN (NUNCA 0)
    - Si congruence_id = 4 → veh_* = 0
    - veh_total = suma de categorías SOLO si todas son válidas
    - Filtros: id_potential=1 AND congruence_id < 4 AND intrazonal_factor=1
    """
    
    # Columnas requeridas de capacidad
    cols_cap = ['cap_moto', 'cap_auto', 'cap_bus', 'cap_cu', 'cap_cai', 'cap_caii', 'cap_total']
    cols_focup = ['focup_moto', 'focup_auto', 'focup_bus', 'focup_cu', 'focup_cai', 'focup_caii']
    
    # Asegurar existencia de columnas (rellenar con NaN si faltan para indicar ausencia de datos)
    # NO rellenar con 0, porque 0 es un valor válido de capacidad, NaN es ausencia.
    for col in cols_cap + cols_focup + ['capacity_fa']:
        if col not in df.columns:
            df[col] = np.nan
            
    # Asegurar columnas de validación
    if 'id_potential' not in df.columns: df['id_potential'] = 0
    if 'congruence_id' not in df.columns: df['congruence_id'] = 4
    if 'intrazonal_factor' not in df.columns: df['intrazonal_factor'] = 1
    
    # Factor de validez global
    # Viajes existen solo si id_potential == 1 AND congruence_id < 4 AND intrazonal_factor == 1
    # Nota: intrazonal_factor ya es 0 o 1.
    # congruence_id < 4 significa 1, 2, 3. (4 es Impossible)
    
    valid_mask = (
        (df['id_potential'] == 1) & 
        (df['congruence_id'] < 4) & 
        (df['intrazonal_factor'] == 1)
    )
    
    # 1. Demand adjustment
    # Si capacity_fa es NaN (no hubo match), trips_adjusted será NaN.
    df['trips_person_adjusted'] = df['trips_person'] * df['capacity_fa']
    
    # Evitar división por cero en cap_total
    cap_total_safe = df['cap_total'].replace(0, np.nan)
    
    categories = {
        'auto': ('cap_auto', 'focup_auto'),
        'bus':  ('cap_bus',  'focup_bus'),
        'cu':   ('cap_cu',   'focup_cu'),
        'cai':  ('cap_cai',  'focup_cai'),
        'caii': ('cap_caii', 'focup_caii')
    }
    
    veh_total_col = pd.Series(0.0, index=df.index)
    
    # Mask for missing capacity (NaN or 0)
    missing_capacity = df['cap_total'].isna() | (df['cap_total'] == 0)
    
    for cat, (col_cap, col_focup) in categories.items():
        # 2. Category split: share_X = cap_X / TOTAL
        share_x = df[col_cap] / cap_total_safe
        
        # 3. Vehicle conversion: veh_X = (trips_person_adjusted * share_X) / Focup_X
        focup_safe = df[col_focup].replace(0, np.nan)
        veh_x = (df['trips_person_adjusted'] * share_x) / focup_safe
        
        # STRICT RULE 5: Aplicar validez
        # Si invalid (congruence) -> 0.0
        # Si capacidad missing -> NaN (NUNCA 0)
        veh_x = veh_x.where(valid_mask, 0.0)
        veh_x = veh_x.mask(missing_capacity, np.nan)
        
        # Store column
        col_veh_name = f'veh_{cat}'
        df[col_veh_name] = veh_x
        
        # Accumulate total
        # STRICT: Si alguna categoría es NaN, el total debe ser NaN
        veh_total_col = veh_total_col + veh_x
        
    df['veh_total'] = veh_total_col
    
    # STRICT RULE 5: Forzar NaN en total si capacidad está ausente
    # veh_total solo existe si TODAS las categorías son válidas
    df.loc[missing_capacity, 'veh_total'] = np.nan
    
    return df
