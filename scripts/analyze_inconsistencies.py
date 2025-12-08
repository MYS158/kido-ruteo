"""Analiza inconsistencias en los resultados del routing."""
import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/routing/routing_test_results.csv')

print('\n=== ANALISIS DE INCONSISTENCIAS ===\n')

# Definir epsilon para precisión numérica
epsilon_ratio = 1e-9  # Precisión de punto flotante
epsilon_m = 1e-6  # 1 micrómetro

# Ratio X < 1.0
print('Ratio X < 1.0 (sin considerar epsilon):')
bad_ratio_raw = df[df['ratio_x'] < 1.0]
if len(bad_ratio_raw) > 0:
    print(f'  {len(bad_ratio_raw)} pares encontrados')
    
    # Verificar si es error de precisión
    bad_ratio = bad_ratio_raw[bad_ratio_raw['ratio_x'] < (1.0 - epsilon_ratio)]
    if len(bad_ratio) > 0:
        print(f'\nRatio X < 1.0 (inconsistencias REALES con epsilon={epsilon_ratio}):')
        print(bad_ratio[['origin_node_id', 'destination_node_id', 'mc_length_m', 'mc2_length_m', 'ratio_x']].to_string())
    else:
        print(f'  ✓ Todos son errores de precisión de punto flotante (< {epsilon_ratio})')
else:
    print('  Ninguno')

# MC2 < MC
print('\n\nMC2 < MC (sin considerar epsilon):')
bad_mc2_raw = df[df['mc2_length_m'] < df['mc_length_m']]
if len(bad_mc2_raw) > 0:
    print(f'  {len(bad_mc2_raw)} pares encontrados')
    
    # Calcular diferencias
    bad_mc2_raw_copy = bad_mc2_raw.copy()
    bad_mc2_raw_copy['diff_m'] = bad_mc2_raw_copy['mc_length_m'] - bad_mc2_raw_copy['mc2_length_m']
    
    # Verificar si es error de precisión
    bad_mc2 = bad_mc2_raw_copy[bad_mc2_raw_copy['diff_m'] > epsilon_m]
    if len(bad_mc2) > 0:
        print(f'\nMC2 < MC (inconsistencias REALES con epsilon={epsilon_m}m):')
        print(bad_mc2[['origin_node_id', 'destination_node_id', 'mc_length_m', 'mc2_length_m', 'ratio_x']].to_string())
        print('\nDiferencias (MC - MC2):')
        print(bad_mc2[['origin_node_id', 'destination_node_id', 'diff_m']].to_string())
    else:
        print(f'  ✓ Todos son errores de precisión de punto flotante (< {epsilon_m}m)')
else:
    print('  Ninguno')

# Estadísticas generales
print('\n\n=== ESTADISTICAS GENERALES ===\n')
diff = df['mc2_length_m'] - df['mc_length_m']
print(f'Diferencia MC2 - MC:')
print(f'  Min: {diff.min():.10f} m')
print(f'  Max: {diff.max():.10f} m')
print(f'  Media: {diff.mean():.10f} m')

# Contar paths idénticos
same_paths = (df['path_nodes_mc'] == df['path_nodes_mc2']).sum()
print(f'\nPares donde path_mc == path_mc2: {same_paths}/{len(df)} ({same_paths/len(df)*100:.1f}%)')

# Investigar por qué paths son idénticos
print('\n\n=== INVESTIGACION: ¿POR QUE MC2 = MC? ===\n')
print('Muestreo de pares:')
for idx in [0, 5, 10]:
    row = df.iloc[idx]
    print(f"\nPar {idx + 1}: {row['origin_node_id']} → {row['destination_node_id']}")
    print(f"  Checkpoint: {row['checkpoint_node']} (source: {row['checkpoint_source']})")
    print(f"  Path MC:  {row['path_nodes_mc']}")
    print(f"  Path MC2: {row['path_nodes_mc2']}")
    print(f"  Iguales: {row['path_nodes_mc'] == row['path_nodes_mc2']}")
