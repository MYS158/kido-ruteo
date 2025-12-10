"""
KIDO-Ruteo: Sistema de procesamiento de datos Origen-Destino.

Paquete para análisis de movilidad urbana y generación de matrices OD.
"""

__version__ = "0.1.0"
__author__ = "KIDO Team"

from . import io
from . import preprocessing
from . import routing
from . import congruence

__all__ = ["io", "preprocessing", "routing", "congruence"]
