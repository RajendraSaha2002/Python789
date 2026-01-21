import heapq

def dijkstra(Graph, start):
    distances = {vertex: float('inf') for vertex in Graph}
    distances[start] = 0
    queue = [(0, start)]
    while queue:
        curr_distance, curr_vertex = heapq.heappop(queue)
        for neighbor, weight in Graph[curr_vertex].items():
            distance = curr_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(queue, (distance, neighbor))
    return distances

graph = {
    'A': {'B': 1, 'C': 4},
    'B': {'A': 1, 'C': 2, 'D': 5},
    'C': {'A': 4, 'B': 2, 'D': 1},
    'D': {'B': 5, 'C': 1}
}
print(dijkstra(graph, 'A'))