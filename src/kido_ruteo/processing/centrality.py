import networkx as nx
import osmnx as ox

def build_network_graph(place_name: str = "Monterrey, Mexico", network_type: str = "drive") -> nx.Graph:
    """
    Descarga y construye el grafo de la red vial usando OSMnx.
    """
    try:
        G = ox.graph_from_place(place_name, network_type=network_type)
        
        # Añadir atributo 'pos' para compatibilidad con funciones posteriores
        for node, data in G.nodes(data=True):
            data['pos'] = (data['x'], data['y'])
            
        return G
    except Exception as e:
        print(f"Error al descargar el grafo: {e}")
        # Retornar un grafo vacío o manejar el error según corresponda
        return nx.Graph()
