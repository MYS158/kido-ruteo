import unittest
import pandas as pd
import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kido_ruteo.pipeline import run_pipeline
from kido_ruteo.trips.calculation import calculate_vehicle_trips
from kido_ruteo.capacity.matcher import match_capacity_to_od
from kido_ruteo.congruence.potential import calculate_potential
from kido_ruteo.congruence.classification import classify_congruence

class TestStrictBusinessRules(unittest.TestCase):

    def setUp(self):
        # Mock Data
        self.od_general = pd.DataFrame({
            'origin_id': [1, 2],
            'destination_id': [3, 4],
            'total_trips': [100, 200],
            'trips_person': [100, 200] # Added trips_person
        })
        
        self.od_checkpoint = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [3],
            'total_trips': [100],
            'checkpoint_id': ['2001'],
            'sense_code': ['0'], # Assuming '0' is valid if capacity exists
            'trips_person': [100],
            'id_potential': [1],
            'congruence_id': [1],
            'intrazonal_factor': [1]
        })
        
        self.capacity = pd.DataFrame({
            'Checkpoint': ['2001'],
            'Sentido': ['0'],
            'FA': [1.0],
            'M': [10], 'A': [50], 'B': [10], 'CU': [10], 'CAI': [10], 'CAII': [10],
            'TOTAL': [100],
            'Focup_M': [1.0], 'Focup_A': [1.5], 'Focup_B': [20.0], 'Focup_CU': [1.0], 'Focup_CAI': [1.0], 'Focup_CAII': [1.0]
        })

    def test_general_query_no_checkpoint(self):
        """Test that General Query (no checkpoint) results in 0 vehicles."""
        # Simulate pipeline steps for General Query
        df = self.od_general.copy()
        
        # Match Capacity (should return original)
        df_matched = match_capacity_to_od(df, self.capacity)
        self.assertTrue('cap_total' not in df_matched.columns)
        
        # Calculate Potential (should handle missing cols)
        if 'checkpoint_id' not in df_matched.columns:
            df_matched['id_potential'] = 0
            
        # Calculate Vehicles
        df_veh = calculate_vehicle_trips(df_matched)
        
        self.assertEqual(df_veh['veh_total'].sum(), 0)
        self.assertTrue('veh_auto' in df_veh.columns)

    def test_checkpoint_query_logic(self):
        """Test strict transformation logic for Checkpoint Query."""
        df = self.od_checkpoint.copy()
        
        # 1. Match Capacity
        df = match_capacity_to_od(df, self.capacity)
        self.assertTrue(df['cap_available'].iloc[0])
        
        # 2. Calculate Vehicles
        df = calculate_vehicle_trips(df)
        
        veh_auto = df['veh_auto'].iloc[0]
        # 100 * 0.5 / 1.5 = 33.333
        self.assertAlmostEqual(veh_auto, 33.333333, places=4)

    def test_vehicle_sum_integrity(self):
        """Test that veh_total equals the sum of all vehicle categories."""
        df = self.od_checkpoint.copy()
        df = match_capacity_to_od(df, self.capacity)
        df = calculate_vehicle_trips(df)
        
        row = df.iloc[0]
        veh_sum = (
            row['veh_moto'] + row['veh_auto'] + row['veh_bus'] + 
            row['veh_cu'] + row['veh_cai'] + row['veh_caii']
        )
        
        self.assertAlmostEqual(row['veh_total'], veh_sum, places=4)

    def test_missing_capacity_entry(self):
        """Test that missing capacity entry results in NaN vehicles (not 0)."""
        df = self.od_checkpoint.copy()
        df['sense_code'] = '999' # Invalid sense
        
        df = match_capacity_to_od(df, self.capacity)
        
        # Should have cap_available = False (or NaN)
        self.assertFalse(df['cap_available'].fillna(False).iloc[0])
        
        # If we force id_potential=1 (which shouldn't happen if potential logic works, but let's test vehicle calc robustness)
        df = calculate_vehicle_trips(df)
        # Now we expect NaN, not 0.0
        self.assertTrue(np.isnan(df['veh_total'].iloc[0]))

    def test_sense_zero_aggregates_capacity(self):
        """Test that sense_code='0' aggregates multiple capacity rows."""
        df = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [2],
            'checkpoint_id': ['2001'],
            'sense_code': ['0'],
            'trips_person': [100],
            'id_potential': [1],
            'congruence_id': [1],
            'intrazonal_factor': [1]
        })
        
        # Capacity with 2 rows for same checkpoint
        cap_df = pd.DataFrame({
            'Checkpoint': ['2001', '2001'],
            'Sentido': ['1', '2'],
            'FA': [1.0, 1.0],
            'M': [10, 10], 'A': [50, 50], 'B': [10, 10], 'CU': [10, 10], 'CAI': [10, 10], 'CAII': [10, 10],
            'TOTAL': [100, 100],
            'Focup_M': [1.0, 1.0], 'Focup_A': [1.5, 1.5], 'Focup_B': [20.0, 20.0], 'Focup_CU': [1.0, 1.0], 'Focup_CAI': [1.0, 1.0], 'Focup_CAII': [1.0, 1.0]
        })
        
        # Match
        df_matched = match_capacity_to_od(df, cap_df)
        
        # Should have aggregated capacity
        # Total Cap = 100 + 100 = 200
        self.assertEqual(df_matched['cap_total'].iloc[0], 200)
        # Cap Auto = 50 + 50 = 100
        self.assertEqual(df_matched['cap_auto'].iloc[0], 100)

    def test_missing_capacity_keeps_trips_person(self):
        """Test that missing capacity does NOT zero trips_person."""
        df = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [2],
            'checkpoint_id': ['9999'], # No capacity
            'sense_code': ['1'],
            'trips_person': [123.45],
            'id_potential': [1],
            'congruence_id': [1],
            'intrazonal_factor': [1]
        })
        
        df_matched = match_capacity_to_od(df, self.capacity)
        df_veh = calculate_vehicle_trips(df_matched)
        
        # trips_person must be preserved
        self.assertEqual(df_veh['trips_person'].iloc[0], 123.45)
        
        # veh_total should be NaN (or 0 if we decided that, but user said NULL/NaN)
        # In our implementation we used NaN for veh_X and veh_total
        self.assertTrue(np.isnan(df_veh['veh_total'].iloc[0]))

    def test_checkpoint_query_never_drops_rows(self):
        """Test that row count is preserved even if capacity is missing."""
        df = pd.DataFrame({
            'origin_id': [1, 2],
            'destination_id': [2, 3],
            'checkpoint_id': ['2001', '9999'], # One valid, one missing cap
            'sense_code': ['1', '1'],
            'trips_person': [100, 100]
        })
        
        df_matched = match_capacity_to_od(df, self.capacity)
        self.assertEqual(len(df_matched), 2)

    def test_congruence_4_when_no_capacity_but_route_exists(self):
        """Test that congruence is 4 if capacity is missing."""
        df = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [2],
            'checkpoint_id': ['9999'], # No capacity
            'sense_code': ['1'],
            'trips_person': [100],
            'id_potential': [1], # Route exists
            'e1_route_score': [1.0],
            'e2_capacity_score': [0.0]
        })
        
        # Need to simulate match to get cap_total=NaN
        df_matched = match_capacity_to_od(df, self.capacity)
        
        # Classify
        df_classified = classify_congruence(df_matched)
        
        self.assertEqual(df_classified['congruence_id'].iloc[0], 4)
        self.assertEqual(df_classified['congruence_label'].iloc[0], 'Impossible')

if __name__ == '__main__':
    unittest.main()