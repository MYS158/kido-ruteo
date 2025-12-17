# KIDO-Ruteo v2.0 - STRICT MODE Documentation

## 🎯 Filosofía del Sistema

El proyecto KIDO-Ruteo v2.0 opera bajo un modelo de **Validación Estricta** donde:

- **La geometría es la fuente de verdad absoluta**
- **No existen aproximaciones ni respaldos**
- **Los datos faltantes se respetan como NaN, nunca se sustituyen por 0**
- **La coincidencia exacta es el único criterio de validez**

## ✅ Reglas de Negocio OBLIGATORIAS

### 1️⃣ Sentido (sense_code)

#### Eliminación del Input
```python
# ❌ PROHIBIDO: Leer sentido del archivo de entrada
df['sense_code'] = input_data['sentido']  # NEVER

# ✅ CORRECTO: Eliminar cualquier columna de sentido
if 'sentido' in df.columns:
    df = df.drop(columns=['sentido'])
```

#### Derivación Geométrica
El sentido **SIEMPRE** se deriva de la ruta MC2:
- Origen → Checkpoint → Destino
- Usando bearings (ángulos) en el nodo del checkpoint
- Cardinalidad fija:
  - **1** = Norte (315° - 45°)
  - **2** = Este (45° - 135°)
  - **3** = Sur (135° - 225°)
  - **4** = Oeste (225° - 315°)

**Formato**: `"X-Y"` donde:
- `X` = Cardinalidad de origen (de dónde viene)
- `Y` = Cardinalidad de destino (hacia dónde va)

**Ejemplo**: `"4-2"` = Viene del Oeste, va al Este

#### Implementación
```python
# src/kido_ruteo/routing/constrained_path.py
def derive_sense_from_path(G, path, checkpoint_node):
    """
    ÚNICA función autorizada para crear sense_code.
    """
    # Calcular bearings de entrada y salida
    bearing_in = calculate_bearing(G, prev_node, checkpoint)
    bearing_out = calculate_bearing(G, checkpoint, next_node)
    
    # Asignar cardinalidad
    origin_card = get_cardinality(bearing_in, is_origin=True)
    dest_card = get_cardinality(bearing_out, is_origin=False)
    
    return f"{origin_card}-{dest_card}"
```

---

### 2️⃣ Ruteo

#### Dos Rutas Complementarias
1. **MC (Camino Mínimo Libre)**: Ruta más corta sin restricciones
2. **MC2 (Camino Mínimo Restringido)**: Ruta más corta que DEBE pasar por el checkpoint

**El sentido SOLO se deriva de MC2.**

```python
# MC: Origen → Destino (directo)
df = compute_mc_matrix(df, G)

# MC2: Origen → Checkpoint → Destino (forzado)
df = compute_mc2_matrix(df, G)  # Aquí se crea sense_code
```

---

### 3️⃣ Asignación de Capacidad (STRICT MODE)

#### Cruce EXACTO
```python
# Cruce usando (Checkpoint, Sentido) como llaves compuestas
merged = pd.merge(
    df_od,
    df_capacity,
    left_on=['checkpoint_id', 'sense_code'],
    right_on=['Checkpoint', 'Sentido'],
    how='left',  # Left join: preservar todos los OD
    validate='many_to_one'  # Validar unicidad de capacidad
)
```

#### Prohibiciones Absolutas

❌ **PROHIBIDO #1**: Usar Sentido '0' como respaldo
```python
# ❌ NUNCA hacer esto:
if sense_code not in capacity:
    use_sense_0_instead()  # PROHIBITED
```

❌ **PROHIBIDO #2**: Sumar sentidos opuestos
```python
# ❌ NUNCA hacer esto:
if not found('1-3'):
    cap = cap['3-1'] + cap['1-3']  # PROHIBITED
```

❌ **PROHIBIDO #3**: Promediar capacidades
```python
# ❌ NUNCA hacer esto:
cap = (cap_sense_1 + cap_sense_2) / 2  # PROHIBITED
```

❌ **PROHIBIDO #4**: Inferir simetría direccional
```python
# ❌ NUNCA hacer esto:
if not found('1-3'):
    cap['1-3'] = cap['3-1']  # PROHIBITED - No symmetry assumption
```

#### Resultado de No-Match
Si `sense_code` no existe en `summary_capacity.csv`:
```python
# Todas las columnas de capacidad = NaN
cap_total = NaN
capacity_fa = NaN
focup_auto = NaN
# ...etc
```

---

### 4️⃣ Congruencia

#### Clasificación Estricta
```python
def classify_congruence(df):
    conditions = [
        (df['id_potential'] == 0),           # → congruence_id = 4
        (df['cap_total'].isna()),             # → congruence_id = 4 (CRITICAL)
        (df['e1'].between(0.9, 1.2) & df['e2'] >= 0.8),  # → 1
        (df['e1'].between(0.8, 1.5) & df['e2'] >= 0.5),  # → 2
        (df['e1'] < 2.0)                      # → 3
    ]
    choices = [4, 4, 1, 2, 3]
    df['congruence_id'] = np.select(conditions, choices, default=4)
```

