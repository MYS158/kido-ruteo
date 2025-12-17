# GUÍA DETALLADA: CREACIÓN DE ARCHIVOS DE SALIDA EN KIDO

## 🎯 OBJETIVO
Transformar un archivo CSV de origen-destino (`checkpoint2002.csv`) en un archivo de salida (`processed_checkpoint2002.csv`) con 7 columnas de viajes vehiculares.

---

## 📥 ARCHIVO DE ENTRADA

**Archivo:** `data/raw/queries/checkpoint/checkpoint2002.csv`

**Contenido original:**
```csv
start_date,end_date,date,destination,destination_name,origin,origin_name,total_trips
2023-01-01,2023-01-31,2023-01,1001,ZONA_A,1002,ZONA_B,250
2023-01-01,2023-01-31,2023-01,1001,ZONA_A,115,ZONA_C,<10
...
```

**Estructura:**
- `total_trips`: Viajes de personas (puede ser número o "<10")
- `origin` / `destination`: IDs de zonas
- NO contiene checkpoint, se infiere del nombre del archivo
- NO contiene sentido (sense_code)

---

## 🔄 PIPELINE COMPLETO - PASO A PASO

### **PASO 1: Carga y Normalización** 
📁 Módulo: `src/kido_ruteo/processing/preprocessing.py`

#### 1.1 Cargar CSV
```python
df_od = pd.read_csv('checkpoint2002.csv')
# 18956 filas × 8 columnas
```

#### 1.2 Normalizar nombres de columnas
Función: `normalize_column_names()`
```python
# Antes:
['start_date', 'end_date', 'date', 'destination', 'destination_name', 
 'origin', 'origin_name', 'total_trips']

# Después:
['start_date', 'end_date', 'date', 'destination_id', 'destination_name', 
 'origin_id', 'origin_name', 'total_trips']
```

**⚠️ STRICT MODE:** Si existiera una columna 'sense', 'sentido', 'sense_code' → **SE ELIMINA**

#### 1.3 Inferir checkpoint_id del nombre de archivo
```python
# filename = "checkpoint2002.csv"
# Extrae: checkpoint_id = "2002"
df_od['checkpoint_id'] = '2002'
```

#### 1.4 Preparar datos
Función: `prepare_data()`

**Transformación de total_trips → trips_person:**
```python
# Caso 1: "<10" → 1
df.loc[df['total_trips'].str.contains('<'), 'trips_person'] = 1

# Caso 2: Números < 10 → 1
df.loc[df['trips_person'] < 10, 'trips_person'] = 1

# Caso 3: NaN → 1 (conservador)
df['trips_person'].fillna(1)

# Resultado:
# "<10" → 1
# 5 → 1
# 15 → 15
# 250 → 250
```

**Calcular factor intrazonal:**
```python
# Si origin_id == destination_id → intrazonal_factor = 0 (anula el viaje)
# Si origin_id != destination_id → intrazonal_factor = 1 (mantiene el viaje)
df['intrazonal_factor'] = np.where(
    df['origin_id'] == df['destination_id'], 0, 1
)
```

**Estado al final del Paso 1:**
```
18956 filas × 11 columnas
Nuevas columnas: checkpoint_id, trips_person, intrazonal_factor, is_intrazonal
```

---

### **PASO 2: Cargar Grafo de Red Vial**
📁 Módulo: `src/kido_ruteo/routing/graph_loader.py`

#### 2.1 Cargar red desde GeoJSON
```python
G = load_graph_from_geojson('data/raw/red_extended.geojson')
# NetworkX MultiDiGraph con 95 nodos, 111 aristas
```

#### 2.2 Reprojectar a coordenadas proyectadas
```python
# De: EPSG:4326 (lat/lon geográfico)
# A: EPSG:32614 (UTM Zone 14N, metros)
# Los nodos pasan a tener IDs como: "476280.537027,2200403.216647"
# Atributo 'pos': (x_metros, y_metros)
```

---

### **PASO 3: Asignar Nodos a Zonas (Centroides)**
📁 Módulo: `src/kido_ruteo/processing/centroides.py`

#### 3.1 Cargar zonificación
```python
zones_gdf = gpd.read_file('data/raw/zonification/zonification.geojson')
# Contiene: polígonos de zonas + polígonos de checkpoints
```

