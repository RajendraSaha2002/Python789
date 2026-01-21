import networkx as nx

G = nx.Graph()
G.add_weighted_edges_from([
    (0, 1, 4),
    (0, 2, 3),
    (1, 2, 1),
    (1, 3, 2),
    (2, 3, 4),
    (3, 4, 2),
    (4, 5, 6)
])

mst = nx.minimum_spanning_tree(G)
print("Edges in MST:", list(mst.edges(data=True)))