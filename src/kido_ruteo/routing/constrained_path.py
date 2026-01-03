"""kido_ruteo.routing.constrained_path

STRICT MODE (docs/flow.md):
- Calcula MC2 (camino mínimo obligado por checkpoint).
- Deriva `sense_code` EXCLUSIVAMENTE desde la geometría de MC2 en el checkpoint.
- Valida el `sense_code` contra el catálogo `sense_cardinality.csv`.

No existe lectura de sentido desde OD, ni fallbacks, ni promedios.
"""

import networkx as nx
import pandas as pd
import math
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from tqdm import tqdm


def _default_sense_catalog_path() -> Path:
    # repo_root/.../src/kido_ruteo/routing/constrained_path.py -> parents[3] == repo root
    return Path(__file__).resolve().parents[3] / 'data' / 'catalogs' / 'sense_cardinality.csv'


def _load_valid_sense_codes(catalog_path: Optional[str] = None) -> set[str]:
    """Carga el catálogo de sentidos válidos.

    El flujo oficial exige lookup explícito en sense_cardinality.csv.
    Si el archivo no existe o es inválido, se debe fallar (no hay fallback).
    """
    path = Path(catalog_path) if catalog_path else _default_sense_catalog_path()
    if not path.exists():
        raise FileNotFoundError(f"sense_cardinality.csv no encontrado en: {path}")

    df = pd.read_csv(path)
    if 'sentido' not in df.columns:
        raise ValueError("sense_cardinality.csv debe contener columna 'sentido'")

    valid = (
        df['sentido']
        .astype(str)
        .str.strip()
        .replace({'nan': np.nan, 'None': np.nan})
        .dropna()
        .tolist()
    )
    return set(valid)

def calculate_bearing(G, u, v):
    """Calculates bearing from node u to node v in degrees (0=N, 90=E)."""
    def _xy(n):
        data = G.nodes.get(n, {})
        if 'x' in data and 'y' in data:
            return data['x'], data['y']
        p = data.get('pos')
        if isinstance(p, (tuple, list)) and len(p) == 2:
            return p[0], p[1]
        return None

    p1 = _xy(u)
    p2 = _xy(v)
    if p1 is None or p2 is None:
        return None

    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    angle = math.degrees(math.atan2(dx, dy))
    if angle < 0:
        angle += 360
    return angle

def get_cardinality(bearing, is_origin=False):
    """Maps bearing to cardinality code (1=N, 2=E, 3=S, 4=W)."""
    if bearing is None: return None
    
    # Sectors: N(315-45), E(45-135), S(135-225), W(225-315)
    if bearing >= 315 or bearing < 45:
        card = 1 # North
    elif bearing >= 45 and bearing < 135:
        card = 2 # East
    elif bearing >= 135 and bearing < 225:
        card = 3 # South
    else:
        card = 4 # West
        
    if is_origin:
        # Origin is opposite to incoming direction
        # If I head North (1), I come from South (3)
        # If I head East (2), I come from West (4)
        # If I head South (3), I come from North (1)
        # If I head West (4), I come from East (2)
        map_opp = {1: 3, 2: 4, 3: 1, 4: 2}
        return map_opp[card]
    else:
        return card