#### 3.2 Filtrar solo zonas "Core"
```python
zones_gdf = zones_gdf[zones_gdf['poly_type'] == 'Core']
# Quedan: Amealco de Bonfil, Huimilpan, Apaseo el Grande, San Juan del Río, Tequisquiapan
```

#### 3.3 Calcular centroide de cada zona
Función: `assign_nodes_to_zones()`
```python
# Para cada polígono de zona:
1. Calcular centroide (centro geométrico)
2. Encontrar nodo más cercano en el grafo G
3. Asignar: zone_id → node_id

# Resultado: mapping zone_id → node_id
# Ejemplo: zona 131 → nodo "476280.537027,2200403.216647"
```

#### 3.4 Mapear centroides al DataFrame OD
Función: `add_centroid_coordinates_to_od()`
```python
# Para cada fila de df_od:
df_od['origin_node_id'] = map(origin_id → centroid_node_id)
df_od['destination_node_id'] = map(destination_id → centroid_node_id)

# Agrega también coordenadas:
df_od['origin_lat'], df_od['origin_lon']
df_od['dest_lat'], df_od['dest_lon']
```

**Estado al final del Paso 3:**
```
18956 filas × 17 columnas
Nuevas columnas: origin_node_id, destination_node_id, origin_lat, origin_lon, dest_lat, dest_lon
```

---

### **PASO 4: Cargar y Asignar Checkpoints**
📁 Módulo: `src/kido_ruteo/processing/checkpoint_loader.py`

#### 4.1 Extraer checkpoints de zonification.geojson
Función: `load_checkpoints_from_zonification()`
```python
# Filtrar features con poly_type='Checkpoint'
checkpoints = gdf[gdf['poly_type'] == 'Checkpoint']

# Extraer:
- checkpoint_id: del campo 'ID' (2001, 2002, 3003, ...)
- checkpoint_name: del campo 'NOMGEO' ('E01', 'E02', ...)
- geometry: centroide del polígono checkpoint

# Resultado: 26 checkpoints
```

#### 4.2 Asignar nodo más cercano a cada checkpoint
Función: `assign_checkpoint_nodes()`
```python
# Para cada checkpoint:
1. Proyectar centroide a EPSG:32614
2. Calcular distancia euclidiana a TODOS los nodos del grafo
3. Seleccionar el nodo más cercano
4. Guardar: checkpoint_id → checkpoint_node_id

# Ejemplo:
# checkpoint 2002 → nodo "475989.620854,2200356.447543"
# (a 46.7 km de distancia)
```

#### 4.3 Mapear checkpoint_node_id al DataFrame OD
```python
# Crear diccionario: checkpoint_id → checkpoint_node_id
checkpoint_dict = {
    '2002': '475989.620854,2200356.447543',
    '2001': '475959.876065,2200374.071919',
    ...
}

# Asignar a cada fila:
df_od['checkpoint_node_id'] = df_od['checkpoint_id'].map(checkpoint_dict)
```

**Estado al final del Paso 4:**
```
18956 filas × 18 columnas
Nueva columna: checkpoint_node_id
```

---

### **PASO 5: Calcular Rutas MC (Shortest Path)**
📁 Módulo: `src/kido_ruteo/routing/shortest_path.py`

Función: `compute_mc_matrix()`

#### 5.1 Para cada par origen-destino
```python
for cada fila en df_od:
    origin_node = fila['origin_node_id']
    dest_node = fila['destination_node_id']
    
    # Calcular camino más corto en el grafo G
    try:
        path = nx.shortest_path(G, origin_node, dest_node, weight='length')
        length = nx.shortest_path_length(G, origin_node, dest_node, weight='length')
    except nx.NetworkXNoPath:
        path = None
        length = NaN
```

#### 5.2 Guardar resultados
```python
df_od['mc_distance_m'] = length  # Distancia en metros
df_od['mc_path'] = path          # Lista de nodos en el camino
```

**Ejemplo de resultado:**
```python
# Fila 1:
origin_node_id = "476280.537027,2200403.216647"
destination_node_id = "476261.294511,2200392.641370"
mc_distance_m = 1250.5
mc_path = ["476280.537027,2200403.216647", "476270.123,2200398.456", ...]
```

**Estado al final del Paso 5:**
```
18956 filas × 20 columnas
Nuevas columnas: mc_distance_m, mc_path
```

---

