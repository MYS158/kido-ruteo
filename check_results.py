import pandas as pd

df = pd.read_csv('data/processed/processed_checkpoint2002.csv')

print('Primeras 10 filas:')
print(df.head(10))

print('\nEstadísticas de veh_total:')
print(df['veh_total'].describe())

print(f'\nCantidad de NaN en veh_total: {df["veh_total"].isna().sum()} de {len(df)}')
print(f'Cantidad de valores válidos: {df["veh_total"].notna().sum()}')

# Mostrar algunos con valores válidos
valid_rows = df[df['veh_total'].notna()]
if len(valid_rows) > 0:
    print(f'\nPrimeras filas con veh_total válido:')
    print(valid_rows.head(10))
