"""
KIDO-Ruteo v2.0: Sistema completo de ruteo y congruencia KIDO.

Implementa el flujo metodológico completo KIDO para matrices OD.
"""

__version__ = "2.0.0"
__author__ = "KIDO Team"

from . import io
from . import preprocessing
from . import centrality
from . import centroides
from . import access_vectors
from . import validation
from . import impedance
from . import constrained_paths
from . import congruence
from . import viajes

__all__ = [
    "io",
    "preprocessing",
    "centrality",
    "centroides",
    "access_vectors",
    "validation",
    "impedance",
    "constrained_paths",
    "congruence",
    "viajes",
]
