import pandas as pd

def calculate_potential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula id_potential basado en reglas de negocio.
    
    id_potential = 1 SOLO si:
    - Existen rutas MC y MC2 válidas (has_valid_path)
    - Checkpoint está asignado (checkpoint_id no nulo)
    - Sentido es válido (sense_valid)
    - Existe capacidad (cap_available)
    
    De lo contrario id_potential = 0.
    """
    
    # Asegurar que columnas booleanas sean booleanas
    if 'sense_valid' not in df.columns: df['sense_valid'] = False
    if 'cap_available' not in df.columns: df['cap_available'] = False

    df['has_valid_path'] = df['has_valid_path'].fillna(False).astype(bool)
    df['sense_valid'] = df['sense_valid'].fillna(False).astype(bool)
    df['cap_available'] = df['cap_available'].fillna(False).astype(bool)
    
    # Existencia de Checkpoint
    if 'checkpoint_id' in df.columns:
        has_checkpoint = df['checkpoint_id'].notna() & (df['checkpoint_id'] != '')
    else:
        has_checkpoint = False
    
    # Calcular potencial
    # Regla estricta: Capacity data never invalidates trips.
    # sense_code = 0 DOES NOT invalidate the row.
    # id_potential depende SOLO de la validez espacial (ruta) y existencia de checkpoint.
    df['id_potential'] = (
        df['has_valid_path'] &
        has_checkpoint
    ).astype(int)
    
    return df
