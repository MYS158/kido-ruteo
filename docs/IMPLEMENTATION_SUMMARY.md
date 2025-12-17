# KIDO-Ruteo v2.0 - Resumen de Implementación STRICT MODE

## ✅ Cambios Completados

### 1. Eliminación de Sentido del Input
**Archivo**: `src/kido_ruteo/processing/preprocessing.py`

**Antes**:
```python
if 'sentido' in df.columns:
    df.rename(columns={'sentido': 'sense_code'}, inplace=True)
```

**Después (STRICT MODE)**:
```python
# Detectar y ELIMINAR cualquier columna de sentido
cols_to_drop = []
for col in df.columns:
    if col in ['sentido', 'sense', 'sense_code', 'direccion', 'direction']:
        cols_to_drop.append(col)

if cols_to_drop:
    df = df.drop(columns=cols_to_drop)
    print(f"⚠️  STRICT MODE: Columnas de sentido eliminadas del input: {cols_to_drop}")
```

**Resultado**: El sentido NUNCA se lee del input. Se muestra advertencia explícita al usuario.

---

### 2. Derivación Geométrica del Sentido
**Archivo**: `src/kido_ruteo/routing/constrained_path.py`

**Función clave**: `derive_sense_from_path()`

```python
def derive_sense_from_path(G: nx.Graph, path: List[str], checkpoint_node: str) -> Optional[str]:
    """
    STRICT MODE: Deriva el código de sentido desde la GEOMETRÍA.
    
    El sentido SIEMPRE se calcula geométricamente a partir de la ruta:
    Origen → Checkpoint → Destino
    
    Cardinalidad fija: 1=Norte, 2=Este, 3=Sur, 4=Oeste
    Formato: "X-Y" donde X=origen, Y=destino
    
    NUNCA se lee del input. NUNCA se asume. SOLO se deriva.
    """
```

**Resultado**: El sentido se crea ÚNICAMENTE en `compute_mc2_matrix()` después de calcular la ruta forzada.

---

### 3. Eliminación del Fallback a Sentido '0'
**Archivo**: `src/kido_ruteo/capacity/matcher.py`

**Antes (PROHIBIDO)**:
```python
def resolve_checkpoint_capacity(df_capacity):
    """
    Agregaba capacidades para crear Sentido '0' (promedio)
    """
    # ... 80 líneas de código de agregación ...

merged_exact = pd.merge(...)  # Match específico
merged_fallback = pd.merge(...)  # Match con Sentido '0'
result = merged_exact.combine_first(merged_fallback)  # ❌ FALLBACK
```

**Después (STRICT MODE)**:
```python
def match_capacity_to_od(df_od, df_capacity):
    """
    STRICT MODE:
    - Match EXACTO de (Checkpoint, Sentido).
    - NO fallback a Sentido '0'.
    - NO agregación de capacidades.
    """
    merged = pd.merge(
        df_od,
        df_capacity,
        left_on=['checkpoint_id', 'sense_code'],
        right_on=['Checkpoint', 'Sentido'],
        how='left',  # SOLO left join, sin fallback
        validate='many_to_one'
    )
    # Si no hay match: cap_* = NaN
```

**Resultado**: 
- ✅ Función `resolve_checkpoint_capacity` completamente eliminada
- ✅ NO existe merge secundario con Sentido '0'
- ✅ Sin match exacto → capacidad = NaN

---

### 4. Congruencia Estricta con Capacidad
**Archivo**: `src/kido_ruteo/congruence/classification.py`

**Validación añadida**:
```python
conditions = [
    (df['id_potential'] == 0),        # → Impossible
    (df['cap_total'].isna()),         # ← NUEVO: Sin capacidad → Impossible
    (df['e1'].between(0.9, 1.2) & df['e2'] >= 0.8),  # → Extremely Possible
    # ...
]
```

**Resultado**: Si no existe match de capacidad, el viaje se marca como "Imposible" (congruence_id=4).

---

### 5. Cálculo Vehicular con Manejo Estricto de NaN
**Archivo**: `src/kido_ruteo/trips/calculation.py`

**Actualizado**:
```python
# STRICT RULE 5: Aplicar validez
# Si invalid (congruence) → 0.0
# Si capacidad missing → NaN (NUNCA 0)
veh_x = veh_x.where(valid_mask, 0.0)
veh_x = veh_x.mask(missing_capacity, np.nan)  # ← CRÍTICO

# STRICT: Si alguna categoría es NaN, el total debe ser NaN
df.loc[missing_capacity, 'veh_total'] = np.nan
```

**Resultado**: 
- ✅ NaN se propaga correctamente (no se convierte en 0)
- ✅ veh_total es NaN si cualquier categoría es NaN
- ✅ Semántica: NaN = "sin datos", 0 = "cero tráfico"

---

### 6. Salida Limpia (Solo 7 Columnas)
**Archivo**: `src/kido_ruteo/pipeline.py`

**Antes**:
```python
output_cols = [
    'origin_id', 'destination_id', 
    'veh_auto', 'veh_bus', 'veh_cu', 'veh_cai', 'veh_caii', 'veh_total'
]
```

