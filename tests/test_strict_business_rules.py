import pytest
import pandas as pd
import numpy as np
import os
# from kido_ruteo.pipeline import run_pipeline_for_file
# Assuming run_pipeline_for_file is a function we can expose or we mock the pipeline run.
# Since run_pipeline_for_file doesn't exist in the current pipeline.py (it has run_pipeline which does everything),
# we might need to refactor pipeline.py to allow running for a single file or dataframe for testing.
# For now, I will mock the dataframe transformation steps or assume we can import the processing functions.

# To make these tests runnable, I will import the specific functions that implement the logic
# and test them in isolation or sequence, simulating "run_pipeline".

from kido_ruteo.processing.preprocessing import normalize_column_names, prepare_data
from kido_ruteo.capacity.matcher import match_capacity_to_od
from kido_ruteo.congruence.scoring import calculate_scores
from kido_ruteo.congruence.potential import calculate_potential
from kido_ruteo.congruence.classification import classify_congruence
from kido_ruteo.trips.calculation import calculate_vehicle_trips

# Mock data creation
def create_mock_df(checkpoint_id='2001', sense_code='1', trips=10):
    return pd.DataFrame({
        'origin_id': ['1'],
        'destination_id': ['2'],
        'checkpoint_id': [checkpoint_id],
        'sense_code': [sense_code],
        'trips_person': [trips],
        'mc_distance_m': [1000],
        'mc2_distance_m': [1200],
        'total_trips': [trips],
        'has_valid_path': [True]
    })

def create_mock_capacity():
    return pd.DataFrame({
        'Checkpoint': ['2001', '2001'],
        'Sentido': ['1', '2'],
        'cap_total': [1000, 2000],
        'cap_moto': [100, 200],
        'cap_auto': [500, 1000],
        'cap_bus': [100, 200],
        'cap_cu': [100, 200],
        'cap_cai': [100, 200],
        'cap_caii': [100, 200],
        'focup_moto': [1, 1],
        'focup_auto': [1.5, 1.5],
        'focup_bus': [20, 20],
        'focup_cu': [1.2, 1.2],
        'focup_cai': [1.1, 1.1],
        'focup_caii': [1.1, 1.1]
    })

# Helper to simulate pipeline run
def run_pipeline_mock(df, cap_df):
    # 1. Ingest (Mocked by creation)
    # 2. Sense Validation (Need to implement strict rule)
    # In matcher.py or pipeline.py
    
    # Simulate Match Capacity
    df = match_capacity_to_od(df, cap_df)
    
    # Simulate Potential
    df = calculate_potential(df)
    
    # Simulate Scoring
    df = calculate_scores(df)
    
    # Simulate Congruence
    df = classify_congruence(df)
    
    # Simulate Vehicle Trips
    df = calculate_vehicle_trips(df)
    
    return df
    
    # Simulate Vehicle Trips
    df = calculate_vehicle_trips(df)
    
    return df

# 🧪 Test 1 — Checkpoint inmutable
def test_checkpoint_is_read_only():
    # This test verifies that throughout the transformation, checkpoint_id remains '2001'
    df = create_mock_df(checkpoint_id='2001')
    cap_df = create_mock_capacity()
    
    result = run_pipeline_mock(df, cap_df)
    
    assert (result["checkpoint_id"] == '2001').all()
    # Ensure it wasn't converted to int or float if it started as string, or vice versa if strict
    # The prompt says "If input is checkpoint2001.csv, then checkpoint_id = 2001"
    # Usually IDs are strings to avoid math operations.
    
# 🧪 Test 2 — Capacidad indexada correctamente
def test_capacity_depends_on_checkpoint_and_sense():
    # Create DF with same checkpoint but different senses
    df = pd.concat([
        create_mock_df(checkpoint_id='2001', sense_code='1'),
        create_mock_df(checkpoint_id='2001', sense_code='2')
    ])
    cap_df = create_mock_capacity() # Has different caps for sense 1 and 2
    
    result = run_pipeline_mock(df, cap_df)
    
    # Check that e2_capacity_score or cap_total is different
    # Note: E2 depends on demand/capacity. If demand is same (10 trips), and capacity differs (1000 vs 2000),
    # E2 score might be same (1.0) if both ratios are low.
    # Let's check 'cap_total' which is merged in.
    
    assert result.loc[result['sense_code'] == '1', 'cap_total'].iloc[0] == 1000
    assert result.loc[result['sense_code'] == '2', 'cap_total'].iloc[0] == 2000

# 🧪 Test 3 — Sentido inválido mata el potencial
def test_invalid_sense_forces_impossible():
    df = create_mock_df(checkpoint_id='2001', sense_code='0')
    cap_df = create_mock_capacity() # No capacity for sense '0'
    
    result = run_pipeline_mock(df, cap_df)
    
    # Strict rule: sense '0' -> sense_valid = False -> id_potential = 0 -> congruence = 4
    assert (result["id_potential"] == 0).all()
    assert (result["congruence_id"] == 4).all()

# 🧪 Test 4 — Viajes solo si hay potencial
def test_no_vehicle_trips_without_potential():
    # Case where potential is 0 (e.g. invalid sense)
    df = create_mock_df(checkpoint_id='2001', sense_code='0')
    cap_df = create_mock_capacity()
    
    result = run_pipeline_mock(df, cap_df)
    
    no_pot = result[result["id_potential"] == 0]
    veh_cols = ["veh_moto","veh_auto","veh_bus","veh_cu","veh_cai","veh_caii"]
    
    assert (no_pot[veh_cols].sum(axis=1) == 0).all()

# 🧪 Test 5 — Invarianza de filas (No expansión)
def test_capacity_does_not_expand_rows():
    # Input: 1 row
    df = create_mock_df(checkpoint_id='2001', sense_code='1')
    cap_df = create_mock_capacity()
    
    # Even if capacity has multiple entries for other senses or checkpoints,
    # the output should still be 1 row because we match on (checkpoint, sense).
    # Let's ensure capacity has multiple entries for this checkpoint (already does: 1 and 2)
    
    result = run_pipeline_mock(df, cap_df)
    
    assert len(result) == len(df)

# 🧪 Test 6 — Sentido inválido (Validación explícita)
def test_invalid_sense_validation_flags():
    df = create_mock_df(checkpoint_id='2001', sense_code='999') # Invalid sense
    cap_df = create_mock_capacity()
    
    result = run_pipeline_mock(df, cap_df)
    
    row = result.iloc[0]
    # sense_valid should be False because '999' is not in cap_df
    assert row["sense_valid"] is False or row["sense_valid"] == False
    assert row["id_potential"] == 0
    assert row["congruence_id"] == 4
