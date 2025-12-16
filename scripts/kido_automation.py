import pandas as pd
import numpy as np
import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point, LineString
import os
import sys
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configuration
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw'))
PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'processed'))
OUTPUT_FILE = os.path.join(PROCESSED_DIR, 'resultados_kido_automatizado.xlsx')

# Ensure processed directory exists
os.makedirs(PROCESSED_DIR, exist_ok=True)

def load_data():
    """
    Carga los datos necesarios para el procesamiento.
    """
    print(">>> Cargando datos...")
    
    # 1. Cargar df_kido (Checkpoint 2001 como ejemplo)
    # Se busca el archivo en data/raw/queries/checkpoint/
    kido_path = os.path.join(DATA_DIR, 'queries', 'checkpoint', 'checkpoint2001.csv')
    if not os.path.exists(kido_path):
        raise FileNotFoundError(f"No se encontró el archivo KIDO en: {kido_path}")
    df_kido = pd.read_csv(kido_path)
    print(f"   - KIDO cargado: {len(df_kido)} registros.")

    # 2. Cargar df_macrozonas
    macro_path = os.path.join(DATA_DIR, 'macrozones.csv')
    df_macrozonas = pd.read_csv(macro_path)
    # Clean column names (remove whitespace)
    df_macrozonas.columns = df_macrozonas.columns.str.strip()
    print(f"   - Macrozonas cargado: {len(df_macrozonas)} registros.")

    # 3. Cargar df_sentidos
    sentidos_path = os.path.join(DATA_DIR, 'valid_senses_standard.csv')
    df_sentidos = pd.read_csv(sentidos_path)
    df_sentidos.columns = df_sentidos.columns.str.strip()
    print(f"   - Sentidos cargado: {len(df_sentidos)} registros.")

    # 4. Cargar df_validacion (Factores de Ocupación)
    validacion_path = os.path.join(DATA_DIR, 'ocupation_factor.csv')
    df_validacion = pd.read_csv(validacion_path)
    df_validacion.columns = df_validacion.columns.str.strip()
    print(f"   - Validación cargado: {len(df_validacion)} registros.")

    # 5. Cargar gdf_zonas
    zonas_path = os.path.join(DATA_DIR, 'zonification', 'zonification.geojson')
    gdf_zonas = gpd.read_file(zonas_path)
    print(f"   - Zonificación cargada: {len(gdf_zonas)} registros.")

    # 6. Cargar/Generar dato_vial_tipologia.csv
    # Como no existe el archivo original, crearemos uno dummy o intentaremos cargarlo si existe
    vial_path = os.path.join(DATA_DIR, 'dato_vial_tipologia.csv')
    if os.path.exists(vial_path):
        df_vial = pd.read_csv(vial_path)
        print(f"   - Dato Vial cargado: {len(df_vial)} registros.")
    else:
        print("   ! Archivo dato_vial_tipologia.csv no encontrado. Se usará un valor dummy para validación.")
        df_vial = pd.DataFrame({'Suma de AU_OK': [10000]}) # Dummy value

    return df_kido, df_macrozonas, df_sentidos, df_validacion, gdf_zonas, df_vial

