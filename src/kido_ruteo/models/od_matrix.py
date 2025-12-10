"""
Modelo de matriz Origen-Destino para KIDO-Ruteo.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple


class ODMatrix:
    """
    Representa una matriz Origen-Destino con métodos de manipulación.
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        origin_col: str = 'origen',
        dest_col: str = 'destino',
        value_col: str = 'viajes'
    ):
        """
        Inicializa matriz OD.
        
        Args:
            data: DataFrame con datos OD
            origin_col: Nombre de columna de origen
            dest_col: Nombre de columna de destino
            value_col: Nombre de columna de valores
        """
        self.data = data.copy()
        self.origin_col = origin_col
        self.dest_col = dest_col
        self.value_col = value_col
    
    def to_wide_format(self) -> pd.DataFrame:
        """
        Convierte a formato ancho (matriz pivotada).
        
        Returns:
            DataFrame en formato ancho
        """
        return self.data.pivot(
            index=self.origin_col,
            columns=self.dest_col,
            values=self.value_col
        ).fillna(0)
    
    def get_total_trips(self) -> float:
        """
        Calcula total de viajes en la matriz.
        
        Returns:
            Total de viajes
        """
        return self.data[self.value_col].sum()
    
    def get_zone_production(self, zone_id: int) -> float:
        """
        Calcula producción total de viajes de una zona.
        
        Args:
            zone_id: ID de la zona
            
        Returns:
            Total de viajes originados en la zona
        """
        return self.data[self.data[self.origin_col] == zone_id][self.value_col].sum()
    
    def get_zone_attraction(self, zone_id: int) -> float:
        """
        Calcula atracción total de viajes de una zona.
        
        Args:
            zone_id: ID de la zona
            
        Returns:
            Total de viajes destinados a la zona
        """
        return self.data[self.data[self.dest_col] == zone_id][self.value_col].sum()
    
    def filter_by_threshold(self, min_trips: float = 0) -> 'ODMatrix':
        """
        Filtra pares OD por umbral de viajes mínimos.
        
        Args:
            min_trips: Umbral mínimo de viajes
            
        Returns:
            Nueva instancia de ODMatrix filtrada
        """
        filtered_data = self.data[self.data[self.value_col] >= min_trips].copy()
        return ODMatrix(filtered_data, self.origin_col, self.dest_col, self.value_col)
    
    def get_intrazonal_trips(self) -> pd.DataFrame:
        """
        Extrae viajes intrazonales (origen == destino).
        
        Returns:
            DataFrame con viajes intrazonales
        """
        return self.data[self.data[self.origin_col] == self.data[self.dest_col]].copy()
    
    def get_interzonal_trips(self) -> pd.DataFrame:
        """
        Extrae viajes interzonales (origen != destino).
        
        Returns:
            DataFrame con viajes interzonales
        """
        return self.data[self.data[self.origin_col] != self.data[self.dest_col]].copy()
    
    def normalize(self, method: str = 'total') -> 'ODMatrix':
        """
        Normaliza valores de la matriz.
        
        Args:
            method: Método de normalización ('total', 'row', 'column')
            
        Returns:
            Nueva instancia de ODMatrix normalizada
        """
        normalized_data = self.data.copy()
        
        if method == 'total':
            total = self.get_total_trips()
            if total > 0:
                normalized_data[self.value_col] = normalized_data[self.value_col] / total
        
        elif method == 'row':
            for origin in normalized_data[self.origin_col].unique():
                mask = normalized_data[self.origin_col] == origin
                row_total = normalized_data[mask][self.value_col].sum()
                if row_total > 0:
                    normalized_data.loc[mask, self.value_col] /= row_total
        
        elif method == 'column':
            for dest in normalized_data[self.dest_col].unique():
                mask = normalized_data[self.dest_col] == dest
                col_total = normalized_data[mask][self.value_col].sum()
                if col_total > 0:
                    normalized_data.loc[mask, self.value_col] /= col_total
        
        return ODMatrix(normalized_data, self.origin_col, self.dest_col, self.value_col)
    
    def __len__(self) -> int:
        """Retorna número de pares OD."""
        return len(self.data)
    
    def __repr__(self) -> str:
        """Representación en string."""
        return f"ODMatrix({len(self)} pairs, {self.get_total_trips():.0f} total trips)"