**Regla Crítica**: Si no hay capacidad → Congruence = 4 (Impossible)

#### Interpretación
- **1**: Extremadamente Posible
- **2**: Posible
- **3**: Poco Probable
- **4**: Imposible (No genera viajes)

---

### 5️⃣ Cálculo Vehicular

#### Fórmula
Solo se aplica si **existe capacidad**:
```python
# 1. Ajuste de demanda
trips_adjusted = trips_person × FA

# 2. Split por categoría
share_cat = cap_cat / cap_total

# 3. Conversión a vehículos
veh_cat = (trips_adjusted × share_cat) / Focup_cat
```

#### Manejo de NaN
```python
# Si capacidad es NaN → veh_* = NaN (NUNCA 0)
if pd.isna(cap_total):
    veh_auto = NaN
    veh_cu = NaN
    veh_cai = NaN
    veh_caii = NaN
    veh_total = NaN
```

#### Filtro de Validez
```python
valid_mask = (
    (id_potential == 1) &
    (congruence_id < 4) &
    (intrazonal_factor == 1)
)

# Si invalid → veh_* = 0
# Si capacidad missing → veh_* = NaN
veh_x = veh_x.where(valid_mask, 0.0)
veh_x = veh_x.mask(missing_capacity, np.nan)
```

---

### 6️⃣ Salida FINAL (Limpia)

#### Columnas Permitidas
El archivo de salida debe contener **ÚNICAMENTE**:
```python
output_cols = [
    'Origen',      # origin_id renombrado
    'Destino',     # destination_id renombrado
    'veh_AU',      # veh_auto renombrado
    'veh_CU',      # veh_cu renombrado
    'veh_CAI',     # veh_cai renombrado
    'veh_CAII',    # veh_caii renombrado
    'veh_total'    # suma de categorías
]
```

#### Columnas PROHIBIDAS en Output
❌ No incluir:
- Geometría (coordinates, paths, shapes)
- Distancias (mc_distance_m, mc2_distance_m)
- Flags internos (has_valid_path, cap_available, sense_valid)
- Columnas de auditoría (checkpoint_id, sense_code, congruence_id)
- Scores intermedios (e1, e2, id_potential)

```python
# ❌ PROHIBIDO
df_output = df[['origin_id', 'destination_id', 'checkpoint_id', 'sense_code', ...]]

# ✅ CORRECTO
df_output = df[['Origen', 'Destino', 'veh_AU', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total']]
```

---

## 🧪 Tests Obligatorios

### Test 1: Sentido NO se lee del input
```python
def test_sense_not_read_from_input():
    df_input = pd.DataFrame({
        'sentido': ['BAD_VALUE'],  # Debe ser eliminado
    })
    df_cleaned = normalize_column_names(df_input)
    assert 'sentido' not in df_cleaned.columns
```

### Test 2: Sentido se deriva de geometría
```python
def test_sense_derived_from_geometry():
    # Ruta: West → Checkpoint → East
    sense = derive_sense_from_path(G, path, checkpoint)
    assert sense == "4-2"  # Oeste → Este
```

### Test 3: NO existe fallback a Sentido 0
```python
def test_no_fallback_to_sense_zero():
    df_od = pd.DataFrame({'sense_code': ['4-2']})
    df_capacity = pd.DataFrame({'Sentido': ['0', '1-3']})  # No tiene '4-2'
    
    result = match_capacity_to_od(df_od, df_capacity)
    
    assert pd.isna(result['cap_total'])  # Debe ser NaN, no el valor de '0'
```

### Test 4: Sin match exacto → veh_* = NaN
```python
def test_missing_capacity_results_in_nan():
    df['cap_total'] = NaN
    df = calculate_vehicle_trips(df)
    
    assert pd.isna(df['veh_auto'])
    assert pd.isna(df['veh_total'])
    assert df['veh_auto'] != 0  # NUNCA 0
```

### Test 5: veh_total solo existe si todas las categorías son válidas
```python
def test_veh_total_requires_all_categories():
    df['cap_total'] = 500  # Existe
    df = calculate_vehicle_trips(df)
    
    # Si alguna categoría es NaN, total debe ser NaN
    if pd.isna(df['veh_auto']) or pd.isna(df['veh_cu']):
        assert pd.isna(df['veh_total'])
```

---

