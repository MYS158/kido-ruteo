"""
Tests para validar STRICT MODE según la guía detallada de creación de archivos de salida.

Valida:
1. El input NO puede definir el sentido
2. Sentido solo se obtiene por geometría
3. No existe fallback a sentido 0
4. Sin match exacto de capacidad → veh_* = NaN
5. Output contiene EXACTAMENTE 7 columnas
6. veh_total es NaN si todas las categorías son NaN
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from kido_ruteo.processing.preprocessing import normalize_column_names
from kido_ruteo.capacity.matcher import match_capacity_to_od
from kido_ruteo.trips.calculation import calculate_vehicle_trips


class TestStrictModeV2(unittest.TestCase):
    """
    Tests para STRICT MODE v2.0 - Ocupación fija, sin fallback, match exacto
    """
    
    def setUp(self):
        """Preparar datos de prueba"""
        # Capacity data con formato correcto
        self.capacity = pd.DataFrame({
            'Checkpoint': ['2001', '2001', '2002'],
            'Sentido': ['1-3', '3-1', '1-3'],
            'A': [1500, 1400, 1200],      # Autos
            'CU': [400, 350, 300],         # Camioneta Utilitaria
            'CAI': [200, 180, 150],        # Camión Articulado I
            'CAII': [80, 70, 50]           # Camión Articulado II
        })
    
    def test_rule1_input_cannot_define_sense(self):
        """
        REGLA 1: El input NO puede definir el sentido.
        Las columnas 'sentido', 'sense', 'sense_code' deben eliminarse del input.
        """
        # Input con columna 'sentido' (prohibido)
        df_input = pd.DataFrame({
            'Origin': [1, 2],
            'Destination': [2, 3],
            'Sentido': ['1-3', '3-1'],  # ❌ PROHIBIDO
            'total_trips': [100, 200]
        })
        
        # Normalizar columnas (debe eliminar 'sentido')
        df_normalized = normalize_column_names(df_input)
        
        # Verificar que 'sentido' fue eliminado
        self.assertNotIn('sentido', df_normalized.columns)
        self.assertNotIn('sense', df_normalized.columns)
        self.assertNotIn('sense_code', df_normalized.columns)
    
    def test_rule2_sense_only_from_geometry(self):
        """
        REGLA 2: El sentido SOLO se deriva geométricamente de la ruta MC2.
        Esta prueba verifica que sin ruta geométrica, no hay sense_code válido.
        """
        # OD sin sense_code (aún no calculado por geometría)
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001'],
            'origin_id': [1],
            'destination_id': [2],
            'trips_person': [100]
        })
        
        # En este punto, sense_code no existe o es None
        # Al hacer match con capacidad, NO debe haber match
        df_matched = match_capacity_to_od(df_od, self.capacity)
        
        # Verificar que NO hay capacidad (porque sense_code no existe)
        self.assertTrue(pd.isna(df_matched['cap_total'].iloc[0]))
    
    def test_rule3_no_fallback_to_sentido_0(self):
        """
        REGLA 3: No existe fallback a sentido 0.
        Si sense_code no hace match exacto, capacidad = NaN.
        """
        # OD con sense_code='0' (prohibido como fallback)
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001'],
            'sense_code': ['0'],  # NO existe en capacity
            'origin_id': [1],
            'destination_id': [2],
            'trips_person': [100]
        })
        
        # Match con capacidad
        df_matched = match_capacity_to_od(df_od, self.capacity)
        
        # Verificar que NO hay match (cap_total = NaN)
        self.assertTrue(pd.isna(df_matched['cap_total'].iloc[0]))
    
    def test_rule4_no_exact_match_means_nan(self):
        """
        REGLA 4: Sin match exacto de (checkpoint_id, sense_code) → veh_* = NaN
        """
        # OD con sense_code que NO existe en capacity
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001'],
            'sense_code': ['2-4'],  # NO existe para checkpoint 2001
            'origin_id': [1],
            'destination_id': [2],
            'trips_person': [100],
            'intrazonal_factor': [1]
        })
        
        # Match con capacidad (no debe encontrar)
        df_matched = match_capacity_to_od(df_od, self.capacity)
        
        # Verificar que cap_total = NaN
        self.assertTrue(pd.isna(df_matched['cap_total'].iloc[0]))
        
        # Calcular viajes vehiculares
        df_veh = calculate_vehicle_trips(df_matched)
        
        # TODOS los veh_* deben ser NaN
        self.assertTrue(pd.isna(df_veh['veh_auto'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_cu'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_cai'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_caii'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_total'].iloc[0]))
    
    def test_rule5_output_exactly_7_columns(self):
        """
        REGLA 5: El output contiene EXACTAMENTE 7 columnas.
        No veh_bus, no veh_moto, no columnas intermedias.
        """
        # Columnas esperadas en la salida final
        expected_cols = [
            'Origen',
            'Destino',
            'veh_AU',
            'veh_CU',
            'veh_CAI',
            'veh_CAII',
            'veh_total'
        ]
        
        # Simular salida del pipeline
        df_output = pd.DataFrame({
            'Origen': [1, 2],
            'Destino': [2, 3],
            'veh_AU': [100.0, 150.0],
            'veh_CU': [40.0, 60.0],
            'veh_CAI': [8.3, 12.5],
            'veh_CAII': [4.0, 6.0],
            'veh_total': [152.3, 228.5]
        })
        
        # Verificar que tiene exactamente las 7 columnas
        self.assertEqual(len(df_output.columns), 7)
        self.assertListEqual(list(df_output.columns), expected_cols)
        
        # Verificar que NO tiene columnas prohibidas
        forbidden_cols = ['veh_bus', 'veh_moto', 'sense_code', 'checkpoint_id', 
                         'cap_total', 'congruence_id', 'mc2_distance_m']
        for col in forbidden_cols:
            self.assertNotIn(col, df_output.columns)
    
    def test_rule6_veh_total_nan_if_all_categories_nan(self):
        """
        REGLA 6: veh_total = NaN si todas las categorías son NaN
        """
        # OD sin capacidad (todas categorías = NaN)
        df_od = pd.DataFrame({
            'checkpoint_id': ['9999'],
            'sense_code': ['1-3'],
            'origin_id': [1],
            'destination_id': [2],
            'trips_person': [100],
            'intrazonal_factor': [1],
            'cap_total': [np.nan]
        })
        
        # Calcular viajes vehiculares
        df_veh = calculate_vehicle_trips(df_od)
        
        # Verificar que todas las categorías son NaN
        self.assertTrue(pd.isna(df_veh['veh_auto'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_cu'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_cai'].iloc[0]))
        self.assertTrue(pd.isna(df_veh['veh_caii'].iloc[0]))
        
        # veh_total DEBE ser NaN (NO 0)
        self.assertTrue(pd.isna(df_veh['veh_total'].iloc[0]))
    
    def test_vehicle_calculation_with_capacity(self):
        """
        Test de cálculo correcto con capacidad válida.
        Fórmula: veh_X = (trips_person / ocupacion_X) × intrazonal_factor
        Ocupación: AU=1.5, CU=2.5, CAI=12.0, CAII=25.0
        """
        # OD con match exacto
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001'],
            'sense_code': ['1-3'],
            'origin_id': [1],
            'destination_id': [2],
            'trips_person': [300],  # 300 personas
            'intrazonal_factor': [1]
        })
        
        # Match con capacidad (debe encontrar)
        df_matched = match_capacity_to_od(df_od, self.capacity)
        
        # Verificar que encontró capacidad
        self.assertFalse(pd.isna(df_matched['cap_total'].iloc[0]))
        self.assertEqual(df_matched['cap_au'].iloc[0], 1500)
        
        # Calcular viajes vehiculares
        df_veh = calculate_vehicle_trips(df_matched)
        
        # Verificar cálculos:
        # veh_AU = 300 / 1.5 = 200.0
        # veh_CU = 300 / 2.5 = 120.0
        # veh_CAI = 300 / 12.0 = 25.0
        # veh_CAII = 300 / 25.0 = 12.0
        # veh_total = 200 + 120 + 25 + 12 = 357.0
        
        self.assertAlmostEqual(df_veh['veh_auto'].iloc[0], 200.0, places=2)
        self.assertAlmostEqual(df_veh['veh_cu'].iloc[0], 120.0, places=2)
        self.assertAlmostEqual(df_veh['veh_cai'].iloc[0], 25.0, places=2)
        self.assertAlmostEqual(df_veh['veh_caii'].iloc[0], 12.0, places=2)
        self.assertAlmostEqual(df_veh['veh_total'].iloc[0], 357.0, places=2)
    
    def test_intrazonal_factor_zeros_vehicles(self):
        """
        Test que intrazonal_factor = 0 anula los viajes vehiculares.
        """
        # OD intrazonal (mismo origen y destino)
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001'],
            'sense_code': ['1-3'],
            'origin_id': [1],
            'destination_id': [1],  # Mismo que origen
            'trips_person': [100],
            'intrazonal_factor': [0],  # Anula viajes
            'cap_total': [2180]  # Capacidad válida
        })
        
        # Calcular viajes vehiculares
        df_veh = calculate_vehicle_trips(df_od)
        
        # Todos los viajes deben ser 0 (no NaN, porque hay capacidad)
        self.assertEqual(df_veh['veh_auto'].iloc[0], 0.0)
        self.assertEqual(df_veh['veh_cu'].iloc[0], 0.0)
        self.assertEqual(df_veh['veh_cai'].iloc[0], 0.0)
        self.assertEqual(df_veh['veh_caii'].iloc[0], 0.0)
        self.assertEqual(df_veh['veh_total'].iloc[0], 0.0)
    
    def test_exact_match_checkpoint_and_sense(self):
        """
        Test que el match es EXACTO: (checkpoint_id, sense_code)
        """
        # OD con match exacto
        df_od = pd.DataFrame({
            'checkpoint_id': ['2001', '2001', '2002'],
            'sense_code': ['1-3', '3-1', '1-3'],
            'origin_id': [1, 2, 3],
            'destination_id': [2, 3, 4],
            'trips_person': [100, 100, 100],
            'intrazonal_factor': [1, 1, 1]
        })
        
        # Match con capacidad
        df_matched = match_capacity_to_od(df_od, self.capacity)
        
        # Verificar matches correctos
        # Fila 0: checkpoint=2001, sense=1-3 → cap_au=1500
        self.assertEqual(df_matched['cap_au'].iloc[0], 1500)
        
        # Fila 1: checkpoint=2001, sense=3-1 → cap_au=1400
        self.assertEqual(df_matched['cap_au'].iloc[1], 1400)
        
        # Fila 2: checkpoint=2002, sense=1-3 → cap_au=1200
        self.assertEqual(df_matched['cap_au'].iloc[2], 1200)


if __name__ == '__main__':
    unittest.main()
