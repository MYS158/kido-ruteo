"""Módulo de procesamiento KIDO: limpieza, intrazonal, vector de acceso, cardinalidad y centroides."""

from .reader import load_kido_raw, load_network_metadata, load_od, load_zonas, load_aforo
from .cleaner import clean_kido
from .intrazonal import marcar_intrazonales
from .vector_acceso import generar_vectores_acceso
from .cardinalidad import asignar_sentido
from .processing_pipeline import KIDORawProcessor

try:
    from .centroids import (
        compute_subgraph_centroid,
        compute_all_zone_centroids,
        save_centroids,
        load_centroids,
    )

    __all__ = [
        "load_kido_raw",
        "load_network_metadata",
        "load_od",
        "load_zonas",
        "load_aforo",
        "clean_kido",
        "marcar_intrazonales",
        "generar_vectores_acceso",
        "asignar_sentido",
        "KIDORawProcessor",
        "compute_subgraph_centroid",
        "compute_all_zone_centroids",
        "save_centroids",
        "load_centroids",
    ]
except (ImportError, AttributeError):  # GeoPandas/NetworkX no disponible o incompatible
    __all__ = [
        "load_kido_raw",
        "load_network_metadata",
        "load_od",
        "load_zonas",
        "load_aforo",
        "clean_kido",
        "marcar_intrazonales",
        "generar_vectores_acceso",
        "asignar_sentido",
        "KIDORawProcessor",
    ]