### **PASO 6: Calcular Rutas MC2 (Constrained Path) y DERIVAR SENTIDO**
📁 Módulo: `src/kido_ruteo/routing/constrained_path.py`

Función: `compute_mc2_matrix()`

#### 6.1 Para cada par origen-destino que pasa por checkpoint
```python
for cada fila en df_od:
    origin_node = fila['origin_node_id']
    checkpoint_node = fila['checkpoint_node_id']
    dest_node = fila['destination_node_id']
    
    # Ruta restringida: Origen → Checkpoint → Destino
    try:
        # Tramo 1: origen → checkpoint
        path1 = nx.shortest_path(G, origin_node, checkpoint_node, weight='length')
        len1 = nx.shortest_path_length(G, origin_node, checkpoint_node, weight='length')
        
        # Tramo 2: checkpoint → destino
        path2 = nx.shortest_path(G, checkpoint_node, dest_node, weight='length')
        len2 = nx.shortest_path_length(G, checkpoint_node, dest_node, weight='length')
        
        # Ruta completa
        mc2_path = path1 + path2[1:]  # Evitar duplicar checkpoint
        mc2_distance = len1 + len2
    except:
        mc2_path = None
        mc2_distance = NaN
```

#### 6.2 **DERIVAR SENTIDO GEOMÉTRICAMENTE** ⭐
Función: `derive_sense_from_path()`

Esta es la **ÚNICA** forma de obtener `sense_code`. NUNCA se lee del input.

```python
def derive_sense_from_path(mc2_path, checkpoint_node_id, G, cardinality_df):
    """
    Deriva el sentido del checkpoint analizando la geometría de la ruta.
    """
    # 1. Encontrar posición del checkpoint en la ruta
    checkpoint_index = mc2_path.index(checkpoint_node_id)
    
    # 2. Obtener nodo anterior y siguiente al checkpoint
    if checkpoint_index > 0:
        before_node = mc2_path[checkpoint_index - 1]
    else:
        before_node = None
    
    if checkpoint_index < len(mc2_path) - 1:
        after_node = mc2_path[checkpoint_index + 1]
    else:
        after_node = None
    
    # 3. Calcular bearing (dirección) de entrada
    if before_node:
        # Obtener coordenadas del nodo anterior
        x1, y1 = G.nodes[before_node]['pos']
        x_cp, y_cp = G.nodes[checkpoint_node_id]['pos']
        
        # Calcular ángulo de entrada (en grados)
        bearing_in = math.atan2(y_cp - y1, x_cp - x1) * 180 / math.pi
    
    # 4. Calcular bearing de salida
    if after_node:
        x_cp, y_cp = G.nodes[checkpoint_node_id]['pos']
        x2, y2 = G.nodes[after_node]['pos']
        
        bearing_out = math.atan2(y2 - y_cp, x2 - x_cp) * 180 / math.pi
    
    # 5. Determinar dirección promedio
    avg_bearing = (bearing_in + bearing_out) / 2
    
    # 6. Mapear bearing a cardinalidad (Norte, Sur, Este, Oeste)
    # 0° = Este, 90° = Norte, 180° = Oeste, 270° = Sur
    if -45 <= avg_bearing < 45 or avg_bearing >= 315 or avg_bearing < -315:
        direction = 'Este'
        cardinality_code = 1
    elif 45 <= avg_bearing < 135:
        direction = 'Norte'
        cardinality_code = 2
    elif 135 <= avg_bearing < 225 or -225 <= avg_bearing < -135:
        direction = 'Oeste'
        cardinality_code = 3
    else:
        direction = 'Sur'
        cardinality_code = 4
    
    # 7. Buscar en catálogo sense_cardinality.csv
    # Este archivo mapea: (checkpoint_id, cardinality) → sense_code
    sense_row = cardinality_df[
        (cardinality_df['checkpoint_id'] == checkpoint_id) &
        (cardinality_df['cardinality'] == cardinality_code)
    ]
    
    if not sense_row.empty:
        sense_code = sense_row.iloc[0]['sense_code']
    else:
        sense_code = None  # No hay sentido válido
    
    return sense_code
```

