import unittest
import pandas as pd
import numpy as np
import os
import sys
import tempfile

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kido_ruteo.pipeline import run_pipeline
from kido_ruteo.trips.calculation import calculate_vehicle_trips
from kido_ruteo.capacity.matcher import match_capacity_to_od
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
            'sense_code': ['1-3'],
            'trips_person': [100],
            'intrazonal_factor': [1]
        })
        
        self.capacity = pd.DataFrame({
            'Checkpoint': ['2001'],
            'Sentido': ['1-3'],
            'FA': [1.0],
            'M': [0], 'A': [50], 'B': [0], 'CU': [50], 'CAI': [0], 'CAII': [0],
            'Focup_M': [np.nan], 'Focup_A': [2.0], 'Focup_B': [np.nan], 'Focup_CU': [2.0], 'Focup_CAI': [np.nan], 'Focup_CAII': [np.nan]
        })

    def test_general_query_no_checkpoint(self):
        """Test that General Query (no checkpoint) results in 0 vehicles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            od_path = os.path.join(tmpdir, 'od_general.csv')
            out_dir = os.path.join(tmpdir, 'out')
            self.od_general.to_csv(od_path, index=False)

            output_file = run_pipeline(
                od_path=od_path,
                zonification_path='__unused__',
                network_path='__unused__',
                capacity_path='__unused__',
                output_dir=out_dir,
            )

            df_out = pd.read_csv(output_file)
            self.assertListEqual(
                list(df_out.columns),
                ['Origen', 'Destino', 'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total']
            )
            self.assertTrue((df_out[['veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total']] == 0).all().all())

    def test_checkpoint_query_logic(self):
        """Test strict transformation logic for Checkpoint Query."""
        df = self.od_checkpoint.copy()
        
        # 1. Match Capacity
        df = match_capacity_to_od(df, self.capacity)

        self.assertFalse(df['cap_total'].isna().iloc[0])

        # 2. Congruence (needs route validity)
        df['has_valid_path'] = True
        df = classify_congruence(df)
        self.assertEqual(df['congruence_id'].iloc[0], 1)
        
        # 3. Calculate Vehicles
        df = calculate_vehicle_trips(df)

        # cap_A=50, cap_CU=50, cap_total=100, FA=1.0, focup_A=2.0, focup_CU=2.0
        # veh_A = 100*1.0*(0.5)/2 = 25
        # veh_CU = 100*1.0*(0.5)/2 = 25
        self.assertAlmostEqual(df['veh_A'].iloc[0], 25.0, places=6)
        self.assertAlmostEqual(df['veh_CU'].iloc[0], 25.0, places=6)
        self.assertAlmostEqual(df['veh_total'].iloc[0], 50.0, places=6)

    def test_vehicle_sum_integrity(self):
        """Test that veh_total equals the sum of all vehicle categories."""
        df = self.od_checkpoint.copy()
        df = match_capacity_to_od(df, self.capacity)
        df['has_valid_path'] = True
        df = classify_congruence(df)
        df = calculate_vehicle_trips(df)
        
        row = df.iloc[0]
        veh_sum = (
            row['veh_M'] + row['veh_A'] + row['veh_B'] +
            row['veh_CU'] + row['veh_CAI'] + row['veh_CAII']
        )
        
        self.assertAlmostEqual(row['veh_total'], veh_sum, places=4)

    def test_missing_capacity_entry(self):
        """Test that missing capacity entry results in NaN vehicles (not 0)."""
        df = self.od_checkpoint.copy()
        df['sense_code'] = '999' # Invalid sense
        
        df = match_capacity_to_od(df, self.capacity)
        
        self.assertTrue(np.isnan(df['cap_total'].iloc[0]))
        df['has_valid_path'] = True
        df = classify_congruence(df)
        self.assertEqual(df['congruence_id'].iloc[0], 4)
        
        df = calculate_vehicle_trips(df)
        # Now we expect NaN, not 0.0
        self.assertTrue(np.isnan(df['veh_total'].iloc[0]))

    def test_sense_zero_not_fallback_for_directional_checkpoint(self):
        """STRICT (FLOW): en checkpoint direccional, sense_code='0' NO hace match ni agrega."""
        df = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [2],
            'checkpoint_id': ['2001'],
            'sense_code': ['0'],
            'trips_person': [100],
            'intrazonal_factor': [1]
        })
        
        # Capacity direccional (no existe Sentido='0')
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

        # No match should happen (cap_total remains NaN)
        self.assertTrue(np.isnan(df_matched['cap_total'].iloc[0]))

    def test_sense_zero_matches_for_aggregated_checkpoint(self):
        """STRICT (FLOW): en checkpoint agregado (solo Sentido='0'), se hace match por checkpoint y sense_code='0' es válido."""
        df = pd.DataFrame({
            'origin_id': [1],
            'destination_id': [2],
            'checkpoint_id': ['2002'],
            # Aunque venga distinto, en agregado se debe fijar a '0'
            'sense_code': ['1-3'],
            'trips_person': [100],
            'intrazonal_factor': [1]
        })

        cap_df = pd.DataFrame({
            'Checkpoint': ['2002'],
            'Sentido': ['0'],
            'FA': [1.0],
            'M': [10], 'A': [50], 'B': [10], 'CU': [10], 'CAI': [10], 'CAII': [10],
            'TOTAL': [100],
            'Focup_M': [1.0], 'Focup_A': [1.5], 'Focup_B': [20.0], 'Focup_CU': [1.0], 'Focup_CAI': [1.0], 'Focup_CAII': [1.0]
        })

        df_matched = match_capacity_to_od(df, cap_df)
        self.assertFalse(np.isnan(df_matched['cap_total'].iloc[0]))
        self.assertEqual(df_matched['sense_code'].iloc[0], '0')

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
            'has_valid_path': [True],
        })
        
        # Need to simulate match to get cap_total=NaN
        df_matched = match_capacity_to_od(df, self.capacity)
        
        # Classify
        df_classified = classify_congruence(df_matched)
        
        self.assertEqual(df_classified['congruence_id'].iloc[0], 4)
        self.assertEqual(df_classified['congruence_label'].iloc[0], 'Impossible')

if __name__ == '__main__':
    unittest.main()