def preprocess_and_adjust(df_kido, df_macrozonas, df_sentidos):
    """
    Módulo de Pre-procesamiento y Depuración.
    """
    print(">>> Iniciando Pre-procesamiento...")
    
    df = df_kido.copy()

    # 1. total_trips_modif
    # Convertir '<10' a 1, y el resto a numérico
    def clean_trips(val):
        if isinstance(val, str):
            if '<10' in val:
                return 1
            try:
                return float(val)
            except ValueError:
                return 0
        return val

    df['total_trips_numeric'] = df['total_trips'].apply(clean_trips)
    
    # Regla: Si total_trips < 10 (o era '<10'), total_trips_modif = 1. Sino, igual.
    df['total_trips_modif'] = df['total_trips_numeric'].apply(lambda x: 1 if x < 10 else x)

    # 2. intrazonal
    df['intrazonal'] = np.where(df['destination'] == df['origin'], 1, 0)

    # 3. Claves O-D (AUX)
    df['MIN'] = df[['origin', 'destination']].min(axis=1)
    df['MAX'] = df[['origin', 'destination']].max(axis=1)
    df['AUX'] = df['MIN'].astype(str) + "-" + df['MAX'].astype(str)

    # 4. Merge de Referencias (Macrozonas)
    # Asumimos que 'ID' en macrozonas corresponde a 'origin'/'destination' en kido
    # Y que la columna de macrozona es 'ZON_2527'
    
    # Merge Origin
    df = df.merge(df_macrozonas[['ID', 'ZON_2527']], left_on='origin', right_on='ID', how='left')
    df.rename(columns={'ZON_2527': 'MACROZONA-O'}, inplace=True)
    df.drop(columns=['ID'], inplace=True)

    # Merge Destination
    df = df.merge(df_macrozonas[['ID', 'ZON_2527']], left_on='destination', right_on='ID', how='left')
    df.rename(columns={'ZON_2527': 'MACROZONA-D'}, inplace=True)
    df.drop(columns=['ID'], inplace=True)

    # 5. Merge de Sentidos
    # Crear clave compuesta AUX MACROZONA para el merge
    df['AUX_MACROZONA'] = df['MACROZONA-O'].astype(str) + "-" + df['MACROZONA-D'].astype(str)
    
    # Merge con df_sentidos
    # Renombramos 'Valido' a 'VÁLIDO_OK' para coincidir con el prompt
    df_sentidos_renamed = df_sentidos.rename(columns={'Auxiliar': 'AUX_KEY', 'Valido': 'VÁLIDO_OK'})
    
    df = df.merge(df_sentidos_renamed[['AUX_KEY', 'VÁLIDO_OK']], left_on='AUX_MACROZONA', right_on='AUX_KEY', how='left')
    df.drop(columns=['AUX_KEY'], inplace=True)
    
    # Llenar NaN en VÁLIDO_OK con 0 (por si no hay match)
    df['VÁLIDO_OK'] = df['VÁLIDO_OK'].fillna(0)

    print("   - Pre-procesamiento completado.")
    return df

def network_simulation_and_validation(df_kido, gdf_zonas=None):
    """
    Módulo de Análisis de Red y Cardinalidad (Simulado).
    """
    print(">>> Iniciando Simulación de Red...")
    
    # Simulación de DIST_MC y DIST_MC2
    np.random.seed(42)
    
    # DIST_MC: Distancia "real" (simulada)
    df_kido['DIST_MC'] = np.random.uniform(1000, 50000, len(df_kido))
    
    # DIST_MC2: Distancia constreñida (debe ser mayor o igual a DIST_MC)
    df_kido['DIST_MC2'] = df_kido['DIST_MC'] * np.random.uniform(1.0, 1.5, len(df_kido))
    
    # Cálculo de id_potencial
    # Si (DIST_MC2 / DIST_MC) < 1.10 -> 1, else 0
    df_kido['ratio_dist'] = df_kido['DIST_MC2'] / df_kido['DIST_MC']
    df_kido['id_potencial'] = np.where(df_kido['ratio_dist'] < 1.10, 1, 0)
    
    # Generar cardinalidad.geojson (simulado como dataframe exportado)
    # cardinalidad = df_kido[['origin', 'destination', 'id_potencial']].drop_duplicates()
    
    print("   - Simulación de Red completada.")
    return df_kido

