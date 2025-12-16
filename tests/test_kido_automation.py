import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))

from kido_automation import (
    preprocess_and_adjust, 
    network_simulation_and_validation, 
    final_calculation, 
    convert_to_tpda_and_matrices
)

class TestKidoAutomation(unittest.TestCase):

    def setUp(self):
        # Create sample data
        self.df_kido = pd.DataFrame({
            'date': ['2025-05-11', '2025-05-11', '2025-05-12'],
            'origin': [101, 102, 101],
            'destination': [102, 101, 101], # Row 3 is intrazonal
            'total_trips': [100, 5, 50]
        })
        
        self.df_macrozonas = pd.DataFrame({
            'ID': [101, 102],
            'ZON_2527': ['MacroA', 'MacroB']
        })
        
        self.df_sentidos = pd.DataFrame({
            'Auxiliar': ['MacroA-MacroB'], # Matches AUX_MACROZONA
            'Valido': [1]
        })
        
        self.df_validacion = pd.DataFrame({
            'AU': [1.8], 'BUS': [20], 'CU': [1.2], 'CAI': [1.1], 'CAII': [1.15], 'M': [1.0]
        })
        
        self.df_vial = pd.DataFrame({
            'Suma de AU_OK': [1000]
        })

    def test_preprocess_and_adjust(self):
        df = preprocess_and_adjust(self.df_kido, self.df_macrozonas, self.df_sentidos)
        
        # Check columns created
        self.assertIn('AUX', df.columns)
        self.assertIn('intrazonal', df.columns)
        self.assertIn('total_trips_modif', df.columns)
        
        # Check intrazonal logic (Row 3: 101->101 should be 1)
        self.assertEqual(df.loc[2, 'intrazonal'], 1)
        self.assertEqual(df.loc[0, 'intrazonal'], 0)
        
        # Check total_trips_modif (Row 2: 5 < 10 -> 1)
        self.assertEqual(df.loc[1, 'total_trips_modif'], 1)
        self.assertEqual(df.loc[0, 'total_trips_modif'], 100)
        
        # Check Macrozonas mapping
        self.assertEqual(df.loc[0, 'MACROZONA-O'], 'MacroA')

    def test_network_simulation(self):
        df_in = preprocess_and_adjust(self.df_kido, self.df_macrozonas, self.df_sentidos)
        df = network_simulation_and_validation(df_in)
        
        self.assertIn('DIST_MC', df.columns)
        self.assertIn('id_potencial', df.columns)
        # id_potencial should be 0 or 1
        self.assertTrue(df['id_potencial'].isin([0, 1]).all())

    def test_final_calculation(self):
        df_in = preprocess_and_adjust(self.df_kido, self.df_macrozonas, self.df_sentidos)
        df_in = network_simulation_and_validation(df_in)
        df = final_calculation(df_in, self.df_validacion, self.df_vial)
        
        self.assertIn('VIAJES', df.columns)
        
        # Check Intrazonal trips are 0 (Row 3)
        # Logic: VIAJES = ... * (1 - intrazonal) ...
        # Row 3 is intrazonal=1, so VIAJES should be 0
        self.assertEqual(df.loc[2, 'VIAJES'], 0)
        
        # Check Interzonal trips (Row 1)
        self.assertFalse(df['VIAJES'].isna().any())

    def test_matrices(self):
        df_in = preprocess_and_adjust(self.df_kido, self.df_macrozonas, self.df_sentidos)
        df_in = network_simulation_and_validation(df_in)
        df_final = final_calculation(df_in, self.df_validacion, self.df_vial)
        
        matrices, df_export = convert_to_tpda_and_matrices(df_final, self.df_validacion)
        
        # Check matrix shape
        # Origins: 101, 102. Dests: 101, 102.
        self.assertIn('VEH_AU_TRABAJO', matrices)
        mat_au = matrices['VEH_AU_TRABAJO']
        
        self.assertTrue(101 in mat_au.index)
        self.assertTrue(102 in mat_au.columns)

if __name__ == '__main__':
    unittest.main()
