"""
debug_tracer.py

Clase DebugTracer para registrar la trazabilidad numérica completa del pipeline
en el checkpoint 2030.

Rastrea cada paso del cálculo por par OD:
- origin_id, destination_id
- trips_person
- intrazonal_factor
- mc_distance_m, mc2_distance_m
- sense_code
- checkpoint_is_directional
- cap_M, cap_A, cap_B, cap_CU, cap_CAI, cap_CAII, cap_total
- FA
- focup_M, ..., focup_CAII
- share_M, ..., share_CAII
- veh_M, ..., veh_CAII
- veh_total
- congruence_id

Salida: debug_checkpoint2030_trace.csv (no contractual, solo para auditoría)
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DebugTracer:
    """
    Rastridor de trazabilidad numérica para checkpoint 2030.
    
    Registra cada OD procesado con todos los valores intermedios y finales.
    """
    
    def __init__(self, output_dir: str = "."):
        """
        Args:
            output_dir: Directorio donde guardar el archivo de traza (debug_checkpoint2030_trace.csv)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.trace_rows = []
        self.trace_file = self.output_dir / "debug_checkpoint2030_trace.csv"
        
        logger.info(f"🔍 DebugTracer inicializado. Output: {self.trace_file}")
    
    def register_od_start(
        self,
        origin_id: str,
        destination_id: str,
        trips_person: Optional[float] = None,
        intrazonal_factor: Optional[float] = None,
    ) -> None:
        """
        Registra el inicio del procesamiento de un OD.
        
        Args:
            origin_id: ID de la zona origen
            destination_id: ID de la zona destino
            trips_person: Número de viajes persona
            intrazonal_factor: Factor intrazonal (0 o 1)
        """
        self.current_od = {
            'origin_id': str(origin_id),
            'destination_id': str(destination_id),
            'trips_person': trips_person,
            'intrazonal_factor': intrazonal_factor,
        }
    
    def register_routing(
        self,
        mc_distance_m: Optional[float],
        mc2_distance_m: Optional[float],
        sense_code: Optional[str],
        checkpoint_is_directional: Optional[bool],
    ) -> None:
        """
        Registra información de ruteo y sentido derivado.
        
        Args:
            mc_distance_m: Distancia de ruta MC (más corta)
            mc2_distance_m: Distancia de ruta MC2 (con checkpoint)
            sense_code: Código de sentido derivado (ej: "1-3")
            checkpoint_is_directional: Si el checkpoint es direccional (True) o agregado (False)
        """
        if not hasattr(self, 'current_od'):
            return
        
        self.current_od.update({
            'mc_distance_m': mc_distance_m,
            'mc2_distance_m': mc2_distance_m,
            'sense_code': sense_code,
            'checkpoint_is_directional': checkpoint_is_directional,
        })
    
    def register_capacity_match(
        self,
        cap_M: Optional[float] = None,
        cap_A: Optional[float] = None,
        cap_B: Optional[float] = None,
        cap_CU: Optional[float] = None,
        cap_CAI: Optional[float] = None,
        cap_CAII: Optional[float] = None,
        cap_total: Optional[float] = None,
        fa: Optional[float] = None,
        focup_M: Optional[float] = None,
        focup_A: Optional[float] = None,
        focup_B: Optional[float] = None,
        focup_CU: Optional[float] = None,
        focup_CAI: Optional[float] = None,
        focup_CAII: Optional[float] = None,
    ) -> None:
        """
        Registra datos de capacidad y factor de ocupación.
        
        Args:
            cap_*: Capacidades por categoría
            cap_total: Capacidad total
            fa: Factor de ajuste
            focup_*: Factores de ocupación por categoría
        """
        if not hasattr(self, 'current_od'):
            return
        
        self.current_od.update({
            'cap_M': cap_M,
            'cap_A': cap_A,
            'cap_B': cap_B,
            'cap_CU': cap_CU,
            'cap_CAI': cap_CAI,
            'cap_CAII': cap_CAII,
            'cap_total': cap_total,
            'fa': fa,
            'focup_M': focup_M,
            'focup_A': focup_A,
            'focup_B': focup_B,
            'focup_CU': focup_CU,
            'focup_CAI': focup_CAI,
            'focup_CAII': focup_CAII,
        })
    
    def register_shares(
        self,
        share_M: Optional[float] = None,
        share_A: Optional[float] = None,
        share_B: Optional[float] = None,
        share_CU: Optional[float] = None,
        share_CAI: Optional[float] = None,
        share_CAII: Optional[float] = None,
    ) -> None:
        """
        Registra shares (proporción de capacidad) por categoría.
        
        share_* = cap_* / cap_total
        """
        if not hasattr(self, 'current_od'):
            return
        
        self.current_od.update({
            'share_M': share_M,
            'share_A': share_A,
            'share_B': share_B,
            'share_CU': share_CU,
            'share_CAI': share_CAI,
            'share_CAII': share_CAII,
        })
    
    def register_vehicles(
        self,
        veh_M: Optional[float] = None,
        veh_A: Optional[float] = None,
        veh_B: Optional[float] = None,
        veh_CU: Optional[float] = None,
        veh_CAI: Optional[float] = None,
        veh_CAII: Optional[float] = None,
        veh_total: Optional[float] = None,
    ) -> None:
        """
        Registra vehículos calculados por categoría.
        
        Args:
            veh_*: Vehículos por categoría
            veh_total: Total de vehículos
        """
        if not hasattr(self, 'current_od'):
            return
        
        self.current_od.update({
            'veh_M': veh_M,
            'veh_A': veh_A,
            'veh_B': veh_B,
            'veh_CU': veh_CU,
            'veh_CAI': veh_CAI,
            'veh_CAII': veh_CAII,
            'veh_total': veh_total,
        })
    
    def register_congruence(self, congruence_id: Optional[int]) -> None:
        """
        Registra el ID de congruencia (0=OK, 1,2,3=Warning, 4=No congruente).
        
        Args:
            congruence_id: ID de congruencia
        """
        if not hasattr(self, 'current_od'):
            return
        
        self.current_od['congruence_id'] = congruence_id
    
    def finalize_od(self) -> None:
        """
        Finaliza el registro del OD actual y lo agrega a la lista de trazas.
        """
        if hasattr(self, 'current_od') and self.current_od:
            self.trace_rows.append(self.current_od.copy())
            self.current_od = {}
    
    def save_trace(self) -> str:
        """
        Guarda el archivo de traza como CSV.
        
        Devuelve:
            Ruta del archivo guardado
        """
        if not self.trace_rows:
            logger.warning("⚠️ No hay ODs registrados para traza.")
            return str(self.trace_file)
        
        df_trace = pd.DataFrame(self.trace_rows)
        
        # Organizar columnas de forma lógica
        col_order = [
            'origin_id', 'destination_id',
            'trips_person', 'intrazonal_factor',
            'mc_distance_m', 'mc2_distance_m',
            'sense_code', 'checkpoint_is_directional',
            'cap_M', 'cap_A', 'cap_B', 'cap_CU', 'cap_CAI', 'cap_CAII', 'cap_total',
            'fa',
            'focup_M', 'focup_A', 'focup_B', 'focup_CU', 'focup_CAI', 'focup_CAII',
            'share_M', 'share_A', 'share_B', 'share_CU', 'share_CAI', 'share_CAII',
            'veh_M', 'veh_A', 'veh_B', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total',
            'congruence_id',
        ]
        
        # Seleccionar columnas que existen en el dataframe
        available_cols = [col for col in col_order if col in df_trace.columns]
        df_trace = df_trace[available_cols]
        
        df_trace.to_csv(self.trace_file, index=False)
        logger.info(f"✅ Traza de ODs guardada: {self.trace_file}")
        logger.info(f"   Total de ODs registrados: {len(df_trace)}")
        
        return str(self.trace_file)
    
    def summary_stats(self) -> Dict:
        """
        Retorna estadísticas resumidas de la traza.
        
        Devuelve:
            Diccionario con estadísticas clave
        """
        if not self.trace_rows:
            return {}
        
        df_trace = pd.DataFrame(self.trace_rows)
        
        stats = {
            'total_ods': len(df_trace),
            'ods_with_valid_route': (df_trace['mc_distance_m'] > 0).sum(),
            'ods_with_capacity_match': df_trace['cap_total'].notna().sum(),
            'ods_congruent': (df_trace['congruence_id'] == 0).sum(),
            'ods_warning': ((df_trace['congruence_id'] >= 1) & (df_trace['congruence_id'] <= 3)).sum(),
            'ods_not_congruent': (df_trace['congruence_id'] == 4).sum(),
            'avg_veh_total': df_trace['veh_total'].mean(),
            'sum_veh_total': df_trace['veh_total'].sum(),
        }
        
        return stats
    
    def print_summary(self) -> None:
        """
        Imprime un resumen de la trazabilidad en log.
        """
        stats = self.summary_stats()
        
        if not stats:
            logger.info("No hay estadísticas disponibles.")
            return
        
        logger.info("=" * 70)
        logger.info("📊 RESUMEN DE TRAZABILIDAD - CHECKPOINT 2030")
        logger.info("=" * 70)
        logger.info(f"Total de ODs procesados: {stats['total_ods']}")
        logger.info(f"ODs con ruta válida (MC y MC2): {stats['ods_with_valid_route']}")
        logger.info(f"ODs con capacidad encontrada: {stats['ods_with_capacity_match']}")
        logger.info(f"ODs congruentes (id=0): {stats['ods_congruent']}")
        logger.info(f"ODs con warning (id=1,2,3): {stats['ods_warning']}")
        logger.info(f"ODs no congruentes (id=4): {stats['ods_not_congruent']}")
        logger.info(f"Promedio de veh_total: {stats['avg_veh_total']:.2f}")
        logger.info(f"Suma de veh_total: {stats['sum_veh_total']:.2f}")
        logger.info("=" * 70)
