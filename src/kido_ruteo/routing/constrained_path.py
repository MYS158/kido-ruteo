"""
Módulo para cálculo de Constrained Shortest Path (MC2).
"""

import networkx as nx
import pandas as pd
import math
from typing import List, Tuple, Optional
from tqdm import tqdm

def calculate_bearing(G, u, v):
    """Calculates bearing from node u to node v in degrees (0=N, 90=E)."""
    try:
        x1, y1 = G.nodes[u]['x'], G.nodes[u]['y']
        x2, y2 = G.nodes[v]['x'], G.nodes[v]['y']
        dx = x2 - x1
        dy = y2 - y1
        angle = math.degrees(math.atan2(dx, dy))
        if angle < 0:
            angle += 360
        return angle
    except KeyError:
        return None

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
    STRICT MODE: Deriva el código de sentido (ej. '1-3') desde la GEOMETRÍA.
    
    El sentido SIEMPRE se calcula geométricamente a partir de la ruta:
    Origen → Checkpoint → Destino
    
    Usando bearings en el nodo del checkpoint:
    - Cardinalidad fija: 1=Norte, 2=Este, 3=Sur, 4=Oeste
    - Formato: "X-Y" donde X=origen, Y=destino
    - Ej: "4-2" = Viene del Oeste, va al Este
    
    NUNCA se lee del input. NUNCA se asume. SOLO se deriva.
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
    dest_node_col: str = 'destination_node_id'
) -> pd.DataFrame:
    """
    STRICT MODE: Calcula MC2 (ruta mínima obligada por checkpoint) y DERIVA EL SENTIDO.
    
    REGLA 2: El sentido SOLO se deriva de MC2.
    - Nunca se lee del input
    - Nunca se infiere de otra fuente
    - Si no hay ruta MC2 válida → sense_code = None
    
    Esta es la ÚNICA función que crea sense_code.
    """
    print("  Calculando matriz MC2 (Constrained Path) y Sentido...")
    
    dist_mc2 = []
    derived_senses = []
    
    for idx, row in tqdm(df_od.iterrows(), total=len(df_od)):
        origin = row.get(origin_node_col)
        dest = row.get(dest_node_col)
        checkpoint = row.get(checkpoint_col)
        
        if pd.isna(origin) or pd.isna(dest) or pd.isna(checkpoint):
            dist_mc2.append(None)
            derived_senses.append(None)
            continue
            
        checkpoint = str(checkpoint)
        
        path, dist = compute_constrained_shortest_path(G, origin, dest, checkpoint)
        
        dist_mc2.append(dist)
        
        # Derive Sense
        sense = None
        if path:
            sense = derive_sense_from_path(G, path, checkpoint)
        derived_senses.append(sense)
        
    df_od['mc2_distance_m'] = dist_mc2
    df_od['sense_code'] = derived_senses # Overwrite or create sense_code
        
    return df_od
