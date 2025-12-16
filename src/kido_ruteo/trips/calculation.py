import pandas as pd
import numpy as np

def calculate_vehicle_trips(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los viajes vehiculares basándose en la distribución observada en el aforo (capacidad).
    
    Fórmula:
    veh_X = trips_person * (cap_X / cap_total) / Focup_X
    
    Categorías obligatorias:
    - veh_moto
    - veh_auto
    - veh_bus
    - veh_cu
    - veh_cai
    - veh_caii
    """
    
    # Asegurar que existen las columnas de capacidad y factores de ocupación
    cols_cap = ['cap_moto', 'cap_auto', 'cap_bus', 'cap_cu', 'cap_cai', 'cap_caii', 'cap_total']
    cols_focup = ['focup_moto', 'focup_auto', 'focup_bus', 'focup_cu', 'focup_cai', 'focup_caii']
    
    for col in cols_cap + cols_focup:
        if col not in df.columns:
            df[col] = 0
            
    # Evitar división por cero en cap_total
    df['cap_total_safe'] = df['cap_total'].replace(0, np.nan)
    
    # Función auxiliar para cálculo seguro
    def calc_veh(trips, cap_x, cap_total, focup_x, potential, congruence, intrazonal_factor):
        # Flow: Viajes = id_congruencia * id_potencial * intrazonal * total_trips_modif
        # id_congruencia: 0 si Congruencia=4, 1 si no.
        # id_potencial: 1 si cumple, 0 si no.
        # intrazonal: 0 si es intrazonal, 1 si no.
        
        # Factor de congruencia (binario)
        # Si congruence_id es 4 (Impossible), factor es 0.
        cong_factor = np.where(congruence == 4, 0, 1)
        
        denominator = cap_total * focup_x
        raw_veh = (trips * cap_x) / denominator.replace(0, np.nan)
        
        # Aplicar filtros
        return raw_veh * potential * cong_factor * intrazonal_factor

    # Calcular viajes vehiculares
    # Si focup es 0 o NaN, resultará en NaN -> fillna(0)
    
    # Asegurar columnas necesarias
    if 'id_potential' not in df.columns:
        df['id_potential'] = 0
    if 'congruence_id' not in df.columns:
        df['congruence_id'] = 4 # Default to impossible if not classified
    if 'intrazonal_factor' not in df.columns:
        df['intrazonal_factor'] = 1 # Default to keep
    
    df['veh_moto'] = pd.Series(calc_veh(df['trips_person'], df['cap_moto'], df['cap_total_safe'], df['focup_moto'], df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    df['veh_auto'] = pd.Series(calc_veh(df['trips_person'], df['cap_auto'], df['cap_total_safe'], df['focup_auto'], df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    df['veh_bus']  = pd.Series(calc_veh(df['trips_person'], df['cap_bus'],  df['cap_total_safe'], df['focup_bus'],  df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    df['veh_cu']   = pd.Series(calc_veh(df['trips_person'], df['cap_cu'],   df['cap_total_safe'], df['focup_cu'],   df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    df['veh_cai']  = pd.Series(calc_veh(df['trips_person'], df['cap_cai'],  df['cap_total_safe'], df['focup_cai'],  df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    df['veh_caii'] = pd.Series(calc_veh(df['trips_person'], df['cap_caii'], df['cap_total_safe'], df['focup_caii'], df['id_potential'], df['congruence_id'], df['intrazonal_factor'])).fillna(0)
    
    # Limpieza auxiliar
    df.drop(columns=['cap_total_safe'], inplace=True)
    
    # Eliminar columnas antiguas si existen
    cols_to_remove = ['veh_light', 'veh_heavy', 'share_moto', 'share_auto', 'share_bus', 'share_heavy']
    df.drop(columns=[c for c in cols_to_remove if c in df.columns], inplace=True)
    
    return df
