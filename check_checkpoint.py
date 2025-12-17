from src.kido_ruteo.routing.graph_loader import load_graph_from_geojson
from src.kido_ruteo.processing.checkpoint_loader import get_checkpoint_node_mapping

G = load_graph_from_geojson('data/raw/red.geojson')
checkpoint_nodes = get_checkpoint_node_mapping('data/raw/zonification/zonification.geojson', G)

print("Mapeo de checkpoints a nodos:")
print(checkpoint_nodes)

# Buscar el checkpoint 2002 específicamente
cp_2002 = checkpoint_nodes[checkpoint_nodes['checkpoint_id'] == 2002]
print(f"\nCheckpoint 2002:")
print(cp_2002)

# Ver el nodo asignado
if len(cp_2002) > 0:
    node_id = cp_2002.iloc[0]['checkpoint_node_id']
    print(f"\nNodo asignado: {node_id}")
    if node_id in G.nodes():
        print(f"Atributos del nodo: {G.nodes[node_id]}")
