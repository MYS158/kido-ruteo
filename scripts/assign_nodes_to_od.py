"""Asigna nodos de red a zonas origen/destino en datos OD.

Este script toma:
1. Datos OD con columnas origin_id, destination_id (IDs de zonas)
2. Red de nodos (nodes.gpkg) con asociación zona → nodo
3. Genera archivo OD con origin_node_id, destination_node_id poblados

Permite ejecutar el pipeline de routing con datos reales del proyecto.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def assign_nodes_to_od(
    od_file: Path,
    nodes_file: Path,
    output_file: Path,
    origin_col: str = "origin_id",
    dest_col: str = "destination_id",
) -> pd.DataFrame:
    """Asigna nodos de red a zonas origen/destino.
    
    Args:
        od_file: Archivo CSV con datos OD
        nodes_file: Archivo GPKG con nodos de red
        output_file: Archivo CSV de salida con node_ids asignados
        origin_col: Nombre de columna con ID de zona origen
        dest_col: Nombre de columna con ID de zona destino
        
    Returns:
        DataFrame con origin_node_id y destination_node_id poblados
    """
    logger.info("=== Asignando nodos a datos OD ===")
    
    # 1. Cargar datos OD
    logger.info("Cargando datos OD desde %s", od_file)
    df_od = pd.read_csv(od_file)
    logger.info("  ✓ Cargados %d registros", len(df_od))
    
    # Validar columnas requeridas
    if origin_col not in df_od.columns:
        raise ValueError(f"Columna '{origin_col}' no existe en {od_file}")
    if dest_col not in df_od.columns:
        raise ValueError(f"Columna '{dest_col}' no existe en {od_file}")
    
    logger.info("  Columnas origen/destino: '%s' / '%s'", origin_col, dest_col)
    
    # 2. Cargar nodos
    logger.info("Cargando nodos desde %s", nodes_file)
    gdf_nodes = gpd.read_file(nodes_file)
    logger.info("  ✓ Cargados %d nodos", len(gdf_nodes))
    
    # Validar que nodos tienen zone_id o zone_name
    if "zone_id" in gdf_nodes.columns:
        zone_col = "zone_id"
    elif "zone_name" in gdf_nodes.columns:
        zone_col = "zone_name"
        logger.info("  ✓ Usando zone_name para mapeo")
    else:
        raise ValueError(
            f"Archivo de nodos debe tener columna 'zone_id' o 'zone_name'. "
            f"Columnas disponibles: {gdf_nodes.columns.tolist()}"
        )
    
    # 3. Crear mapeo zona → nodo (convertir ambos lados a string para consistencia)
    logger.info("Creando mapeo zona → nodo (columna: %s)...", zone_col)
    zone_to_node = {str(z): n for z, n in zip(gdf_nodes[zone_col], gdf_nodes["node_id"]) if pd.notna(z)}
    logger.info("  ✓ Mapeo creado para %d zonas", len(zone_to_node))
    
    # 4. Asignar nodos a orígenes (convertir a string para match consistente)
    logger.info("Asignando nodos a orígenes...")
    df_od["origin_node_id"] = df_od[origin_col].astype(str).map(zone_to_node)
    
    # Contar asignaciones exitosas
    n_origin_assigned = df_od["origin_node_id"].notna().sum()
    n_origin_missing = df_od["origin_node_id"].isna().sum()
    
    logger.info("  ✓ Asignados: %d / %d (%.1f%%)",
                n_origin_assigned,
                len(df_od),
                n_origin_assigned / len(df_od) * 100)
    
    if n_origin_missing > 0:
        logger.warning("  ⚠️  Sin asignar: %d orígenes", n_origin_missing)
        missing_zones = df_od[df_od["origin_node_id"].isna()][origin_col].unique()
        logger.warning("     Zonas sin nodo: %s", missing_zones[:10])
    
    # 5. Asignar nodos a destinos (convertir a string para match consistente)
    logger.info("Asignando nodos a destinos...")
    df_od["destination_node_id"] = df_od[dest_col].astype(str).map(zone_to_node)
    
    n_dest_assigned = df_od["destination_node_id"].notna().sum()
    n_dest_missing = df_od["destination_node_id"].isna().sum()
    
    logger.info("  ✓ Asignados: %d / %d (%.1f%%)",
                n_dest_assigned,
                len(df_od),
                n_dest_assigned / len(df_od) * 100)
    
    if n_dest_missing > 0:
        logger.warning("  ⚠️  Sin asignar: %d destinos", n_dest_missing)
        missing_zones = df_od[df_od["destination_node_id"].isna()][dest_col].unique()
        logger.warning("     Zonas sin nodo: %s", missing_zones[:10])
    
    # 6. Filtrar registros con ambos nodos asignados
    df_od_valid = df_od[
        df_od["origin_node_id"].notna() & df_od["destination_node_id"].notna()
    ].copy()
    
    logger.info("\n=== Resumen ===")
    logger.info("  Total registros: %d", len(df_od))
    logger.info("  Con ambos nodos: %d (%.1f%%)",
                len(df_od_valid),
                len(df_od_valid) / len(df_od) * 100)
    logger.info("  Descartados: %d", len(df_od) - len(df_od_valid))
    
    # 7. Convertir node_ids a enteros
    df_od_valid["origin_node_id"] = df_od_valid["origin_node_id"].astype(int)
    df_od_valid["destination_node_id"] = df_od_valid["destination_node_id"].astype(int)
    
    # 8. Guardar resultado
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_od_valid.to_csv(output_file, index=False)
    logger.info("\n✅ Datos OD con nodos guardados en: %s", output_file)
    
    return df_od_valid


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Asigna nodos de red a zonas origen/destino en datos OD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Asignar nodos a kido_interim.csv
  python scripts/assign_nodes_to_od.py
  
  # Especificar archivos personalizados
  python scripts/assign_nodes_to_od.py \\
    --od data/interim/mi_od.csv \\
    --nodes data/network/synthetic/nodes.gpkg \\
    --output data/interim/od_with_nodes.csv
  
  # Usar nombres de columna diferentes
  python scripts/assign_nodes_to_od.py \\
    --origin-col zona_origen \\
    --dest-col zona_destino
        """,
    )
    
    parser.add_argument(
        "--od",
        type=Path,
        default=Path("data/interim/kido_interim.csv"),
        help="Archivo CSV con datos OD (default: data/interim/kido_interim.csv)",
    )
    
    parser.add_argument(
        "--nodes",
        type=Path,
        default=Path("data/network/synthetic/nodes.gpkg"),
        help="Archivo GPKG con nodos (default: data/network/synthetic/nodes.gpkg)",
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/kido_interim_with_nodes.csv"),
        help="Archivo CSV de salida (default: data/interim/kido_interim_with_nodes.csv)",
    )
    
    parser.add_argument(
        "--origin-col",
        type=str,
        default="origin_id",
        help="Nombre de columna con ID de zona origen (default: origin_id)",
    )
    
    parser.add_argument(
        "--dest-col",
        type=str,
        default="destination_id",
        help="Nombre de columna con ID de zona destino (default: destination_id)",
    )
    
    args = parser.parse_args()
    
    # Validar archivos de entrada
    if not args.od.exists():
        logger.error("Error: Archivo OD no existe: %s", args.od)
        return 1
    
    if not args.nodes.exists():
        logger.error("Error: Archivo de nodos no existe: %s", args.nodes)
        logger.info("\nGenerar red primero: python scripts/generate_network.py")
        return 1
    
    # Asignar nodos
    try:
        df_result = assign_nodes_to_od(
            od_file=args.od,
            nodes_file=args.nodes,
            output_file=args.output,
            origin_col=args.origin_col,
            dest_col=args.dest_col,
        )
        
        logger.info("\nPróximos pasos:")
        logger.info("  1. Ejecutar routing: python scripts/run_pipeline.py --od %s", args.output)
        logger.info("  2. O usar directamente en código Python")
        
        return 0
        
    except Exception as exc:
        logger.error("Error asignando nodos: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
