from __future__ import annotations
from typing import Any


class Deadlock(Exception):
    pass


class WrongUnlockOrder(Exception):
    pass


Edge = tuple[str, str]
Graph = dict[str, set[Edge]]


def edge_target(edge: Edge) -> str:
    return edge[0]


def edge_name(edge: Edge) -> str:
    return edge[1]


class DFS:
    def __init__(self, graph: Graph) -> None:
        self.graph: Graph = graph
        self.enter: dict[str, int] = {}
        self.exit: dict[str, int] = {}
        self.enter_index = 0
        self.exit_index = 0

    def _search(self, vertex: str) -> None:
        self.enter_index += 1
        self.enter[vertex] = self.enter_index
        for edge in self.graph.get(vertex, set()):
            target = edge_target(edge)
            if target not in self.enter:
                self._search(target)
        self.exit_index += 1
        self.exit[vertex] = self.exit_index

    def search(self, starting_vertex: str) -> None:
        self._search(starting_vertex)


base_vertex: str = ""


def find_cycle(graph: Graph) -> bool:
    search = DFS(graph)
    for vertex in graph:
        if vertex not in search.enter:
            search.search(vertex)
    for vertex, edges in graph.items():
        for edge in edges:
            target = edge_target(edge)
            if (
                search.enter[target] <= search.enter[vertex]
                and search.exit[target] >= search.exit[vertex]
            ):
                return True
    return False


def format_graph(graph: Graph, name: str) -> str:
    result = ""
    for vertex, edges in graph.items():
        for edge in edges:
            result += '    "{}" -> "{}" [label="{}"]\n'.format(
                vertex, edge_target(edge), edge_name(edge)
            )
    return 'digraph "{}"{{\n{}}}\n'.format(name, result)


def _list_to_set(l: list[Any] | set[Any]) -> set[Edge]:
    return set(tuple(e) for e in l)  # type: ignore[arg-type]


def append_graph(graph: dict[str, Any], new: Graph) -> None:
    for vertex, new_edges in new.items():
        edges: Any = graph.setdefault(vertex, set())
        if type(edges) is not set:
            edges = _list_to_set(edges)
            graph[vertex] = edges
        edges |= _list_to_set(new_edges)
