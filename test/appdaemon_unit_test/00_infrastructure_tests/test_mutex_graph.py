import pytest
from typing import Any
from apps.mutex_graph import find_cycle, append_graph


@pytest.mark.parametrize("graph_dict, expected", [
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3')]}, False),
    ({'': {('a', 'e1'), ('b', 'e2')}, 'a': {('b', 'e3')}}, False),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5')]}, False),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('', 'e3')]}, True),
    ({'': {('a', 'e1'), ('b', 'e2')}, 'a': {('', 'e3')}}, True),
    ({'': [('a', 'e1'), ('b', 'e2')], 'b': [('', 'e3')]}, True),
    ({'': [('a', 'e1')], 'a': [('b', 'e2')], 'b': [('', 'e3')]}, True),
    ({'': [('a', 'e1'), ('b', 'e2')], 'a': [('b', 'e3'), ('c', 'e4')], 'c': [('b', 'e5'), ('a', 'e6')]}, True),
    ({'': [('a', 'e1')], 'a': [('a', 'e2')]}, True),
])
def test_find_cycle(graph_dict: dict[str, Any], expected: bool) -> None:
    assert find_cycle(graph_dict) == expected


@pytest.mark.parametrize("expected, g1, g2", [
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': {('a', 'e1'), ('b', 'e2')}},
     {'': {('a', 'e1'), ('b', 'e3')}}),
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': [('a', 'e1'), ('b', 'e2')]},
     {'': [('a', 'e1'), ('b', 'e3')]}),
    ({'': {('a', 'e1'), ('b', 'e2'), ('b', 'e3')}},
     {'': [['a', 'e1'], ['b', 'e2']]},
     {'': [['a', 'e1'], ['b', 'e3']]}),
    ({'': {('a', 'e1'), ('c', 'e3')}, 'a': {('b', 'e2')}, 'c': {('b', 'e4')}},
     {'': {('a', 'e1')}, 'a': {('b', 'e2')}},
     {'': {('c', 'e3')}, 'c': {('b', 'e4')}}),
])
def test_append_graph(expected: dict[str, Any], g1: dict[str, Any], g2: dict[str, Any]) -> None:
    append_graph(g1, g2)
    assert g1 == expected