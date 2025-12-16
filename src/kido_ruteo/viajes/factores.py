"""
Módulo de factores para viajes.
"""

import pandas as pd
from datetime import datetime

def add_daily_tables(
    df: pd.DataFrame,
    fecha: str = None
) -> pd.DataFrame:
    """
    Añade columnas para tablas diarias (Paso 10).
    
    - tpdes: Tráfico promedio día entre semana
    - tpdfs: Tráfico promedio día fin de semana
    - tpds: Tráfico promedio día sábado
    
    Args:
        df: DataFrame con Viajes
        fecha: Fecha en formato 'YYYY-MM-DD'
        
    Returns:
        DataFrame con columnas diarias
    """
    df = df.copy()
    
    # Agregar fecha
    if fecha is None:
        fecha = datetime.now().strftime('%Y-%m-%d')
    
    df['fecha'] = fecha
    
    # Por ahora, factores simplificados
    # (pueden ajustarse según datos reales)
    df['tpdes'] = df['Viajes'] * 0.70  # 70% en días entre semana
    df['tpdfs'] = df['Viajes'] * 0.25  # 25% en fin de semana
    df['tpds'] = df['Viajes'] * 0.30   # 30% en sábado
    
    return df