def derive_sense_from_path(G: nx.Graph, path: List[str], checkpoint_node: str) -> Optional[str]:
    """
    STRICT MODE: Deriva el `sense_code` desde la geometría de MC2.

    NOTA: El lookup contra `sense_cardinality.csv` ocurre fuera de esta función.
    Esta función solo produce el candidato geométrico (ej: '4-2').
    """
    if not path or len(path) < 3:
        return None
        
    try:
        idx = path.index(checkpoint_node)
    except ValueError:
        return None
        
    if idx == 0 or idx == len(path) - 1:
        return None # Checkpoint is start or end, cannot determine flow through
        
    u = path[idx - 1] # Previous node
    v = checkpoint_node
    w = path[idx + 1] # Next node
    
    # Incoming Bearing (u -> v)
    bearing_in = calculate_bearing(G, u, v)
    # Outgoing Bearing (v -> w)
    bearing_out = calculate_bearing(G, v, w)
    
    # Origin Cardinality (From where did I come?)
    # Derived from Incoming Bearing
    origin_card = get_cardinality(bearing_in, is_origin=True)
    
    # Destination Cardinality (To where am I going?)
    # Derived from Outgoing Bearing
    dest_card = get_cardinality(bearing_out, is_origin=False)
    
    if origin_card and dest_card:
        # STRICT: sentidos iguales (ej. 4-4, 1-1) se consideran inválidos/indeterminados
        # y deben mapearse a '0'.
        if origin_card == dest_card:
            return '0'
        return f"{origin_card}-{dest_card}"
    return None

def compute_constrained_shortest_path(
    G: nx.Graph,
    origin_node: str,
    dest_node: str,
    checkpoint_node: str
) -> Tuple[Optional[List[str]], Optional[float]]:
    """
    Calcula shortest path que DEBE pasar por un checkpoint específico.
    """
    try:
        # Ruta origen -> checkpoint
        path1 = nx.shortest_path(G, source=origin_node, target=checkpoint_node, weight='weight')
        dist1 = nx.shortest_path_length(G, source=origin_node, target=checkpoint_node, weight='weight')
        
        # Ruta checkpoint -> destino
        path2 = nx.shortest_path(G, source=checkpoint_node, target=dest_node, weight='weight')
        dist2 = nx.shortest_path_length(G, source=checkpoint_node, target=dest_node, weight='weight')
        
        # Combinar rutas (evitar duplicar checkpoint)
        combined_path = path1 + path2[1:]
        combined_distance = dist1 + dist2
        
        return combined_path, combined_distance
    
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, None

def compute_mc2_matrix(
    df_od: pd.DataFrame,
    G: nx.Graph,
    checkpoint_col: str = 'checkpoint_id',
    origin_node_col: str = 'origin_node_id',
    dest_node_col: str = 'destination_node_id',
    sense_catalog_path: Optional[str] = None
) -> pd.DataFrame:
    """
    STRICT MODE (docs/flow.md):
    - Calcula MC2 (ruta mínima obligada por checkpoint)
    - Deriva sentido geométricamente en el checkpoint
    - Mapea bearings a cardinalidad
    - Hace lookup en `sense_cardinality.csv`

    Si no hay ruta MC2 válida o no se puede derivar/validar el sentido → `sense_code = NaN`.
    """
    print("  Calculando matriz MC2 (Constrained Path) y Sentido...")

    valid_sense_codes = _load_valid_sense_codes(sense_catalog_path)
    
    dist_mc2 = []
    derived_senses = []
    
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od)):
        origin = row.get(origin_node_col)
        dest = row.get(dest_node_col)
        checkpoint = row.get(checkpoint_col)
        
        if pd.isna(origin) or pd.isna(dest) or pd.isna(checkpoint):
            dist_mc2.append(None)
            derived_senses.append(np.nan)
            continue
            
        checkpoint = str(checkpoint)
        
        path, dist = compute_constrained_shortest_path(G, origin, dest, checkpoint)
        
        dist_mc2.append(dist)

        # Derivar + validar sentido (lookup obligatorio)
        sense_candidate = None
        if path:
            sense_candidate = derive_sense_from_path(G, path, checkpoint)

        if sense_candidate == '0':
            # '0' es el código de sentido agregado/indeterminado.
            derived_senses.append('0')
        elif sense_candidate and (sense_candidate in valid_sense_codes) and (sense_candidate != '0'):
            derived_senses.append(sense_candidate)
        else:
            derived_senses.append(np.nan)
        
    df_od['mc2_distance_m'] = dist_mc2
    # Overwrite/create sense_code (STRICT: only here, derived from MC2)
    df_od['sense_code'] = derived_senses
        
    return df_od
