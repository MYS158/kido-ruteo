"""Script de prueba del pipeline con checkpoints manuales forzados."""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kido_ruteo.routing.routing_pipeline import run_routing_pipeline


def main():
    """Prueba con checkpoints manuales fuera de ruta óptima."""
    print("=" * 70)
    print("🔧 TEST: Checkpoints manuales forzando desviaciones")
    print("=" * 70)
    
    project_root = Path(__file__).parent.parent
    network_dir = project_root / "data" / "network" / "synthetic"
    output_dir = project_root / "data" / "processed" / "routing"
    
    # Verificar que existe la red
    if not (network_dir / "edges.gpkg").exists():
        print("\n❌ Error: Primero ejecuta test_routing_with_real_data.py")
        return 1
    
    # Cargar red
    print("\n📂 Cargando red...")
    gdf_nodes = gpd.read_file(network_dir / "nodes.gpkg")
    gdf_edges = gpd.read_file(network_dir / "edges.gpkg")
    print(f"  ✓ {len(gdf_nodes)} nodos, {len(gdf_edges)} edges")
    
    # Crear pares OD específicos
    print("\n🎯 Creando pares OD de prueba...")
    od_pairs = [
        {"origin_node_id": 103, "destination_node_id": 93},
        {"origin_node_id": 15, "destination_node_id": 108},
        {"origin_node_id": 72, "destination_node_id": 21},
    ]
    df_od = pd.DataFrame(od_pairs)
    print(f"  ✓ {len(df_od)} pares")
    
    # Definir checkpoints manuales FUERA de la ruta óptima
    print("\n📍 Definiendo checkpoints manuales (fuera de ruta óptima)...")
    manual_checkpoints = [
        {
            "origin_zone_id": 103,
            "destination_zone_id": 93,
            "checkpoint_node_id": 55,  # Nodo alejado
        },
        {
            "origin_zone_id": 15,
            "destination_zone_id": 108,
            "checkpoint_node_id": 72,  # Nodo alejado
        },
        {
            "origin_zone_id": 72,
            "destination_zone_id": 21,
            "checkpoint_node_id": 15,  # Nodo alejado
        },
    ]
    df_manual = pd.DataFrame(manual_checkpoints)
    print(f"  ✓ {len(df_manual)} checkpoints manuales")
    
    # Ejecutar con checkpoints automáticos
    print("\n🔄 Test 1: Routing con checkpoints AUTO...")
    df_auto = run_routing_pipeline(
        network_path=network_dir,
        df_od=df_od,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="auto",
    )
    
    print("\n📊 Resultados AUTO:")
    for idx, row in df_auto.iterrows():
        print(f"\n  Par {row['origin_node_id']} → {row['destination_node_id']}:")
        print(f"    Checkpoint: {row['checkpoint_node']} (auto)")
        print(f"    MC:  {row['mc_length_m']/1000:.2f} km")
        print(f"    MC2: {row['mc2_length_m']/1000:.2f} km")
        print(f"    Ratio X: {row['ratio_x']:.3f}")
    
    # Ejecutar con checkpoints manuales
    print("\n" + "=" * 70)
    print("🔄 Test 2: Routing con checkpoints MANUALES (forzados)...")
    df_manual_result = run_routing_pipeline(
        network_path=network_dir,
        df_od=df_od,
        df_manual_checkpoints=df_manual,
        gdf_nodes=gdf_nodes,
        gdf_edges=gdf_edges,
        checkpoint_mode="manual",
    )
    
    print("\n📊 Resultados MANUAL:")
    for idx, row in df_manual_result.iterrows():
        print(f"\n  Par {row['origin_node_id']} → {row['destination_node_id']}:")
        print(f"    Checkpoint: {row['checkpoint_node']} (manual)")
        print(f"    MC:  {row['mc_length_m']/1000:.2f} km")
        print(f"    MC2: {row['mc2_length_m']/1000:.2f} km")
        print(f"    Ratio X: {row['ratio_x']:.3f}")
        
        # Validar que MC2 > MC
        if row['mc2_length_m'] <= row['mc_length_m']:
            print(f"    ⚠️  WARNING: MC2 no es mayor que MC")
        else:
            diff_km = (row['mc2_length_m'] - row['mc_length_m']) / 1000
            print(f"    ✓ Desviación: +{diff_km:.2f} km ({(row['ratio_x']-1)*100:.1f}%)")
    
    # Análisis comparativo
    print("\n" + "=" * 70)
    print("📈 ANALISIS COMPARATIVO AUTO vs MANUAL")
    print("=" * 70)
    
    for i in range(len(df_od)):
        auto_row = df_auto.iloc[i]
        manual_row = df_manual_result.iloc[i]
        
        print(f"\nPar {auto_row['origin_node_id']} → {auto_row['destination_node_id']}:")
        print(f"  AUTO:")
        print(f"    Checkpoint: {auto_row['checkpoint_node']}")
        print(f"    Ratio X: {auto_row['ratio_x']:.3f}")
        print(f"  MANUAL:")
        print(f"    Checkpoint: {manual_row['checkpoint_node']}")
        print(f"    Ratio X: {manual_row['ratio_x']:.3f}")
        print(f"  Diferencia:")
        diff_ratio = manual_row['ratio_x'] - auto_row['ratio_x']
        if diff_ratio > 0.01:
            print(f"    ✓ Manual genera +{diff_ratio:.3f} de ratio (desviación forzada exitosa)")
        elif diff_ratio > 0:
            print(f"    ~ Manual genera +{diff_ratio:.4f} de ratio (desviación mínima)")
        else:
            print(f"    ⚠️  Manual no genera desviación significativa")
    
    # Validaciones finales
    print("\n" + "=" * 70)
    print("✅ VALIDACIONES FINALES")
    print("=" * 70)
    
    # Con checkpoints AUTO: ratio debe ser ~1.0
    auto_ratios = df_auto['ratio_x']
    print(f"\nCheckpoints AUTO:")
    print(f"  Ratio X medio: {auto_ratios.mean():.4f}")
    print(f"  Ratio X max: {auto_ratios.max():.4f}")
    if (auto_ratios < 1.01).all():
        print(f"  ✓ Todos los ratios cerca de 1.0 (checkpoints en ruta óptima)")
    else:
        print(f"  ⚠️  Algunos ratios > 1.01 (checkpoint no en ruta óptima)")
    
    # Con checkpoints MANUAL: ratio debe ser > 1.0
    manual_ratios = df_manual_result['ratio_x']
    print(f"\nCheckpoints MANUAL:")
    print(f"  Ratio X medio: {manual_ratios.mean():.4f}")
    print(f"  Ratio X max: {manual_ratios.max():.4f}")
    if (manual_ratios > 1.05).any():
        print(f"  ✓ Algunos ratios > 1.05 (desviaciones significativas)")
    else:
        print(f"  ⚠️  Todos los ratios < 1.05 (desviaciones pequeñas)")
    
    # Validar que MC2 >= MC siempre
    print(f"\nCoherencia MC2 >= MC:")
    auto_valid = (df_auto['mc2_length_m'] >= df_auto['mc_length_m'] * 0.999999).all()
    manual_valid = (df_manual_result['mc2_length_m'] >= df_manual_result['mc_length_m'] * 0.999999).all()
    print(f"  AUTO: {'✓' if auto_valid else '❌'}")
    print(f"  MANUAL: {'✓' if manual_valid else '❌'}")
    
    print("\n" + "=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
