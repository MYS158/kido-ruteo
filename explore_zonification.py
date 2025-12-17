import geopandas as gpd
import pandas as pd

# Cargar el archivo
gdf = gpd.read_file('data/raw/zonification/zonification.geojson')

print('Total features:', len(gdf))
print('\nColumnas:', gdf.columns.tolist())
print('\nTipos de geometría:', gdf.geometry.type.value_counts())
print('\nPrimeras 5 filas:')
print(gdf.head())

# Buscar columnas relacionadas con checkpoints
checkpoint_cols = [col for col in gdf.columns if 'check' in col.lower() or 'punto' in col.lower() or 'aforo' in col.lower()]
print('\nColumnas relacionadas con checkpoints:', checkpoint_cols if checkpoint_cols else 'No encontradas')

if checkpoint_cols:
    print('\nDatos de checkpoints (primeras 10):')
    print(gdf[checkpoint_cols].head(10))

# Ver todas las propiedades
print('\nTodas las columnas y primeros valores:')
for col in gdf.columns:
    if col != 'geometry':
        print(f"{col}: {gdf[col].unique()[:5]}")
