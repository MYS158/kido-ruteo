import geopandas as gpd
import pandas as pd

# Check nodes
gdf = gpd.read_file('data/raw/network/nodes.gpkg')
print('Zone 144 exists:', '144' in gdf['zone_name'].values)
zone_144 = gdf[gdf['zone_name'] == '144']
print('Nodes with zone 144:', len(zone_144))
if len(zone_144) > 0:
    print(zone_144[['node_id', 'zone_name']])

# Check OD file
df_od = pd.read_csv('data/interim/od_with_nodes.csv')
print('\nOD with nodes shape:', df_od.shape)
print('\nOrigin node ID distribution:')
print(df_od['origin_node_id'].value_counts().head(10))
print('\nDestination node ID distribution:')
print(df_od['destination_node_id'].value_counts().head(10))
print('\nSample OD with nodes:')
print(df_od[['origin', 'destination', 'origin_node_id', 'destination_node_id']].head(20))
