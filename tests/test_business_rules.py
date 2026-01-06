
import pytest
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.congruence.classification import classify_congruence
from kido_ruteo.trips.calculation import calculate_vehicle_trips
from kido_ruteo.processing.preprocessing import prepare_data

def test_sense_zero_invalid_strict():
    """
    STRICT (FLOW.md):
    - Checkpoint direccional: sense_code es obligatorio y '0' es inválido.
    - Checkpoint agregado (Sentido='0' en capacidad): sense_code='0' es válido.
    """
    df = pd.DataFrame({
        'origin_id': ['1'],
        'destination_id': ['2'],
        'checkpoint_id': ['2001'],
        'sense_code': ['0'],
        'cap_total': [1000],
        'trips_person': [100],
        'fa': [1.0],
        'cap_M': [0], 'cap_A': [1000], 'cap_B': [0], 'cap_CU': [0], 'cap_CAI': [0], 'cap_CAII': [0],
        'focup_M': [np.nan], 'focup_A': [2.0], 'focup_B': [np.nan], 'focup_CU': [np.nan], 'focup_CAI': [np.nan], 'focup_CAII': [np.nan],
        'has_valid_path': [True],
    })

    # Classification
    df = classify_congruence(df)
    assert df.iloc[0]['congruence_id'] == 4
    
    # Trips
    df = calculate_vehicle_trips(df)
    # STRICT: congruence_id==4 => veh_* = 0 (explícito), no NaN
    assert df.iloc[0]['veh_total'] == 0.0
    assert df.iloc[0]['veh_A'] == 0.0

def test_capacity_mismatch_blocks_congruence():
    """
    STRICT: Si no existe capacidad -> congruence_id = 4
    """
    df_od = pd.DataFrame({
        'checkpoint_id': ['9999'],
        'sense_code': ['1-3'],
        'trips_person': [100],
        'has_valid_path': [True],
        'cap_total': [np.nan]
    })

    df_od = classify_congruence(df_od)
    assert df_od.iloc[0]['congruence_id'] == 4

def test_intrazonal_logic():
    """
    Regla: is_intrazonal = True si origin == destination
    """
    df = pd.DataFrame({
        'origin_id': ['1', '1'],
        'destination_id': ['1', '2'],
        'total_trips': ['10', '10']
    })
    df = prepare_data(df)
    assert df.iloc[0]['is_intrazonal'] == True
    assert df.iloc[1]['is_intrazonal'] == False


def test_congruence_distance_band_rule():
    """Si MC2 está fuera de ±10% de MC => congruence_id=4."""
    df = pd.DataFrame(
        {
            'checkpoint_id': ['2001'],
            'sense_code': ['1-3'],
            'checkpoint_is_directional': [True],
            'cap_total': [1000.0],
            'has_valid_path': [True],
            'mc_distance_m': [1000.0],
            'mc2_distance_m': [1200.0],  # +20% (fuera)
        }
    )
    df = classify_congruence(df)
    assert int(df['congruence_id'].iloc[0]) == 4
    assert str(df['congruence_reason'].iloc[0]) == 'mc2_outside_10pct_of_mc'


def test_congruence_reason_within_band():
    """Si MC2 está dentro de ±10% de MC => congruence_id=3 y motivo correspondiente."""
    df = pd.DataFrame(
        {
            'checkpoint_id': ['2001'],
            'sense_code': ['1-3'],
            'checkpoint_is_directional': [True],
            'cap_total': [1000.0],
            'has_valid_path': [True],
            'mc_distance_m': [1000.0],
            'mc2_distance_m': [910.0],  # -9% (dentro)
        }
    )
    df = classify_congruence(df)
    assert int(df['congruence_id'].iloc[0]) == 3
    assert str(df['congruence_reason'].iloc[0]) == 'mc2_within_10pct_of_mc'

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
