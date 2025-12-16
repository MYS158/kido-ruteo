"""
Pipeline de validación.
"""

import pandas as pd
from .checks import calculate_validation_factor, validate_consistency
from .congruence import calculate_congruence_x, assign_congruence_nivel

def run_validation_pipeline(df_od: pd.DataFrame, df_vial: pd.DataFrame) -> pd.DataFrame:
    """
    Ejecuta el pipeline de validación completo.
    
    Args:
        df_od: DataFrame OD
        df_vial: DataFrame con datos viales
        
    Returns:
        DataFrame validado
    """
    # 1. Calcular factores E1/E2
    # (Lógica de merge y cálculo)
    
    # 2. Calcular congruencia
    df_od = calculate_congruence_x(df_od)
    df_od = assign_congruence_nivel(df_od)
    
    return df_od
