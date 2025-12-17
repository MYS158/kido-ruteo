import pandas as pd
import numpy as np

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los nombres de columnas del DataFrame OD.
    
    STRICT MODE: El 'sense_code' NUNCA se lee del input.
    Se elimina cualquier columna relacionada con sentido.
    """
    # Normalizar a minúsculas y strip
    df.columns = df.columns.str.strip().str.lower()
    
    # Renombrar columnas estándar
    if 'origin' in df.columns:
        df.rename(columns={'origin': 'origin_id'}, inplace=True)
    if 'destination' in df.columns:
        df.rename(columns={'destination': 'destination_id'}, inplace=True)
    if 'checkpoint' in df.columns:
        df.rename(columns={'checkpoint': 'checkpoint_id'}, inplace=True)
    
    # STRICT RULE: Eliminar CUALQUIER columna de sentido del input
    # El sentido SOLO se deriva geométricamente en compute_mc2_matrix
    cols_to_drop = []
    for col in df.columns:
        if col in ['sentido', 'sense', 'sense_code', 'direccion', 'direction']:
            cols_to_drop.append(col)
    
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        print(f"⚠️  STRICT MODE: Columnas de sentido eliminadas del input: {cols_to_drop}")
        print("    El sentido se derivará geométricamente de la ruta MC2.")
        
    return df

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y prepara los datos OD.
    """
    # 1. Limpiar total_trips -> trips_person
    if 'total_trips' in df.columns:
        # Convertir '<10' a 1 o similar
        df['trips_person'] = pd.to_numeric(df['total_trips'], errors='coerce')
        
        # Manejo específico de '<10' si existe
        mask_low_str = df['total_trips'].astype(str).str.contains('<', na=False)
        df.loc[mask_low_str, 'trips_person'] = 1
        
        # Manejo numérico: si es menor a 10, asignar 1
        # (Asegurando que no afecte a los que ya eran 1 o NaN rellenos)
        df.loc[df['trips_person'] < 10, 'trips_person'] = 1
        
        # Rellenar NaNs con 1 (conservador)
        df['trips_person'] = df['trips_person'].fillna(1)
    else:
        df['trips_person'] = 1.0
        
    # 2. Asegurar IDs como string
    for col in ['origin_id', 'destination_id', 'checkpoint_id', 'sense_code']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('.0', '', regex=False)
            
    # 3. Calcular intrazonal
    # Flow: SI es intrazonal -> intrazonal=0 (factor), NO -> intrazonal=1
    if 'origin_id' in df.columns and 'destination_id' in df.columns:
        # Si origen == destino, es intrazonal -> factor 0
        # Si origen != destino, no es intrazonal -> factor 1
        df['intrazonal_factor'] = np.where(df['origin_id'] == df['destination_id'], 0, 1)
        # Mantener flag booleano por si acaso
        df['is_intrazonal'] = df['origin_id'] == df['destination_id']
    else:
        df['intrazonal_factor'] = 1
        df['is_intrazonal'] = False
            
    return df
