"""
Módulo de agregaciones y conversión a vehículos.
"""

import pandas as pd

def convert_to_vehicle_trips(
    df: pd.DataFrame,
    datos_viales: pd.DataFrame = None,
    tipologia_col: str = 'tipologia'
) -> pd.DataFrame:
    """
    Convierte viajes a viajes vehículo (Paso 11).
    
    - Multiplicar dato vial × factor ocupación
    - Obtener TPDA (Tráfico Promedio Diario Anual)
    - Comparar KIDO vs Vial: E2/E1
    
    Args:
        df: DataFrame con Viajes
        datos_viales: DataFrame con datos viales por tipología
        tipologia_col: Columna de tipología
        
    Returns:
        DataFrame con viajes vehiculares
    """
    # Implementación simplificada
    # Se requiere lógica de merge con datos viales y factores
    return df

def generate_matrices_by_typology(
    df: pd.DataFrame,
    typologies: list = ['A', 'B', 'C']
) -> dict:
    """
    Genera matrices OD por tipología.
    
    Args:
        df: DataFrame con viajes vehiculares
        typologies: Lista de tipologías
        
    Returns:
        Diccionario {tipologia: DataFrame_matriz}
    """
    matrices = {}
    for tipo in typologies:
        # Filtrar o calcular por tipo
        # Placeholder
        matrices[tipo] = pd.DataFrame()
    return matrices
