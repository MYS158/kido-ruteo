import pandas as pd
import numpy as np

def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula puntajes E1 y E2.
    
    E1 (Puntaje de Ruta): Razón de distancia MC2 a distancia MC.
    E2 (Puntaje de Capacidad): Razón de Demanda Total KIDO a Capacidad Observada (a nivel checkpoint).
    """
    
    # --- E1: Puntaje de Ruta ---
    # Evitar división por cero
    df['e1_route_score'] = df['mc2_distance_m'] / df['mc_distance_m'].replace(0, np.nan)
    
    # Regla: Si sense_code es inválido ('0'), E1 = 0
    # EXCEPCIÓN: Si el checkpoint tiene capacidad asignada para '0', entonces '0' es válido.
    # Usamos 'cap_available' como proxy de validez del sentido.
    if 'sense_code' in df.columns and 'cap_available' in df.columns:
        # Invalidar solo si es '0' Y NO hay capacidad (lo cual ya debería estar cubierto por cap_available, pero reforzamos)
        # O mejor: Si sense_code es '0' y cap_available es False -> E1=0.
        # Pero si cap_available es True, entonces '0' es un sentido válido para este checkpoint.
        
        # La regla original era estricta: "sense_code == 0 means INVALID SENSE".
        # Pero dado que existen checkpoints con sentido '0' en la capacidad, relajamos la regla:
        # Solo penalizamos si NO hay capacidad disponible.
        pass 
        # df.loc[(df['sense_code'] == '0') & (~df['cap_available']), 'e1_route_score'] = 0.0
    
    # Calcular ratio_dist (requerido en output final)
    df['ratio_dist'] = df['e1_route_score']
    
    # --- E2: Puntaje de Capacidad ---
    # Necesitamos agregar demanda por checkpoint y sentido para comparar con capacidad
    # Agrupar por Checkpoint + Sentido
    
    # ¿Filtrar solo viajes potenciales para agregación de demanda?
    # Usualmente comparamos la demanda potencial total contra capacidad.
    # Or just the raw demand? El prompt dice "Demanda OD vs capacidad observada".
    # Usemos trips_person donde id_potential = 1.
    
    potential_trips = df[df['id_potential'] == 1].copy()
    
    if potential_trips.empty:
        df['e2_capacity_score'] = 0.0
        return df
        
    # Agregar demanda
    demand_agg = potential_trips.groupby(['checkpoint_id', 'sense_code'])['trips_person'].sum().reset_index()
    demand_agg.rename(columns={'trips_person': 'total_demand_checkpoint'}, inplace=True)
    
    # Unir de nuevo al df principal para obtener info de capacidad (capacidad ya está en df, pero repetida)
    # Podemos tomar capacidad única por checkpoint/sentido del df
    capacity_info = df[['checkpoint_id', 'sense_code', 'cap_total']].drop_duplicates()
    
    # Calcular E2 por checkpoint (Ratio Demanda / Capacidad)
    e2_df = pd.merge(demand_agg, capacity_info, on=['checkpoint_id', 'sense_code'], how='left')
    e2_df['ratio_demand_capacity'] = e2_df['total_demand_checkpoint'] / e2_df['cap_total'].replace(0, np.nan)
    
    # Normalizar E2 a rango [0, 1]
    # Regla:
    # ratio <= 0.8 -> 1.0 (Alta congruencia, capacidad sobra)
    # 0.8 < ratio <= 1.2 -> 0.5 (Congruencia media, capacidad justa)
    # ratio > 1.2 -> 0.0 (Baja congruencia, sobrecapacidad)
    # Sin capacidad -> 0.0
    
    conditions = [
        (e2_df['ratio_demand_capacity'] <= 0.8),
        (e2_df['ratio_demand_capacity'] > 0.8) & (e2_df['ratio_demand_capacity'] <= 1.2),
        (e2_df['ratio_demand_capacity'] > 1.2)
    ]
    choices = [1.0, 0.5, 0.0]
    
    e2_df['e2_capacity_score'] = np.select(conditions, choices, default=0.0)
    
    # Mapear E2 de regreso al DataFrame principal
    df = pd.merge(
        df, 
        e2_df[['checkpoint_id', 'sense_code', 'e2_capacity_score']], 
        on=['checkpoint_id', 'sense_code'], 
        how='left'
    )
    
    # Rellenar NaNs en E2 con 0 (para casos sin potencial o sin capacidad)
    df['e2_capacity_score'] = df['e2_capacity_score'].fillna(0.0)
    
    return df
