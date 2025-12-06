"""Módulo de procesamiento KIDO: limpieza, intrazonal, vector de acceso y cardinalidad."""

from .reader import load_kido_raw, load_network_metadata
from .cleaner import clean_kido
from .intrazonal import marcar_intrazonales
from .vector_acceso import generar_vectores_acceso
from .cardinalidad import asignar_sentido
from .processing_pipeline import KIDORawProcessor

__all__ = [
    "load_kido_raw",
    "load_network_metadata",
    "clean_kido",
    "marcar_intrazonales",
    "generar_vectores_acceso",
    "asignar_sentido",
    "KIDORawProcessor",
]
