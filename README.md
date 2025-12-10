# KIDO-Ruteo

**Sistema de procesamiento de datos Origen-Destino para análisis de movilidad urbana**

## 📋 Descripción

KIDO-Ruteo es un pipeline de procesamiento de datos de movilidad que permite:
- Ingestar datos de matrices Origen-Destino (OD)
- Procesar información geográfica de zonas
- Construir rutas óptimas entre pares OD
- Evaluar congruencia de viajes mediante métricas E1 y E2

## 🏗️ Estructura del Proyecto

```
kido-ruteo/
├── data/                    # Datos del proyecto (no versionados)
│   ├── raw/                 # Datos originales sin procesar
│   ├── interim/             # Datos intermedios procesados
│   ├── processed/           # Datos finales listos para análisis
│   └── external/            # Datos de fuentes externas
│
├── notebooks/               # Jupyter notebooks para análisis exploratorio
│
├── scripts/                 # Scripts ejecutables del pipeline
│   ├── ingest_data.py       # Ingesta de datos desde fuentes
│   ├── preprocess_data.py   # Preprocesamiento y limpieza
│   ├── build_routes.py      # Construcción de rutas OD
│   ├── evaluate_congruence.py # Evaluación de métricas
│   └── utils/
│       └── geo_utils.py     # Utilidades geográficas
│
├── src/                     # Código fuente del paquete
│   └── kido_ruteo/
│       ├── io.py            # Lectura/escritura de datos
│       ├── preprocessing.py # Preprocesamiento de datos
│       ├── routing.py       # Algoritmos de ruteo
│       ├── congruence.py    # Cálculo de métricas de congruencia
│       └── models/          # Modelos de datos
│           ├── od_matrix.py # Representación de matrices OD
│           └── zoning.py    # Modelado de zonas geográficas
│
├── tests/                   # Tests unitarios
│   ├── test_io.py
│   ├── test_preprocessing.py
│   ├── test_routing.py
│   └── test_congruence.py
│
├── .gitignore
├── README.md
├── pyproject.toml          # Configuración del proyecto
└── requirements.txt        # Dependencias Python
```

## 🚀 Instalación

### Prerrequisitos
- Python 3.10 o superior
- pip o conda

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/MYS158/kido-ruteo.git
cd kido-ruteo
```

2. **Crear entorno virtual**
```bash
python -m venv venv
```

3. **Activar entorno virtual**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

5. **Instalar el paquete en modo desarrollo**
```bash
pip install -e .
```

## 📊 Uso

### 1. Ingesta de datos

Coloca los datos fuente en las rutas esperadas:
- `data/raw/kido-data2/Consultas/General/*.csv`
- `data/raw/kido-data2/Consultas/Checkpoint/*.csv`
- `data/raw/kido-data2/Geojson/*.geojson`
- `data/raw/kido-data2/Zoning/*.qmd`

Ejecuta la ingesta:
```bash
python scripts/ingest_data.py
```

### 2. Preprocesamiento

Normaliza y valida los datos:
```bash
python scripts/preprocess_data.py
```

### 3. Construcción de rutas

Genera rutas entre pares OD:
```bash
python scripts/build_routes.py
```

### 4. Evaluación de congruencia

Calcula métricas E1 y E2:
```bash
python scripts/evaluate_congruence.py
```

## 🧪 Testing

Ejecutar todos los tests:
```bash
pytest tests/
```

Ejecutar tests con cobertura:
```bash
pytest --cov=src/kido_ruteo tests/
```

## 📚 Documentación

### Fuentes de datos

Las fuentes de datos oficiales del proyecto KIDO incluyen:
- **Consultas Generales**: Matrices OD agregadas
- **Consultas Checkpoint**: Puntos de verificación de rutas
- **Geojson**: Geometrías de zonas de análisis
- **Zoning**: Metadatos de zonificación (formato QMD)

### Métricas de congruencia

- **E1**: Congruencia de rutas respecto a centroides zonales
- **E2**: Congruencia de distribución de flujos

## 🛠️ Desarrollo

### Estructura de commits

Seguimos Conventional Commits:
- `feat:` Nueva funcionalidad
- `fix:` Corrección de bugs
- `docs:` Cambios en documentación
- `test:` Añadir o modificar tests
- `refactor:` Refactorización de código
- `chore:` Tareas de mantenimiento

### Limpieza de ramas

Para limpiar ramas obsoletas:
```bash
bash scripts/clean_branches.sh
```

## 📄 Licencia

MIT License - Ver archivo LICENSE para más detalles

## 👥 Equipo

Proyecto KIDO - Análisis de Movilidad Urbana

---

**Versión**: 0.1.0  
**Última actualización**: Diciembre 2024
