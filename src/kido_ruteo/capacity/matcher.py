import pandas as pd

def match_capacity_to_od(df_od: pd.DataFrame, df_capacity: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza datos de OD/Ruteo con datos de Capacidad basados en Checkpoint y Sentido.
    
    Args:
        df_od: DataFrame con info de ruteo (debe tener 'checkpoint_id' y 'sense_code')
        df_capacity: DataFrame con info de capacidad (debe tener 'Checkpoint' y 'Sentido')
        
    Returns:
        DataFrame con columnas de capacidad unidas.
    """
    # Asegurar tipos para las llaves de cruce
    df_od['checkpoint_id'] = df_od['checkpoint_id'].astype(str)
    df_capacity['Checkpoint'] = df_capacity['Checkpoint'].astype(str)
    
    df_od['sense_code'] = df_od['sense_code'].astype(str)
    df_capacity['Sentido'] = df_capacity['Sentido'].astype(str)
    
    # Cruce (Merge)
    # Usamos left join para mantener todas las filas OD
    # validate='many_to_one' asegura que no haya duplicados en capacity para la misma llave
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
    # Regla original: Si sense_code es '0', es inválido.
    # Nueva interpretación: Si hay capacidad para el sentido (incluso si es '0'), es válido.
    merged['sense_valid'] = merged['cap_available']
    
    return merged