def final_calculation(df_kido, df_validacion, df_vial):
    """
    Módulo de Validación y Cálculo Final.
    """
    print(">>> Iniciando Cálculo Final...")
    
    # 1. Validación de Confiabilidad
    vol_kido_inicial = df_kido['total_trips_modif'].sum()
    
    # Obtener factor de ocupación de autos (AU)
    f_ocup_au = df_validacion.iloc[0]['AU']
    
    # VolDV-personas
    if 'Suma de AU_OK' in df_vial.columns:
        vol_dv_veh = df_vial['Suma de AU_OK'].sum()
        vol_dv_personas = vol_dv_veh * f_ocup_au
    else:
        vol_dv_personas = 10000 # Fallback
        
    factor_confiabilidad = vol_dv_personas / vol_kido_inicial if vol_kido_inicial > 0 else 0
    print(f"   - Factor de Confiabilidad: {factor_confiabilidad:.3f}")
    
    if 0.95 <= factor_confiabilidad <= 1.05:
        print("     ✅ La data es confiable.")
    else:
        print("     ⚠️ La data podría no ser confiable (fuera del rango 0.95-1.05).")

    # 2. Cálculo de id_congruencia
    # Si VÁLIDO_OK == 0 -> 0, else 1
    df_kido['id_congruencia'] = np.where(df_kido['VÁLIDO_OK'] == 0, 0, 1)
    
    # 3. Cálculo Final de VIAJES
    # VIAJES = id_congruencia * id_potencial * (1 - intrazonal) * total_trips_modif
    # Nota: Se usa (1 - intrazonal) para eliminar viajes intrazonales.
    df_kido['VIAJES'] = df_kido['id_congruencia'] * df_kido['id_potencial'] * (1 - df_kido['intrazonal']) * df_kido['total_trips_modif']
    
    print("   - Cálculo final completado.")
    return df_kido

def convert_to_tpda_and_matrices(df_kido, df_validacion):
    """
    Módulo de Conversión y Matrices TPDA.
    """
    print(">>> Generando Matrices TPDA...")
    
    # Factores de Ocupación (usando primera fila)
    factors = df_validacion.iloc[0]
    
    # Proporciones (Hardcoded por falta de archivo F_TRABAJO.csv)
    prop_au_trabajo = 0.8
    prop_au_otro = 0.2
    
    # Calcular Viajes Vehículo por Tipología
    # VEH_TIPO = (VIAJES * Prop) / Factor
    
    # Autos
    df_kido['VEH_AU_TRABAJO'] = (df_kido['VIAJES'] * prop_au_trabajo) / factors['AU']
    df_kido['VEH_AU_OTRO'] = (df_kido['VIAJES'] * prop_au_otro) / factors['AU']
    
    # Otros modos
    for modo in ['M', 'BUS', 'CU', 'CAI', 'CAII']:
        if modo in factors:
            df_kido[f'VEH_{modo}'] = df_kido['VIAJES'] / factors[modo]
            
    # Generar Matrices (Pivot Tables)
    matrices = {}
    tipologias = ['VEH_AU_TRABAJO', 'VEH_AU_OTRO', 'VEH_M', 'VEH_BUS', 'VEH_CU', 'VEH_CAI', 'VEH_CAII']
    
    for tipo in tipologias:
        if tipo in df_kido.columns:
            mat = df_kido.pivot_table(index='origin', columns='destination', values=tipo, aggfunc='sum', fill_value=0)
            matrices[tipo] = mat
            
    print("   - Matrices generadas.")
    return matrices, df_kido

def main():
    try:
        # 1. Cargar
        df_kido, df_macrozonas, df_sentidos, df_validacion, gdf_zonas, df_vial = load_data()
        
        # 2. Pre-procesar
        df_processed = preprocess_and_adjust(df_kido, df_macrozonas, df_sentidos)
        
        # 3. Simulación Red
        df_simulated = network_simulation_and_validation(df_processed, gdf_zonas)
        
        # 4. Cálculo Final
        df_final = final_calculation(df_simulated, df_validacion, df_vial)
        
        # 5. Matrices
        matrices, df_export = convert_to_tpda_and_matrices(df_final, df_validacion)
        
        # 6. Exportar
        print(f">>> Exportando resultados a {OUTPUT_FILE}...")
        with pd.ExcelWriter(OUTPUT_FILE) as writer:
            df_export.to_excel(writer, sheet_name='DATA_CONSOLIDADA', index=False)
            for name, mat in matrices.items():
                sheet_name = name.replace('VEH_', 'MAT_')[:31]
                mat.to_excel(writer, sheet_name=sheet_name)
                
        print(">>> Proceso finalizado con éxito.")
        
    except Exception as e:
        print(f"!!! Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
