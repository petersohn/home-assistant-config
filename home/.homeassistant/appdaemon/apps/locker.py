from __future__ import annotations
from copy import deepcopy
from typing import Any
import hass
import json
import threading
from mutex_graph import (
    Deadlock,
    Edge,
    Graph,
    WrongUnlockOrder,
    base_vertex,
    edge_name,
    edge_target,
    find_cycle,
    format_graph,
)


class Lock:
    def __init__(self, mutex: Mutex, name: str) -> None:
        self.mutex = mutex
        self.name = name

    def __enter__(self) -> None:
        # self.mutex.locker.log("lock {}.{}".format(self.mutex.name, self.name))
        self.mutex.locker.push_edge(self.mutex.name, self.name)
        self.mutex._lock.acquire()

    def __exit__(self, *args: Any) -> None:
        # self.mutex.locker.log("unlock {}.{}".format(self.mutex.name, self.name))
        self.mutex._lock.release()
        self.mutex.locker.pop_edge(self.mutex.name, self.name)


class Mutex:
    def __init__(self, locker: Locker, name: str) -> None:
        self._lock: threading.Lock = threading.Lock()
        self.locker = locker
        self.name = name

    def lock(self, name: str) -> Lock:
        return Lock(self, name)


class Locker(hass.Hass):
    def initialize(self) -> None:
        self.enable_logging: bool = self.args.get("enable_logging", False)
        self.current_graph: dict[str, Any] = {}
        self.global_graph: Graph = {}
        self.current_stack: dict[int, list[Edge]] = {}
        self._graph_lock: threading.Lock = threading.Lock()

    def get_mutex(self, name: str) -> Mutex:
        return Mutex(self, name)

    def push_edge(self, mutex_name: str, lock_name: str) -> None:
        if not self.enable_logging:
            return
        with self._graph_lock:
            stack = self.current_stack.setdefault(
                threading.current_thread().ident or 0, [(base_vertex, "")]
            )
            last_mutex = edge_target(stack[-1])
            stack.append((mutex_name, lock_name))
            edge: Edge = (mutex_name, lock_name)
            self.global_graph.setdefault(last_mutex, set()).add(edge)
            self.current_graph.setdefault(last_mutex, set()).add(edge)
            if find_cycle(self.current_graph):
                raise Deadlock(format_graph(self.current_graph, "Deadlock"))

    def pop_edge(self, mutex_name: str, lock_name: str) -> None:
        if not self.enable_logging:
            return
        with self._graph_lock:
            stack = self.current_stack.get(
                threading.current_thread().ident or 0, None
            )
            if stack is None:
                raise WrongUnlockOrder()
            element = stack.pop()
            if (
                edge_target(element) != mutex_name
                or edge_name(element) != lock_name
            ):
                raise WrongUnlockOrder()
            self.current_graph[edge_target(stack[-1])].discard(element)

    def get_global_graph(self) -> Graph:
        with self._graph_lock:
            return deepcopy(self.global_graph)