**Ejemplo real:**
```python
# Ruta MC2: [..., nodo_A, checkpoint_2002, nodo_B, ...]
# 
# Nodo A: pos = (476000, 2200300)
# Checkpoint: pos = (475990, 2200356)  
# Nodo B: pos = (475980, 2200400)
#
# Bearing entrada: arctan((2200356-2200300) / (475990-476000)) = arctan(56/-10) ≈ -80° → Norte
# Bearing salida: arctan((2200400-2200356) / (475980-475990)) = arctan(44/-10) ≈ -77° → Norte
#
# Dirección promedio: Norte → cardinality_code = 2
#
# Buscar en sense_cardinality.csv:
# checkpoint_id=2002, cardinality=2 → sense_code = "1-3"
#
# RESULTADO: sense_code = "1-3"
```

#### 6.3 Guardar resultados
```python
df_od['mc2_distance_m'] = mc2_distance
df_od['mc2_path'] = mc2_path
df_od['sense_code'] = sense_code  # ⭐ DERIVADO GEOMÉTRICAMENTE
```

**Estado al final del Paso 6:**
```
18956 filas × 23 columnas
Nuevas columnas: mc2_distance_m, mc2_path, sense_code
```

---

### **PASO 7: Integrar Capacidad del Checkpoint**
📁 Módulo: `src/kido_ruteo/capacity/matcher.py`

Función: `match_capacity_to_od()`

#### 7.1 Cargar archivo de capacidad
```python
df_capacity = pd.read_csv('data/raw/capacity/summary_capacity.csv')
```

**Contenido de summary_capacity.csv:**
```csv
Checkpoint,Sentido,Capacidad_AU,Capacidad_CU,Capacidad_CAI,Capacidad_CAII
2002,0,1200,300,150,50
2002,1-3,1500,400,200,80
2002,3-1,1400,350,180,70
```

#### 7.2 **MATCH EXACTO** (checkpoint_id, sense_code)
```python
# STRICT MODE: Solo merge EXACTO, sin fallback
merged = pd.merge(
    df_od,
    df_capacity,
    left_on=['checkpoint_id', 'sense_code'],
    right_on=['Checkpoint', 'Sentido'],
    how='left',  # Left join mantiene todas las filas de OD
    validate='many_to_one'
)

# Si NO hay match:
# - sense_code = None → No hace match con ninguna fila de capacity
# - Resultado: cap_au = NaN, cap_cu = NaN, ...
#
# Si HAY match:
# - sense_code = "1-3" → Busca (2002, "1-3") en capacity
# - Resultado: cap_au = 1500, cap_cu = 400, ...
```

#### 7.3 Calcular capacidad total
```python
df_od['cap_total'] = (
    df_od['cap_au'].fillna(0) + 
    df_od['cap_cu'].fillna(0) +
    df_od['cap_cai'].fillna(0) + 
    df_od['cap_caii'].fillna(0)
)

# Si todas las capacidades son NaN → cap_total = 0
# Luego se convierte a NaN si corresponde
```

**Estado al final del Paso 7:**
```
18956 filas × 28 columnas
Nuevas columnas: cap_au, cap_cu, cap_cai, cap_caii, cap_total
```

---

### **PASO 8: Calcular Congruencia**
📁 Módulos: `congruence/potential.py`, `congruence/scoring.py`, `congruence/classification.py`

#### 8.1 Calcular Potencial
Función: `calculate_potential()`
```python
# Compara distancia MC (directa) vs MC2 (por checkpoint)
df_od['detour_ratio'] = df_od['mc2_distance_m'] / df_od['mc_distance_m']

# Reglas:
# - Si detour_ratio < 1.1 (desvío < 10%) → id_potential = 1
# - Si detour_ratio < 1.3 → id_potential = 2
# - Si detour_ratio < 1.5 → id_potential = 3
# - Si detour_ratio >= 1.5 → id_potential = 0 (no potencial)
```

#### 8.2 Calcular Scores
Función: `calculate_scores()`
```python
# Score de capacidad: ¿Hay capacidad suficiente?
df_od['score_capacity'] = np.where(
    df_od['cap_total'] > 0, 
    1.0,  # Hay capacidad
    0.0   # No hay capacidad
)

# Otros scores (distancia, intrazonal, etc.)
```

