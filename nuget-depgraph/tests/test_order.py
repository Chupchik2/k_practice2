"""Тесты порядка загрузки."""
import unittest
from pathlib import Path

from depgraph.graph import build_graph
from depgraph.order import load_order
from depgraph.testrepo import TestRepository

DATA = Path(__file__).parent / "data"


def order_of(name, root="A", depth=50):
    """Возвращает порядок загрузки как строку имён."""
    source = TestRepository.from_file(DATA / name)
    graph = build_graph(source, (root, ""), depth)
    return "".join(node[0] for node in load_order(graph)), graph


class LoadOrderTest(unittest.TestCase):
    """Порядок загрузки на разных тестовых репозиториях."""

    def test_diamond(self):
        """Ромб: общая зависимость D грузится один раз и первой."""
        self.assertEqual(order_of("simple.txt")[0], "DBCA")

    def test_larger_diamond(self):
        """Общая зависимость G раньше D и E, корень последний."""
        self.assertEqual(order_of("diamond.txt")[0], "GDEBFCA")

    def test_chain(self):
        """Цепочка грузится с конца."""
        self.assertEqual(order_of("chain.txt")[0], "EDCBA")

    def test_cycle(self):
        """Цикл не мешает: корень последний, все вершины по разу."""
        text, _ = order_of("cycle.txt")
        self.assertEqual(text, "DCBA")

    def test_depth_limit(self):
        """Порядок учитывает ограничение глубины."""
        self.assertEqual(order_of("chain.txt", depth=2)[0], "CBA")

    def test_dependencies_first(self):
        """В ациклическом графе зависимость идёт раньше зависимого."""
        text, graph = order_of("simple.txt")
        position = {name: i for i, name in enumerate(text)}
        for node, deps in graph.edges.items():
            for dep in deps:
                self.assertLess(position[dep[0]], position[node[0]])


if __name__ == "__main__":
    unittest.main()
