"""
Script para validar que la red extendida cubre los checkpoints.
"""

from src.kido_ruteo.routing.graph_loader import load_graph_from_geojson
from src.kido_ruteo.processing.checkpoint_loader import get_checkpoint_node_mapping
import geopandas as gpd

print("=" * 70)
print("VALIDACIÓN DE RED EXTENDIDA")
print("=" * 70)

# 1. Cargar y analizar la red
print("\n1. Cargando red extendida...")
G = load_graph_from_geojson('data/raw/red_extended.geojson')

print(f"   ✓ Nodos en la red: {G.number_of_nodes():,}")
print(f"   ✓ Aristas en la red: {G.number_of_edges():,}")

# 2. Cargar y asignar checkpoints
print("\n2. Asignando checkpoints a nodos...")
checkpoint_nodes = get_checkpoint_node_mapping('data/raw/zonification/zonification.geojson', G)

# 3. Analizar distancias
print("\n3. Análisis de distancias checkpoint → nodo más cercano:")
print(f"   • Distancia mínima:   {checkpoint_nodes['distance_m'].min():.1f} m")
print(f"   • Distancia máxima:   {checkpoint_nodes['distance_m'].max():.1f} m")
print(f"   • Distancia promedio: {checkpoint_nodes['distance_m'].mean():.1f} m")
print(f"   • Distancia mediana:  {checkpoint_nodes['distance_m'].median():.1f} m")

# 4. Identificar checkpoints problemáticos (>1km de distancia)
problematic = checkpoint_nodes[checkpoint_nodes['distance_m'] > 1000]
if len(problematic) > 0:
    print(f"\n⚠️  {len(problematic)} checkpoint(s) están a >1km del nodo más cercano:")
    for _, row in problematic.iterrows():
        print(f"   • {row['checkpoint_name']} (ID {row['checkpoint_id']}): {row['distance_m']:.0f} m")
else:
    print(f"\n✓ Todos los checkpoints están a <1km de la red")

# 5. Verificar checkpoint 2002 específicamente
cp_2002 = checkpoint_nodes[checkpoint_nodes['checkpoint_id'] == 2002]
if len(cp_2002) > 0:
    dist = cp_2002.iloc[0]['distance_m']
    print(f"\n4. Checkpoint 2002 (el que estamos probando):")
    print(f"   • Distancia al nodo: {dist:.1f} m")
    if dist < 500:
        print(f"   ✓ ¡EXCELENTE! Muy cerca de la red")
    elif dist < 1000:
        print(f"   ✓ Aceptable - dentro de 1km")
    elif dist < 5000:
        print(f"   ⚠️  Lejos pero usable")
    else:
        print(f"   ❌ Demasiado lejos - puede causar problemas")

# 6. Conclusión
print("\n" + "=" * 70)
if checkpoint_nodes['distance_m'].max() < 5000:
    print("✅ CONCLUSIÓN: La red es ÚTIL para este proyecto")
    print("   Todos los checkpoints están razonablemente cerca de la red.")
else:
    print("⚠️  CONCLUSIÓN: La red tiene limitaciones")
    print("   Algunos checkpoints están muy alejados de las carreteras.")
print("=" * 70)