#### 8.3 Clasificar Congruencia
Función: `classify_congruence()`
```python
# REGLA CLAVE STRICT MODE:
# Si cap_total es NaN o 0 → congruence_id = 4 (Impossible)

conditions = [
    (df['id_potential'] == 0),           # → congruence_id = 4
    (df['cap_total'].isna()),            # → congruence_id = 4 ⭐ STRICT
    (df['cap_total'] == 0),              # → congruence_id = 4 ⭐ STRICT
    (df['score_capacity'] == 0),         # → congruence_id = 4
    (df['score_combined'] > 0.8),        # → congruence_id = 1
    (df['score_combined'] > 0.5),        # → congruence_id = 2
    (df['score_combined'] > 0.2),        # → congruence_id = 3
]

choices = [4, 4, 4, 4, 1, 2, 3]
default = 4

df['congruence_id'] = np.select(conditions, choices, default=default)
```

**Mapeo congruence_id → etiqueta:**
```python
1 → "Extremely Possible"
2 → "Possible"
3 → "Marginally Possible"
4 → "Impossible"
```

**Estado al final del Paso 8:**
```
18956 filas × 33 columnas
Nuevas columnas: id_potential, detour_ratio, score_*, congruence_id, congruence_label
```

---

### **PASO 9: Calcular Viajes Vehiculares**
📁 Módulo: `src/kido_ruteo/trips/calculation.py`

Función: `calculate_vehicle_trips()`

#### 9.1 Aplicar factores de ocupación
```python
# Factores de ocupación vehicular (personas/vehículo)
OCCUPANCY = {
    'auto': 1.5,
    'cu': 2.5,
    'cai': 12.0,
    'caii': 25.0
}

# Para cada tipo de vehículo:
df['veh_auto'] = (df['trips_person'] / OCCUPANCY['auto']) * df['intrazonal_factor']
df['veh_cu'] = (df['trips_person'] / OCCUPANCY['cu']) * df['intrazonal_factor']
df['veh_cai'] = (df['trips_person'] / OCCUPANCY['cai']) * df['intrazonal_factor']
df['veh_caii'] = (df['trips_person'] / OCCUPANCY['caii']) * df['intrazonal_factor']
```

#### 9.2 **STRICT MODE: Propagar NaN**
```python
# Si cap_total es NaN → TODOS los veh_* deben ser NaN
missing_capacity = df['cap_total'].isna()

df.loc[missing_capacity, 'veh_auto'] = np.nan
df.loc[missing_capacity, 'veh_cu'] = np.nan
df.loc[missing_capacity, 'veh_cai'] = np.nan
df.loc[missing_capacity, 'veh_caii'] = np.nan

# NUNCA convertir NaN a 0
```

#### 9.3 Calcular total
```python
df['veh_total'] = (
    df['veh_auto'].fillna(0) + 
    df['veh_cu'].fillna(0) + 
    df['veh_cai'].fillna(0) + 
    df['veh_caii'].fillna(0)
)

# Si TODOS los veh_* son NaN → veh_total = 0
# Luego convertir ese 0 a NaN:
all_nan = df[['veh_auto', 'veh_cu', 'veh_cai', 'veh_caii']].isna().all(axis=1)
df.loc[all_nan, 'veh_total'] = np.nan
```

**Ejemplo de cálculo:**
```python
# Fila con trips_person=250, intrazonal_factor=1, cap_total=1700:
veh_auto = 250 / 1.5 * 1 = 166.67
veh_cu = 250 / 2.5 * 1 = 100.00
veh_cai = 250 / 12.0 * 1 = 20.83
veh_caii = 250 / 25.0 * 1 = 10.00
veh_total = 166.67 + 100.00 + 20.83 + 10.00 = 297.50

# Fila con sense_code=None (sin capacidad):
veh_auto = NaN
veh_cu = NaN
veh_cai = NaN
veh_caii = NaN
veh_total = NaN
```

**Estado al final del Paso 9:**
```
18956 filas × 38 columnas
Nuevas columnas: veh_auto, veh_cu, veh_cai, veh_caii, veh_total
```

---

### **PASO 10: Extraer y Renombrar Columnas de Salida**
📁 Módulo: `src/kido_ruteo/pipeline.py` (final)

#### 10.1 Renombrar columnas según especificación
```python
rename_map = {
    'origin_id': 'Origen',
    'destination_id': 'Destino',
    'veh_auto': 'veh_AU',
    'veh_cu': 'veh_CU',
    'veh_cai': 'veh_CAI',
    'veh_caii': 'veh_CAII'
}

df_od = df_od.rename(columns=rename_map)
```

