
import pytest
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.congruence.potential import calculate_potential
from kido_ruteo.congruence.classification import classify_congruence
from kido_ruteo.congruence.scoring import calculate_scores
from kido_ruteo.trips.calculation import calculate_vehicle_trips
from kido_ruteo.processing.preprocessing import prepare_data

def test_sense_zero_invalid_strict():
    """
    Regla: Si sense_code == 0:
    id_potential = 0
    congruence_id = 4 (Imposible)
    e1_route_score = 0
    e2_capacity_score = 0
    All vehicle trips = 0
    """
    df = pd.DataFrame({
        'origin_id': ['1'],
        'destination_id': ['2'],
        'checkpoint_id': ['2001'],
        'sense_code': ['0'],
        'mc_distance_m': [1000],
        'mc2_distance_m': [1000],
        'cap_total': [1000],
        'trips_person': [100],
        'cap_moto': [10], 'focup_moto': [1],
        'cap_auto': [10], 'focup_auto': [1],
        'cap_bus': [10], 'focup_bus': [1],
        'cap_cu': [10], 'focup_cu': [1],
        'cap_cai': [10], 'focup_cai': [1],
        'cap_caii': [10], 'focup_caii': [1],
        'cap_total_safe': [1000]
    })
    
    # Matcher logic (simulated)
    df['cap_available'] = True
    df['sense_valid'] = False # sense_code is 0
    df['has_valid_path'] = True
    
    # Potential
    df = calculate_potential(df)
    assert df.iloc[0]['id_potential'] == 0, "id_potential debe ser 0 si sense_code es 0"
    
    # Scoring (E1, E2)
    df = calculate_scores(df)
    assert df.iloc[0]['e1_route_score'] == 0.0, "E1 debe ser 0 si sense_code es 0"
    assert df.iloc[0]['e2_capacity_score'] == 0.0, "E2 debe ser 0 si sense_code es 0"
    
    # Classification
    df = classify_congruence(df)
    assert df.iloc[0]['congruence_id'] == 4, "congruence_id debe ser 4 si id_potential es 0"
    
    # Trips
    df = calculate_vehicle_trips(df)
    assert df.iloc[0]['veh_moto'] == 0.0, "Viajes deben ser 0"
    assert df.iloc[0]['veh_auto'] == 0.0, "Viajes deben ser 0"

def test_capacity_mismatch_e2_zero():
    """
    Regla: Si no existe match de capacidad -> E2 = 0
    """
    df_od = pd.DataFrame({
        'checkpoint_id': ['9999'],
        'sense_code': ['1-3'],
        'trips_person': [100],
        'mc_distance_m': [1000],
        'mc2_distance_m': [1000],
        'id_potential': [1],
        'cap_total': [np.nan] # No match
    })
    
    df_od = calculate_scores(df_od)
    assert df_od.iloc[0]['e2_capacity_score'] == 0.0, "E2 debe ser 0 si no hay capacidad"

def test_intrazonal_logic():
    """
    Regla: intrazonal = True si origin == destination
    """
    df = pd.DataFrame({
        'origin_id': ['1', '1'],
        'destination_id': ['1', '2'],
        'total_trips': ['10', '10']
    })
    df = prepare_data(df)
    assert df.iloc[0]['intrazonal'] == True
    assert df.iloc[1]['intrazonal'] == False

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
