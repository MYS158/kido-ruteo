import pandas as pd
import numpy as np
import os

def load_capacity_data(file_path: str) -> pd.DataFrame:
    """
    Carga y AGREGA los datos de capacidad por Checkpoint y Sentido.
    
    STRICT MODE:
    - summary_capacity.csv contiene datos a nivel ESTACIÓN.
    - Se agrega por (Checkpoint, Sentido).
    - NO se imputan valores faltantes con 0 o 1.0 (no hay "rescates").
    - Focup se calcula como promedio ponderado por la capacidad de su categoría.
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
    
    # Columnas numéricas (no imputar)
    num_cols = ['M', 'A', 'B', 'CU', 'CAI', 'CAII', 'TOTAL']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['FA'] = pd.to_numeric(df['FA'], errors='coerce')

    focup_cols = ['Focup_M', 'Focup_A', 'Focup_B', 'Focup_CU', 'Focup_CAI', 'Focup_CAII']
    for col in focup_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- AGREGACIÓN ---
    # Capacidad: suma (min_count=1 para no convertir "todo NaN" en 0)
    group = df.groupby(['Checkpoint', 'Sentido'], as_index=False)

    df_caps = group[num_cols].sum(min_count=1)
    df_fa = group[['FA']].mean()

    # Ponderación de Focup: sum(Focup_cat * Cap_cat) / sum(Cap_cat)
    df = df.copy()
    df['w_Focup_M'] = df['Focup_M'] * df['M']
    df['w_Focup_A'] = df['Focup_A'] * df['A']
    df['w_Focup_B'] = df['Focup_B'] * df['B']
    df['w_Focup_CU'] = df['Focup_CU'] * df['CU']
    df['w_Focup_CAI'] = df['Focup_CAI'] * df['CAI']
    df['w_Focup_CAII'] = df['Focup_CAII'] * df['CAII']

    w_cols = ['w_Focup_M', 'w_Focup_A', 'w_Focup_B', 'w_Focup_CU', 'w_Focup_CAI', 'w_Focup_CAII']
    df_w = df.groupby(['Checkpoint', 'Sentido'], as_index=False)[w_cols].sum(min_count=1)

    df_agg = df_caps.merge(df_fa, on=['Checkpoint', 'Sentido'], how='left')
    df_agg = df_agg.merge(df_w, on=['Checkpoint', 'Sentido'], how='left')

    # Recalcular Focup ponderados (si capacidad=0 o NaN => Focup queda NaN)
    df_agg['Focup_M'] = df_agg['w_Focup_M'] / df_agg['M'].where(df_agg['M'] > 0)
    df_agg['Focup_A'] = df_agg['w_Focup_A'] / df_agg['A'].where(df_agg['A'] > 0)
    df_agg['Focup_B'] = df_agg['w_Focup_B'] / df_agg['B'].where(df_agg['B'] > 0)
    df_agg['Focup_CU'] = df_agg['w_Focup_CU'] / df_agg['CU'].where(df_agg['CU'] > 0)
    df_agg['Focup_CAI'] = df_agg['w_Focup_CAI'] / df_agg['CAI'].where(df_agg['CAI'] > 0)
    df_agg['Focup_CAII'] = df_agg['w_Focup_CAII'] / df_agg['CAII'].where(df_agg['CAII'] > 0)

    df_agg = df_agg.drop(columns=w_cols)
    return df_agg
