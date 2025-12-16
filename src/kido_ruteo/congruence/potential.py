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
    df['has_valid_path'] = df['has_valid_path'].fillna(False).astype(bool)
    df['sense_valid'] = df['sense_valid'].fillna(False).astype(bool)
    df['cap_available'] = df['cap_available'].fillna(False).astype(bool)
    
    # Existencia de Checkpoint
    has_checkpoint = df['checkpoint_id'].notna() & (df['checkpoint_id'] != '')
    
    # Calcular potencial
    df['id_potential'] = (
        df['has_valid_path'] &
        has_checkpoint &
        df['sense_valid'] &
        df['cap_available']
    ).astype(int)
    
    return df
