class Deadlock(Exception):
    pass


class WrongUnlockOrder(Exception):
    pass


def edge_target(edge):
    return edge[0]


def edge_name(edge):
    return edge[1]


class DFS:
    def __init__(self, graph):
        self.graph = graph

    def _search(self, vertex):
        self.enter_index += 1
        self.enter[vertex] = self.enter_index
        for edge in self.graph.get(vertex, []):
            target = edge_target(edge)
            if target not in self.enter:
                self._search(target)
        self.exit_index += 1
        self.exit[vertex] = self.exit_index

    def search(self, starting_vertex):
        self.enter = {}
        self.exit = {}
        self.enter_index = 0
        self.exit_index = 0
        self._search(starting_vertex)


base_vertex = ""


def find_cycle(graph):
    search = DFS(graph)
    search.search(base_vertex)
    for vertex, edges in graph.items():
        for edge in edges:
            target = edge_target(edge)
            if (
                search.enter[target] <= search.enter[vertex]
                and search.exit[target] >= search.exit[vertex]
            ):
                return True
    return False


def format_graph(graph, name):
    result = ""
    for vertex, edges in graph.items():
        for edge in edges:
            result += '    "{}" -> "{}" [label="{}"]\n'.format(
                vertex, edge_target(edge), edge_name(edge)
            )
    return 'digraph "{}"{{\n{}}}\n'.format(name, result)


def _list_to_set(l):
    return set(tuple(e) for e in l)


def append_graph(graph, new):
    for vertex, new_edges in new.items():
        edges = graph.setdefault(vertex, set())
        if type(edges) is not set:
            edges = _list_to_set(edges)
            graph[vertex] = edges
        edges |= _list_to_set(new_edges)