**Después (STRICT MODE)**:
```python
# Renombrar columnas según especificación
rename_veh = {
    'origin_id': 'Origen',
    'destination_id': 'Destino',
    'veh_auto': 'veh_AU',
    'veh_cu': 'veh_CU',
    'veh_cai': 'veh_CAI',
    'veh_caii': 'veh_CAII'
}

df_od = df_od.rename(columns=rename_veh)

output_cols = [
    'Origen', 'Destino', 
    'veh_AU', 'veh_CU', 'veh_CAI', 'veh_CAII', 'veh_total'
]

df_final = df_od[output_cols]  # SOLO estas columnas
```

**Resultado**:
- ✅ Sin geometría
- ✅ Sin distancias
- ✅ Sin flags de auditoría
- ✅ Sin columnas intermedias
- ✅ Columnas renombradas según especificación

---

## 🧪 Tests Implementados

**Archivo**: `tests/test_strict_capacity.py`

### Test 1: NO fallback a Sentido 0
```python
def test_no_fallback_to_sense_zero():
    # OD con sentido '4-2'
    # Capacidad solo tiene '0' y '1-3'
    # Resultado esperado: cap_total = NaN
    assert pd.isna(result['cap_total'])
```
**Status**: ✅ PASSED

### Test 2: Match exacto funciona
```python
def test_exact_match_works():
    # OD con sentido '1-3'
    # Capacidad tiene '1-3'
    # Resultado esperado: cap_total = 500
    assert result['cap_total'] == 500
```
**Status**: ✅ PASSED

### Test 3: Sentido NO se lee del input
```python
def test_sense_not_read_from_input():
    # Input con columnas 'sentido' y 'sense'
    # Resultado esperado: ambas eliminadas
    assert 'sentido' not in df_cleaned.columns
    assert 'sense' not in df_cleaned.columns
```
**Status**: ✅ PASSED

### Test 4: Múltiples sentidos faltantes
```python
def test_multiple_missing_senses():
    # 3 viajes con sentidos que no existen en capacidad
    # Resultado esperado: todos con cap_total = NaN
    for i in range(3):
        assert pd.isna(result.iloc[i]['cap_total'])
```
**Status**: ✅ PASSED

---

## 📊 Resumen de Reglas Implementadas

| # | Regla | Implementado | Archivo | Línea |
|---|-------|--------------|---------|-------|
| 1️⃣ | Sentido NO se lee del input | ✅ | `preprocessing.py` | 10-25 |
| 2️⃣ | Sentido se deriva SOLO de MC2 | ✅ | `constrained_path.py` | 115-125 |
| 3️⃣ | NO fallback a Sentido '0' | ✅ | `matcher.py` | 1-65 |
| 4️⃣ | Sin capacidad → congruence=4 | ✅ | `classification.py` | 14-16 |
| 5️⃣ | Capacidad missing → veh_*=NaN | ✅ | `calculation.py` | 60-80 |
| 6️⃣ | Salida limpia (7 columnas) | ✅ | `pipeline.py` | 158-175 |

---

## 📝 Documentación Creada

1. **`docs/STRICT_MODE.md`** (este archivo)
   - Filosofía del sistema
   - Reglas de negocio detalladas
   - Ejemplos de código
   - Checklist de implementación
   - Errores comunes a evitar

---

## 🚦 Estado del Proyecto

### ✅ Completado
- [x] Eliminación de sense del input
- [x] Derivación geométrica obligatoria
- [x] Eliminación de fallback a Sentido '0'
- [x] Manejo estricto de NaN vs 0
- [x] Congruencia forzada cuando falta capacidad
- [x] Salida limpia con 7 columnas
- [x] Tests completos (4/4 passing)
- [x] Documentación exhaustiva

### ⚠️ Pendiente (Opcional)
- [ ] Resolver problema de compatibilidad Python 3.14 + NetworkX
  - **Workaround**: Usar Python 3.11 o 3.12
  - **Alternativa**: Esperar actualización de NetworkX
- [ ] Tests de integración end-to-end
- [ ] Performance benchmarking

---

## 📖 Archivos Modificados

```
src/kido_ruteo/
├── capacity/
│   └── matcher.py                    ← Eliminado fallback, función resolve_*
├── congruence/
│   └── classification.py             ← Añadida validación cap_total.isna()
├── processing/
│   └── preprocessing.py              ← Eliminación activa de sense del input
├── routing/
│   └── constrained_path.py           ← Docstrings STRICT MODE
├── trips/
│   └── calculation.py                ← Manejo estricto NaN vs 0
└── pipeline.py                       ← Salida limpia (7 columnas)

tests/
└── test_strict_capacity.py           ← Suite completa de tests

docs/
├── STRICT_MODE.md                    ← Documentación completa
└── IMPLEMENTATION_SUMMARY.md         ← Este archivo
```

---

## 🎯 Conclusión

El proyecto KIDO-Ruteo v2.0 ha sido completamente actualizado para operar bajo el modelo **STRICT MODE**:

✅ **Geometría como fuente de verdad absoluta**  
✅ **Cero tolerancia a fallbacks o aproximaciones**  
✅ **NaN significa "sin datos", nunca se sustituye por 0**  
✅ **Solo se procesan coincidencias exactas**  

Todos los tests pasan exitosamente. La documentación completa está disponible en `docs/STRICT_MODE.md`.
