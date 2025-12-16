import pandas as pd
import numpy as np
import os

def load_capacity_data(file_path: str) -> pd.DataFrame:
    """
    Carga y AGREGA los datos de capacidad por Checkpoint y Sentido.
    
    Reglas:
    - summary_capacity.csv contiene datos a nivel ESTACIÓN.
    - Se debe agregar (SUM) la capacidad de todas las estaciones para un mismo (Checkpoint, Sentido).
    - Los factores de ocupación (Focup) se promedian ponderados por la capacidad vehicular correspondiente.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Capacity file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Normalizar columnas
    df.columns = df.columns.str.strip()
    
    required_cols = [
        'Checkpoint', 'Sentido', 'FA', 
        'M', 'A', 'B', 'CU', 'CAI', 'CAII', 'TOTAL',
        'Focup_M', 'Focup_A', 'Focup_B', 'Focup_CU', 'Focup_CAI', 'Focup_CAII'
    ]
    
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in capacity data: {missing}")
        
    # Asegurar tipos
    df['Checkpoint'] = df['Checkpoint'].astype(str)
    df['Sentido'] = df['Sentido'].astype(str)
    
    # Columnas numéricas
    num_cols = ['M', 'A', 'B', 'CU', 'CAI', 'CAII', 'TOTAL']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    focup_cols = ['Focup_M', 'Focup_A', 'Focup_B', 'Focup_CU', 'Focup_CAI', 'Focup_CAII']
    for col in focup_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- AGREGACIÓN ---
    # Definir funciones de agregación
    # Capacidad: Suma
    agg_dict = {col: 'sum' for col in num_cols}
    
    # FA: Promedio (asumimos que es similar para el mismo checkpoint/sentido)
    # O mejor, promedio ponderado por TOTAL?
    # El prompt dice "FA proviene exclusivamente de summary_capacity.csv".
    # Si hay múltiples estaciones, FA debería ser representativo. Usaremos promedio simple por seguridad.
    agg_dict['FA'] = 'mean'
    
    # Para Focup, necesitamos calcular ponderados.
    # Como groupby.agg no soporta ponderados directos fácilmente, lo hacemos manual o en dos pasos.
    # Estrategia: Calcular (Focup * Cap) antes de agrupar, sumar eso, y luego dividir por suma de Cap.
    
    df['w_Focup_M'] = df['Focup_M'] * df['M']
    df['w_Focup_A'] = df['Focup_A'] * df['A']
    df['w_Focup_B'] = df['Focup_B'] * df['B']
    df['w_Focup_CU'] = df['Focup_CU'] * df['CU']
    df['w_Focup_CAI'] = df['Focup_CAI'] * df['CAI']
    df['w_Focup_CAII'] = df['Focup_CAII'] * df['CAII']
    
    w_cols = ['w_Focup_M', 'w_Focup_A', 'w_Focup_B', 'w_Focup_CU', 'w_Focup_CAI', 'w_Focup_CAII']
    for col in w_cols:
        agg_dict[col] = 'sum'
        
    # Agrupar
    df_agg = df.groupby(['Checkpoint', 'Sentido'], as_index=False).agg(agg_dict)
    
    # Recalcular Focup ponderados
    # Evitar división por cero
    df_agg['Focup_M'] = df_agg['w_Focup_M'] / df_agg['M'].replace(0, np.nan)
    df_agg['Focup_A'] = df_agg['w_Focup_A'] / df_agg['A'].replace(0, np.nan)
    df_agg['Focup_B'] = df_agg['w_Focup_B'] / df_agg['B'].replace(0, np.nan)
    df_agg['Focup_CU'] = df_agg['w_Focup_CU'] / df_agg['CU'].replace(0, np.nan)
    df_agg['Focup_CAI'] = df_agg['w_Focup_CAI'] / df_agg['CAI'].replace(0, np.nan)
    df_agg['Focup_CAII'] = df_agg['w_Focup_CAII'] / df_agg['CAII'].replace(0, np.nan)
    
    # Rellenar NaNs en Focup (si capacidad era 0) con promedios globales o 1.0
    # Usaremos 1.0 como fallback seguro
    for col in focup_cols:
        df_agg[col] = df_agg[col].fillna(1.0)
        
    # Limpiar columnas auxiliares
    df_agg.drop(columns=w_cols, inplace=True)
    
    return df_agg
