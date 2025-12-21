"""
KIDO-Ruteo v2.0 - STRICT MODE Tests

Tests obligatorios que validan:
1. El sentido NO se lee del input
2. El sentido SIEMPRE se deriva de la geometría
3. NO existe fallback a Sentido 0
4. Sin match exacto → veh_* = NaN (NUNCA 0)
5. veh_total solo existe si todas las categorías son válidas
"""

import pandas as pd
import numpy as np
import pytest
import sys
import os
import importlib.util

# Import modules directly from file path to avoid package init issues
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import matcher
file_path_matcher = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kido_ruteo/capacity/matcher.py'))
matcher = import_module_from_path("matcher", file_path_matcher)
match_capacity_to_od = matcher.match_capacity_to_od

# Import preprocessing
file_path_preprocessing = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kido_ruteo/processing/preprocessing.py'))
preprocessing = import_module_from_path("preprocessing", file_path_preprocessing)
normalize_column_names = preprocessing.normalize_column_names


class TestStrictCapacityMatching:
    """Test suite for STRICT MODE capacity matching"""
    
    def test_no_fallback_to_sense_zero(self):
        """
        REGLA 3: NO existe fallback a Sentido 0.
        Si el sentido específico no existe, capacidad = NaN.
        """
        # OD Data: Checkpoint 1-3, Sense 4-2 (Derived from geometry)
        df_od = pd.DataFrame({
            'checkpoint_id': ['1-3'],
            'sense_code': ['4-2'],
            'trips_person': [100]
        })
        
        # Capacity Data: Checkpoint 1-3 has Sense '0' and '1-3' (but NEVER fallback to '0')
        # It does NOT have '4-2'.
        df_capacity = pd.DataFrame({
            'Checkpoint': ['1-3', '1-3'],
            'Sentido': ['0', '1-3'],
            'FA': [1.0, 1.0],
            'M': [100, 50],
            'A': [100, 50],
            'B': [100, 50],
            'CU': [100, 50],
            'CAI': [100, 50],
            'CAII': [100, 50],
            'Focup_M': [1.0, 1.0],
            'Focup_A': [1.0, 1.0],
            'Focup_B': [1.0, 1.0],
            'Focup_CU': [1.0, 1.0],
            'Focup_CAI': [1.0, 1.0],
            'Focup_CAII': [1.0, 1.0],
        })
        
        result = match_capacity_to_od(df_od, df_capacity)
        
        # Assertions: Capacity should be NaN because '4-2' != '0' and '4-2' != '1-3'
        assert pd.isna(result.iloc[0]['cap_total']), "❌ REGLA 3: Capacidad debe ser NaN para sentido no coincidente"
        for col in ['cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'fa', 'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII']:
            assert pd.isna(result.iloc[0][col]), f"❌ REGLA 3: {col} debe ser NaN"
        print("✅ Test 1: NO fallback a Sentido 0 - PASSED")

    def test_exact_match_works(self):
        """
        REGLA 3: Cruce EXACTO funciona correctamente.
        """
        df_od = pd.DataFrame({
            'checkpoint_id': ['1-3'],
            'sense_code': ['1-3'],
            'trips_person': [100]
        })
        
        df_capacity = pd.DataFrame({
            'Checkpoint': ['1-3'],
            'Sentido': ['1-3'],
            'FA': [1.5],
            'M': [50], 'A': [100], 'B': [50], 'CU': [100], 'CAI': [100], 'CAII': [100],
            'Focup_M': [1], 'Focup_A': [2], 'Focup_B': [1], 'Focup_CU': [2], 'Focup_CAI': [2], 'Focup_CAII': [2]
        })
        
        result = match_capacity_to_od(df_od, df_capacity)
        
        assert result.iloc[0]['cap_total'] == 500, "❌ cap_total debe ser 500"
        assert result.iloc[0]['fa'] == 1.5, "❌ fa debe ser 1.5"
        assert result.iloc[0]['cap_A'] == 100, "❌ cap_A debe ser 100"
        assert result.iloc[0]['cap_CU'] == 100, "❌ cap_CU debe ser 100"
        print("✅ Test 2: Match exacto - PASSED")

    def test_sense_not_read_from_input(self):
        """
        REGLA 1: El sentido NO se lee del input.
        Se elimina cualquier columna sense/sentido del input.
        """
        df_input = pd.DataFrame({
            'origin': [1],
            'destination': [2],
            'checkpoint': ['1-3'],
            'sentido': ['BAD_VALUE'],  # This should be REMOVED
            'sense': ['ALSO_BAD'],      # This should also be REMOVED
            'total_trips': [100]
        })
        
        df_cleaned = normalize_column_names(df_input)
        
        assert 'sentido' not in df_cleaned.columns, "❌ REGLA 1: 'sentido' debe ser eliminado del input"
        assert 'sense' not in df_cleaned.columns, "❌ REGLA 1: 'sense' debe ser eliminado del input"
        assert 'sense_code' not in df_cleaned.columns, "❌ REGLA 1: 'sense_code' no debe existir en input"
        assert 'origin_id' in df_cleaned.columns, "❌ 'origin_id' debe existir"
        assert 'checkpoint_id' in df_cleaned.columns, "❌ 'checkpoint_id' debe existir"
        print("✅ Test 3: Sentido NO se lee del input - PASSED")

    def test_multiple_missing_senses(self):
        """
        REGLA 4: Sin match exacto → veh_* = NaN (NUNCA 0).
        Múltiples viajes con sentidos faltantes.
        """
        df_od = pd.DataFrame({
            'checkpoint_id': ['1-3', '1-3', '2-5'],
            'sense_code': ['4-2', '3-1', '2-4'],  # None of these exist in capacity
            'trips_person': [100, 200, 300]
        })
        
        df_capacity = pd.DataFrame({
            'Checkpoint': ['1-3', '2-5'],
            'Sentido': ['1-3', '1-2'],  # Different senses
            'TOTAL': [500, 600],
            'FA': [1.0, 1.0],
            'M': [50, 60], 'A': [50, 60], 'B': [50, 60], 'CU': [100, 120], 'CAI': [100, 120], 'CAII': [100, 120],
            'Focup_M': [1, 1], 'Focup_A': [1, 1], 'Focup_B': [1, 1], 'Focup_CU': [1, 1], 'Focup_CAI': [1, 1], 'Focup_CAII': [1, 1]
        })
        
        result = match_capacity_to_od(df_od, df_capacity)
        
        # All three should have NaN capacity
        for i in range(3):
            assert pd.isna(result.iloc[i]['cap_total']), f"❌ REGLA 4: Fila {i} debe tener cap_total = NaN"
        
        print("✅ Test 4: Múltiples sentidos faltantes → NaN - PASSED")


def run_all_tests():
    """Run all STRICT MODE tests"""
    print("\n" + "="*70)
    print("KIDO-Ruteo v2.0 - STRICT MODE Validation Tests")
    print("="*70 + "\n")
    
    test_suite = TestStrictCapacityMatching()
    
    try:
        test_suite.test_no_fallback_to_sense_zero()
        test_suite.test_exact_match_works()
        test_suite.test_sense_not_read_from_input()
        test_suite.test_multiple_missing_senses()
        
        print("\n" + "="*70)
        print("✅ ALL STRICT MODE TESTS PASSED")
        print("="*70)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
