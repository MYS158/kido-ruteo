import sys
from unittest.mock import MagicMock

import pytest
import pandas as pd
import numpy as np
import os

# Import only what we need and what is safe
# We need to be careful about how we import. 
# If we import kido_ruteo.trips.calculation, it might still trigger __init__.py
# But since we mocked pipeline, maybe it's fine.
from kido_ruteo.trips.calculation import calculate_vehicle_trips

# constrained_path imports networkx, but we mocked it, so it should import now.
# We only want to test the math logic in it.
from kido_ruteo.routing.constrained_path import get_cardinality, calculate_bearing

# Mock data for testing calculation logic
def test_vehicle_calculation_nan_logic():
    # Create a dummy dataframe
    df = pd.DataFrame({
        'trips_person': [100.0, 100.0],
        'fa': [1.0, 1.0],
        'cap_M': [0.0, np.nan],
        'cap_A': [500.0, np.nan],
        'cap_B': [0.0, np.nan],
        'cap_CU': [500.0, np.nan],
        'cap_CAI': [0.0, np.nan],
        'cap_CAII': [0.0, np.nan],
        'cap_total': [1000.0, np.nan],
        'focup_M': [np.nan, np.nan],
        'focup_A': [2.0, 2.0],
        'focup_B': [np.nan, np.nan],
        'focup_CU': [2.0, 2.0],
        'focup_CAI': [np.nan, np.nan],
        'focup_CAII': [np.nan, np.nan],
        'congruence_id': [1, 1],
        'intrazonal_factor': [0, 0],
    })
    
    # Run calculation
    result = calculate_vehicle_trips(df)
    
    # Check valid row
    assert not np.isnan(result.loc[0, 'veh_total']), "Valid row should have a value"
    assert result.loc[0, 'veh_A'] > 0
    
    # Check NaN row
    assert np.isnan(result.loc[1, 'veh_total']), "Missing capacity should result in NaN veh_total"
    assert np.isnan(result.loc[1, 'veh_A']), "Missing capacity should result in NaN veh_A"

def test_vehicle_calculation_no_moto():
    df = pd.DataFrame({
        'trips_person': [100.0], # Changed from trips_person_adjusted because function calculates it
        'fa': [1.0],
        'cap_M': [0.0],
        'cap_A': [500.0],
        'cap_B': [0.0],
        'cap_CU': [500.0],
        'cap_CAI': [0.0],
        'cap_CAII': [0.0],
        'cap_total': [1000.0],
        'focup_M': [np.nan],
        'focup_A': [2.0],
        'focup_B': [np.nan],
        'focup_CU': [2.0],
        'focup_CAI': [np.nan],
        'focup_CAII': [np.nan],
        'congruence_id': [1],
        'intrazonal_factor': [0]
    })
    # valid_mask is internal
    result = calculate_vehicle_trips(df)
    
    assert 'veh_moto' not in result.columns, "veh_moto should not be in the output"
    assert 'veh_auto' not in result.columns
    assert 'veh_A' in result.columns

def test_cardinality_logic():
    # Test basic bearings
    # 1=N, 2=E, 3=S, 4=W
    assert get_cardinality(0) == 1 # N
    assert get_cardinality(90) == 2 # E
    assert get_cardinality(180) == 3 # S
    assert get_cardinality(270) == 4 # W
    assert get_cardinality(45) == 2 # E (boundary)

def test_bearing_calculation():
    # Mock Graph
    G = MagicMock()
    # Mock nodes access: G.nodes[u]['x']
    nodes = {
        'u': {'x': 0, 'y': 0},
        'v_n': {'x': 0, 'y': 1},
        'v_e': {'x': 1, 'y': 0},
        'v_s': {'x': 0, 'y': -1},
        'v_w': {'x': -1, 'y': 0}
    }
    G.nodes = nodes
    
    # Test bearing calculation
    # N (0,0) -> (0,1)
    assert calculate_bearing(G, 'u', 'v_n') == 0.0
    # E (0,0) -> (1,0)
    assert calculate_bearing(G, 'u', 'v_e') == 90.0
    # S (0,0) -> (0,-1)
    assert calculate_bearing(G, 'u', 'v_s') == 180.0
    # W (0,0) -> (-1,0)
    assert calculate_bearing(G, 'u', 'v_w') == 270.0