#### 10.2 Seleccionar SOLO las 7 columnas finales
```python
output_columns = [
    'Origen',      # ID de zona origen
    'Destino',     # ID de zona destino
    'veh_AU',      # Vehículos tipo Auto
    'veh_CU',      # Vehículos tipo Camioneta Utilitaria
    'veh_CAI',     # Vehículos tipo Camión Articulado I
    'veh_CAII',    # Vehículos tipo Camión Articulado II
    'veh_total'    # Total de vehículos
]

df_final = df_od[output_columns]
```

#### 10.3 Guardar archivo CSV
```python
output_file = 'data/processed/processed_checkpoint2002.csv'
df_final.to_csv(output_file, index=False)
```

---

## 📤 ARCHIVO DE SALIDA

**Archivo:** `data/processed/processed_checkpoint2002.csv`

**Contenido:**
```csv
Origen,Destino,veh_AU,veh_CU,veh_CAI,veh_CAII,veh_total
1001,1002,NaN,NaN,NaN,NaN,NaN
1002,1001,NaN,NaN,NaN,NaN,NaN
115,1001,NaN,NaN,NaN,NaN,NaN
...
```

**Estructura:**
```
18956 filas × 7 columnas
TODAS las filas = NaN (porque sense_code = None por falta de geometría válida)
```

---

## ⚠️ POR QUÉ SALEN TODO NaN

### Cadena de causas:

1. **Checkpoints muy alejados de la red**
   - Checkpoint 2002 está a 46.7 km del nodo más cercano
   - La red solo tiene 95 nodos en una región específica

2. **Rutas MC2 inválidas**
   - Al calcular origen → checkpoint → destino
   - Las distancias son irreales (cientos de kilómetros de desvío)
   - `mc2_distance_m` = valores muy grandes o NaN

3. **sense_code = None**
   - La función `derive_sense_from_path()` recibe rutas inválidas
   - No puede calcular bearings correctos
   - Retorna `sense_code = None`

4. **Sin match de capacidad**
   - Al hacer merge con `(checkpoint_id='2002', sense_code=None)`
   - No encuentra fila en summary_capacity.csv
   - Resultado: `cap_au=NaN, cap_cu=NaN, ..., cap_total=NaN`

5. **Propagación de NaN**
   - STRICT MODE: Si `cap_total.isna()` → todos los `veh_*` = NaN
   - `veh_total` = NaN

6. **Salida final**
   - 7 columnas, todas con NaN
   - **NO hay datos de viajes porque NO hay geometría válida**

---

## ✅ CÓMO SE VERÍA CON DATOS CORRECTOS

Si los checkpoints estuvieran cerca de la red (<1km):

```csv
Origen,Destino,veh_AU,veh_CU,veh_CAI,veh_CAII,veh_total
1001,1002,166.67,100.00,20.83,10.00,297.50
1002,1001,0.67,0.40,0.08,0.04,1.19
115,1001,10.00,6.00,1.25,0.50,17.75
119,1001,133.33,80.00,16.67,6.67,236.67
...
```

Con:
- Rutas MC2 válidas (distancias razonables)
- sense_code derivado correctamente (ej: "1-3", "3-1")
- Capacidad matched (ej: cap_total = 1700)
- Viajes calculados según ocupación vehicular

---

## 🎯 RESUMEN EJECUTIVO

**Transformación completa:**
```
checkpoint2002.csv (8 columnas, trips_person)
    ↓ [10 pasos de procesamiento]
processed_checkpoint2002.csv (7 columnas, veh_*)
```

**Pasos críticos:**
1. ✅ Normalización y limpieza de datos
2. ✅ Asignación de centroides a nodos de red
3. ✅ Carga de checkpoints desde zonification.geojson
4. ✅ Cálculo de rutas MC y MC2
5. ⭐ **Derivación geométrica de sense_code** (ÚNICA fuente)
6. ✅ Match exacto con capacidad (sin fallback)
7. ✅ Clasificación de congruencia
8. ✅ Cálculo de viajes vehiculares
9. ✅ Propagación estricta de NaN
10. ✅ Salida limpia de 7 columnas

**Razón de NaN actuales:**
- Desalineación geográfica entre red, zonas y checkpoints
- Imposible calcular rutas y sentidos válidos
- Sin sentido → sin capacidad → sin viajes

**Solución necesaria:**
- Red vial que cubra la región de los checkpoints
- O checkpoints dentro del área de la red actual
