import hass
from mutex_graph import (
    edge_target,
    edge_name,
    find_cycle,
    format_graph,
    base_vertex,
    Deadlock,
    WrongUnlockOrder,
)
import json
import threading


class Lock:
    def __init__(self, mutex, name):
        self.mutex = mutex
        self.name = name

    def __enter__(self):
        # self.mutex.locker.log("lock {}.{}".format(self.mutex.name, self.name))
        self.mutex.locker.push_edge(self.mutex.name, self.name)
        self.mutex._lock.acquire()

    def __exit__(self, *args):
        # self.mutex.locker.log("unlock {}.{}".format(self.mutex.name, self.name))
        self.mutex._lock.release()
        self.mutex.locker.pop_edge(self.mutex.name, self.name)


class Mutex:
    def __init__(self, locker, name):
        self._lock = threading.Lock()
        self.locker = locker
        self.name = name

    def lock(self, name):
        return Lock(self, name)


class Locker(hass.Hass):
    def initialize(self):
        self.log("Init locker")
        self.enable_logging = self.args.get("enable_logging", False)
        self.current_graph = {}
        self.global_graph = {}
        self.current_stack = {}
        self.lock = threading.Lock()
        self.log("Inited locker")

    def get_mutex(self, name):
        return Mutex(self, name)

    def push_edge(self, mutex_name, lock_name):
        if not self.enable_logging:
            return
        with self.lock:
            stack = self.current_stack.setdefault(
                threading.current_thread().ident, [(base_vertex, "")]
            )
            last_mutex = edge_target(stack[-1])
            stack.append((mutex_name, lock_name))
            edge = (mutex_name, lock_name)
            self.global_graph.setdefault(last_mutex, set()).add(edge)
            self.current_graph.setdefault(last_mutex, set()).add(edge)
            if find_cycle(self.current_graph):
                raise Deadlock(format_graph(self.current_graph, "Deadlock"))

    def pop_edge(self, mutex_name, lock_name):
        if not self.enable_logging:
            return
        with self.lock:
            stack = self.current_stack.get(threading.current_thread().ident, None)
            if stack is None:
                raise WrongUnlockOrder()
            element = stack.pop()
            if edge_target(element) != mutex_name or edge_name(element) != lock_name:
                raise WrongUnlockOrder()
            self.current_graph[edge_target(stack[-1])].remove(element)

    def get_global_graph(self):
        import copy

        with self.lock:
            return copy.deepcopy(self.global_graph)
