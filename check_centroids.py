#!/usr/bin/env python3
"""Verify regenerated centroids have good diversity"""

import geopandas as gpd

# Check the regenerated centroids
gdf = gpd.read_file('data/network/centroids.gpkg', layer='centroids')
print('=' * 70)
print('REGENERATED CENTROIDS ANALYSIS')
print('=' * 70)
print(f'Total zones: {len(gdf)}')
print(f'Unique centroid nodes: {gdf["centroid_node_id"].nunique()}')
print(f'Diversity: {100*gdf["centroid_node_id"].nunique()/len(gdf):.1f}%')
print()
print('Top 15 centroid nodes:')
print(gdf['centroid_node_id'].value_counts().head(15))
print()
print('Sample centroids (first 10):')
print(gdf[['zone_id', 'centroid_node_id', 'method', 'nodes_in_zone']].head(10))
print()

# Verify diversity
unique_nodes = gdf['centroid_node_id'].nunique()
total_zones = len(gdf)

if unique_nodes == total_zones:
    print('✅ PERFECT: Each zone has its own unique centroid node!')
elif unique_nodes > total_zones * 0.8:
    print('✅ EXCELLENT: High diversity centroids (>80% unique)')
elif unique_nodes > total_zones * 0.5:
    print('✅ GOOD: Reasonable diversity centroids (>50% unique)')
elif unique_nodes > total_zones * 0.3:
    print('⚠️  FAIR: Low diversity centroids (>30% unique)')
else:
    print('❌ BAD: Very low diversity centroids (<30% unique)')

print()
print('=' * 70)
