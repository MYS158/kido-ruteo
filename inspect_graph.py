from src.kido_ruteo.routing.graph_loader import load_graph_from_geojson

G = load_graph_from_geojson('data/raw/red.geojson')
sample_nodes = list(G.nodes(data=True))[:5]

print(f'Total nodos: {G.number_of_nodes()}')
print('\nMuestra de 5 nodos:')
for node_id, attrs in sample_nodes:
    print(f'  ID={node_id}')
    print(f'  Tipo ID: {type(node_id)}')
    print(f'  Attrs: {attrs}')
    print()
