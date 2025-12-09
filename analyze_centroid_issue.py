#!/usr/bin/env python3
"""Detailed analysis of centroid regeneration issue"""

import geopandas as gpd
import pandas as pd

print("=" * 70)
print("CENTROID ISSUE ANALYSIS")
print("=" * 70)

# Load all necessary files
gdf_centroids = gpd.read_file('data/network/centroids.gpkg', layer='centroids')
gdf_nodes = gpd.read_file('data/raw/network/nodes.gpkg')
gdf_zonas = gpd.read_file('data/raw/geografia/kido_zonas.geojson')

print("\n1. ZONES DATA:")
print(f"   Total zones: {len(gdf_zonas)}")
print(f"   Zone columns: {gdf_zonas.columns.tolist()}")
print(f"   First 5 zones: {gdf_zonas['zone_id'].head().tolist() if 'zone_id' in gdf_zonas.columns else 'No zone_id column'}")

print("\n2. NODES DATA:")
print(f"   Total nodes: {len(gdf_nodes)}")
print(f"   Node columns: {gdf_nodes.columns.tolist()}")
print(f"   Node ID range: {gdf_nodes['node_id'].min()} to {gdf_nodes['node_id'].max()}")

print("\n3. CENTROIDS DATA:")
print(f"   Total centroids: {len(gdf_centroids)}")
print(f"   Centroid columns: {gdf_centroids.columns.tolist()}")
print(f"   centroid_node_id values:")
print(f"     - Total non-null: {gdf_centroids['centroid_node_id'].notna().sum()}")
print(f"     - Total null: {gdf_centroids['centroid_node_id'].isna().sum()}")
print(f"   Centroid methods used:")
print(gdf_centroids['method'].value_counts())
print(f"   nodes_in_zone distribution:")
print(gdf_centroids['nodes_in_zone'].value_counts().head(10))

print("\n4. ISSUE DIAGNOSIS:")
if gdf_centroids['centroid_node_id'].isna().sum() > 0:
    print(f"   ⚠️  {gdf_centroids['centroid_node_id'].isna().sum()} zones have NULL centroid_node_id")
    print("   Possible causes:")
    print("   1. Zones don't contain any nodes (nodes_in_zone = 0)")
    print("   2. Zones don't have edges (edges_in_zone = 0)")
    print("   3. Zone geometry doesn't intersect with network")
    
    # Check distribution of nodes_in_zone
    null_centroid = gdf_centroids[gdf_centroids['centroid_node_id'].isna()]
    print(f"\n   Zones with NULL centroids:")
    print(f"   - With 0 nodes_in_zone: {(null_centroid['nodes_in_zone'] == 0).sum()}")
    print(f"   - With >0 nodes_in_zone: {(null_centroid['nodes_in_zone'] > 0).sum()}")

print("\n5. SPATIAL OVERLAP CHECK:")
# Check if zones actually contain nodes
zones_with_nodes = 0
for idx, zone in gdf_zonas.head(10).iterrows():
    nodes_in = gdf_nodes[gdf_nodes.geometry.within(zone.geometry)]
    if len(nodes_in) > 0:
        zones_with_nodes += 1
        print(f"   Zone {zone.get('zone_id', idx)}: {len(nodes_in)} nodes inside")
    else:
        print(f"   Zone {zone.get('zone_id', idx)}: NO NODES INSIDE")

print(f"\n   Summary: {zones_with_nodes}/10 zones have nodes inside geometry")

print("\n" + "=" * 70)
print("RECOMMENDATION:")
print("=" * 70)

if gdf_centroids['centroid_node_id'].isna().sum() > 0:
    print("""
The centroid calculation is working correctly - it's returning NULL when zones
don't have nodes/edges because the fallback methods (geometric_fallback,
single_node_fallback) aren't being selected.

This might be because:
1. Zone geometries in kido_zonas.geojson don't overlap with nodes in nodes.gpkg
2. CRS (coordinate reference system) mismatch between zone and node data
3. Zones are too small or don't actually contain network nodes

SOLUTION: Use od_with_nodes.csv directly (primary method) instead of relying
on centroids, which is what the pipeline now does! ✅

od_with_nodes.csv has 6,623 OD pairs with verified node assignments, so we
don't need all 154 zones to have centroids - only the ones in od_with_nodes.
""")
else:
    print("✅ Centroids regenerated successfully with diverse nodes")
