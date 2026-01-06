# KIDO-Ruteo v2.0

Pipeline de ruteo y cálculo vehicular para matrices Origen-Destino (OD) bajo reglas **STRICT MODE**.

## 📚 Documentación (fuente de verdad)

- `docs/FLOW.md` — flujo normativo y reglas vigentes
- `docs/PIPELINE_FULL_EXAMPLE.md` — ejemplo numérico completo (direccional vs agregado)
- `docs/OUTPUT_CREATION_DETAILED_GUIDE.md` — guía paso a paso (entrada → salida contractual)

> Nota: el repositorio contiene scripts de ejecución en `scripts/` y el paquete principal en `src/kido_ruteo/`.

## 🏗️ Estructura del Proyecto

```text
kido-ruteo/
├── data/
│   ├── catalogs/         # Catálogos de referencia
│   │   └── sense_cardinality.csv
│   ├── raw/              # Datos originales
│   │   ├── queries/      # Datos de encuestas (checkpoint, general)
│   │   ├── zonification/ # Información geográfica (geojson)
│   │   ├── chkp2001.xlsx
│   │   ├── chkp2030.xlsm
│   │   ├── macrozones.csv
│   │   ├── ocupation_factor.csv
│   │   ├── valid_senses_special.csv
│   │   └── valid_senses_standard.csv
│   ├── interim/          # Datos intermedios procesados
│   ├── processed/        # Resultados finales
│   │   └── resultados_kido_automatizado.xlsx
│   └── external/         # Datos externos auxiliares
│
├── src/kido_ruteo/       # Paquete principal
│   ├── pipeline.py       # Orquestador maestro
│   ├── processing/       # Preprocesamiento, centroides, checkpoints
│   ├── routing/          # Grafo, shortest path (MC) y constrained path (MC2)
│   ├── capacity/         # Loader + matcher de capacidad
│   ├── congruence/       # Clasificación de congruencia
│   ├── trips/            # Cálculo vehicular (veh_*)
│   └── utils/            # Utilidades varias
│
├── scripts/              # Scripts ejecutables
│   ├── run_full_pipeline.py    # Ejecuta todas las queries (checkpoint + general)
│   ├── run_all_checkpoints.py  # Ejecuta solo checkpoint*.csv
│   ├── run_single_checkpoint.py# Ejemplo: un checkpoint fijo (editar paths/bbox)
│   └── debug_*.py              # Utilidades de depuración
│
├── tests/                # Tests unitarios
│   ├── test_strict_capacity.py
│   ├── test_strict_mode_v2.py
│   ├── test_strict_business_rules.py
│   └── ...
│
├── notebooks/            # Análisis exploratorio
│   └── exploracion.ipynb
│
├── README.md
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## 🚀 Instalación

### 1. Clonar repositorio

```bash
git clone https://github.com/MYS158/kido-ruteo.git
cd kido-ruteo
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install -e .
```

## 📊 Uso

### Pipeline completo (recomendado)

Ejecuta todas las queries encontradas en:

- `data/raw/queries/checkpoint/checkpoint*.csv`
- `data/raw/queries/general/*.csv`

```bash
python scripts/run_full_pipeline.py
```

### Solo checkpoints

```bash
python scripts/run_all_checkpoints.py
```

### Un solo checkpoint (ejemplo)

El script `scripts/run_single_checkpoint.py` está pensado como ejemplo (paths y `osm_bbox` están hardcodeados). Ajusta:

- `od_path`
- `zonification_path`
- `network_path`
- `capacity_path`
- `osm_bbox`

```bash
python scripts/run_single_checkpoint.py
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📚 Estructura de datos esperada

```text
data/raw/
├── queries/
│   ├── checkpoint/          # checkpointXXXX.csv
│   └── general/             # general.csv u otros
├── zonification/
│   └── zonification.geojson # incluye zonas (Core) y checkpoints (Checkpoint)
├── capacity/
│   └── summary_capacity.csv # capacidad por checkpoint/sentido
└── network/
    └── red.geojson          # opcional (si falta, se descarga de OSM)
```

La salida contractual se genera en `data/processed/` con prefijo `processed_`.

## 🤝 Contribución

1. Crear rama desde `main`
2. Seguir convenciones de código
3. Agregar tests para nuevas funcionalidades
4. Pull request con descripción detallada

## 📄 Licencia

//

---

**Versión**: 2.0.0  
**Última actualización**: Enero 2026
