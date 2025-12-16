"""
Módulo de cálculo de viajes finales.
"""

import pandas as pd

def calculate_viajes(
    df: pd.DataFrame,
    id_congruencia_col: str = 'id_congruencia',
    id_potencial_col: str = 'id_potencial',
    intrazonal_col: str = 'intrazonal',
    trips_modif_col: str = 'total_trips_modif'
) -> pd.DataFrame:
    """
    Calcula Viajes según fórmula KIDO (Paso 9).
    
    Viajes = id_congruencia × id_potencial × (1-intrazonal) × total_trips_modif
    
    Args:
        df: DataFrame con datos preparados
        id_congruencia_col: Columna de id_congruencia
        id_potencial_col: Columna de id_potencial
        intrazonal_col: Columna de intrazonal
        trips_modif_col: Columna de total_trips_modif
        
    Returns:
        DataFrame con columna Viajes
    """
    df = df.copy()
    
    df['Viajes'] = (
        df[id_congruencia_col] *
        df[id_potencial_col] *
        (1 - df[intrazonal_col]) *
        df[trips_modif_col]
    )
    
    return df
