import pandas as pd
import numpy as np

def calculate_vehicle_trips(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los viajes vehiculares usando ocupación fija por categoría.
    
    STRICT MODE - Reglas obligatorias:
    1. Fórmula: veh_X = (trips_person / ocupacion_X) × intrazonal_factor
    2. Ocupación fija: AU=1.5, CU=2.5, CAI=12.0, CAII=25.0
    3. Si cap_total es NaN → TODOS los veh_* = NaN (NUNCA 0)
    4. veh_total = suma de categorías SOLO si todas son válidas, sino NaN
    5. No usar shares, focup ni FA
    """
    
    # Factores de ocupación vehicular fijos (personas/vehículo)
    OCCUPANCY = {
        'auto': 1.5,   # veh_AU
        'cu': 2.5,     # veh_CU
        'cai': 12.0,   # veh_CAI
        'caii': 25.0   # veh_CAII
    }
    
    # Asegurar columnas requeridas
    if 'trips_person' not in df.columns:
        df['trips_person'] = 1.0
    if 'intrazonal_factor' not in df.columns:
        df['intrazonal_factor'] = 1.0
    if 'cap_total' not in df.columns:
        df['cap_total'] = np.nan
    
    # Identificar filas sin capacidad (missing capacity)
    missing_capacity = df['cap_total'].isna() | (df['cap_total'] == 0)
    
    # Calcular viajes vehiculares por categoría
    for cat_key, occupancy in OCCUPANCY.items():
        veh_col = f'veh_{cat_key}'
        
        # Fórmula base: trips_person / ocupacion × intrazonal_factor
        df[veh_col] = (df['trips_person'] / occupancy) * df['intrazonal_factor']
        
        # STRICT MODE: Si cap_total es NaN → veh_* = NaN (propagar)
        df.loc[missing_capacity, veh_col] = np.nan
    
    # Calcular veh_total
    veh_cols = ['veh_auto', 'veh_cu', 'veh_cai', 'veh_caii']
    
    # Suma SOLO si todas las categorías son válidas (no NaN)
    all_valid = df[veh_cols].notna().all(axis=1)
    
    # Inicializar veh_total con NaN
    df['veh_total'] = np.nan
    
    # Calcular suma solo donde todas las categorías son válidas
    df.loc[all_valid, 'veh_total'] = df.loc[all_valid, veh_cols].sum(axis=1)
    
    return df
