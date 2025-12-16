import pandas as pd
import numpy as np

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los nombres de columnas del DataFrame OD.
    """
    # Mapa de renombramiento estándar
    rename_map = {
        'origin': 'origin_id',
        'destination': 'destination_id',
        'checkpoint': 'checkpoint_id',
        'sense': 'sense_code',
        'total_trips': 'total_trips',
        'total_trips_modif': 'total_trips_adjusted'
    }
    
    # Normalizar a minúsculas y strip
    df.columns = df.columns.str.strip().str.lower()
    
    # Renombrar si existen
    # Invertir el mapa para buscar claves
    # Pero mejor iteramos
    
    # Si las columnas ya son correctas, no hacer nada
    # Si son las del archivo raw (origin, destination, etc)
    
    # Ajuste específico para el archivo de checkpoint
    if 'origin' in df.columns:
        df.rename(columns={'origin': 'origin_id'}, inplace=True)
    if 'destination' in df.columns:
        df.rename(columns={'destination': 'destination_id'}, inplace=True)
    if 'checkpoint' in df.columns:
        df.rename(columns={'checkpoint': 'checkpoint_id'}, inplace=True)
    if 'sentido' in df.columns:
        df.rename(columns={'sentido': 'sense_code'}, inplace=True)
    if 'sense' in df.columns:
        df.rename(columns={'sense': 'sense_code'}, inplace=True)
        
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
