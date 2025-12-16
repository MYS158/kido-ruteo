"""
KIDO-Ruteo v2.0: Sistema completo de ruteo y congruencia KIDO.

Implementa el flujo metodológico completo KIDO para matrices OD.
"""

__version__ = "2.0.0"
__author__ = "KIDO Team"

from . import capacity
from . import congruence
from . import processing
from . import routing
from . import trips
from . import pipeline

from .pipeline import run_pipeline