## 🔍 Flujo Completo del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INGESTA                                                      │
│    - Leer OD CSV                                                │
│    - ELIMINAR cualquier columna 'sentido'/'sense'               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. GEOMETRÍA Y GRAFO                                            │
│    - Cargar red vial (GeoJSON)                                  │
│    - Asignar centroides a zonas                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RUTEO (El Núcleo)                                            │
│    ┌────────────────────────────────────────────────────────┐   │
│    │ MC: Origen → Destino (libre)                          │   │
│    └────────────────────────────────────────────────────────┘   │
│    ┌────────────────────────────────────────────────────────┐   │
│    │ MC2: Origen → Checkpoint → Destino (forzado)          │   │
│    │ └─→ AQUÍ se deriva sense_code geométricamente         │   │
│    └────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CAPACIDAD (STRICT MODE)                                      │
│    - Cruce EXACTO: (checkpoint_id, sense_code) vs capacity     │
│    - Sin match → cap_* = NaN                                    │
│    - NO fallback a Sentido '0'                                  │
│    - NO promedios, NO inferencias                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CONGRUENCIA                                                  │
│    - Si cap_total = NaN → congruence_id = 4 (Impossible)       │
│    - Si congruence = 4 → NO se generan viajes                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. CÁLCULO VEHICULAR                                            │
│    - Fórmula: veh = (trips × FA × share) / Focup               │
│    - Si cap = NaN → veh = NaN (NUNCA 0)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. SALIDA LIMPIA                                                │
│    - SOLO: Origen, Destino, veh_AU, veh_CU, veh_CAI,          │
│            veh_CAII, veh_total                                  │
│    - SIN auditoría, geometría, flags, scores                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Checklist de Implementación

### ✅ Preprocessing
- [x] Eliminar columnas `sentido`/`sense`/`sense_code` del input
- [x] Mensaje de advertencia cuando se detectan
- [x] Normalización de columnas estándar (origin → origin_id)

### ✅ Ruteo
- [x] Calcular MC (ruta libre)
- [x] Calcular MC2 (ruta forzada por checkpoint)
- [x] Derivar `sense_code` SOLO de MC2
- [x] Usar bearings y cardinalidad (1=N, 2=E, 3=S, 4=W)

### ✅ Capacidad
- [x] Cruce EXACTO con `pd.merge` (checkpoint_id, sense_code)
- [x] Eliminar función `resolve_checkpoint_capacity`
- [x] Eliminar fallback a Sentido '0'
- [x] Sin match → cap_* = NaN

### ✅ Congruencia
- [x] cap_total.isna() → congruence_id = 4
- [x] Clasificación 1-4 basada en scores E1/E2

### ✅ Cálculo Vehicular
- [x] Aplicar fórmula solo si capacidad existe
- [x] missing_capacity → veh_* = NaN (NUNCA 0)
- [x] Filtro: (id_potential==1) & (congruence<4) & (intrazonal==1)

### ✅ Salida
- [x] Renombrar: veh_auto → veh_AU, origin_id → Origen
- [x] Filtrar columnas: SOLO las 7 requeridas
- [x] Sin geometría, distancias, flags

### ✅ Tests
- [x] test_sense_not_read_from_input
- [x] test_no_fallback_to_sense_zero
- [x] test_exact_match_works
- [x] test_multiple_missing_senses

---

## 🚨 Errores Comunes a Evitar

### ❌ Error 1: Confundir 0 con NaN
```python
# ❌ INCORRECTO
if cap_total == 0:
    veh_total = 0

# ✅ CORRECTO
if pd.isna(cap_total):
    veh_total = np.nan  # NaN significa "sin datos", 0 significa "cero tráfico"
```

### ❌ Error 2: Leer sentido del input "por si acaso"
```python
# ❌ INCORRECTO
if 'sense_code' in df.columns:
    use_input_sense = df['sense_code']
else:
    derive_sense_from_geometry()

# ✅ CORRECTO
# SIEMPRE eliminar y SIEMPRE derivar
df = df.drop(columns=['sense_code'], errors='ignore')
df['sense_code'] = derive_sense_from_path(G, path, checkpoint)
```

### ❌ Error 3: Usar Sentido '0' como "valor por defecto"
```python
# ❌ INCORRECTO
merged_exact = merge_on_specific_sense()
merged_fallback = merge_on_sense_zero()
result = merged_exact.combine_first(merged_fallback)

# ✅ CORRECTO
merged = merge_on_specific_sense()  # Solo esto. Nada más.
```

---

## 📖 Referencias

- [BUSINESS_INVARIANTS.md](./BUSINESS_INVARIANTS.md): Invariantes del sistema
- [business_rules.md](./business_rules.md): Reglas de negocio completas
- [DATA_CONTRACT.md](./DATA_CONTRACT.md): Contrato de datos
- [output_schema.md](./output_schema.md): Esquema de salida

---

## 🔄 Historial de Cambios

### v2.0.0 - STRICT MODE (2025-12-17)
- ✅ Eliminación total de fallback a Sentido '0'
- ✅ Forzar derivación geométrica de sense_code
- ✅ Eliminación de columnas de sentido del input
- ✅ Manejo estricto de NaN vs 0
- ✅ Salida limpia con solo 7 columnas
- ✅ Suite completa de tests de validación

### v1.x - Legacy (Deprecated)
- ❌ Usaba Sentido '0' como respaldo
- ❌ Aceptaba sentido del input
- ❌ Promediaba capacidades faltantes
