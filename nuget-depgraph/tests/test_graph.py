"""Тесты построения графа, глубины и циклов."""
import unittest
from pathlib import Path

from depgraph.graph import back_edges, build_graph, find_cycles, label
from depgraph.repository import RepositoryError
from depgraph.testrepo import TestRepository, parse_text

DATA = Path(__file__).parent / "data"


def graph_of(name, root, depth):
    """Строит граф по тестовому файлу."""
    source = TestRepository.from_file(DATA / name)
    return build_graph(source, (root, ""), depth)


def names(nodes):
    """Преобразует вершины в список имён."""
    return [node[0] for node in nodes]


class ParseTest(unittest.TestCase):
    """Разбор файла тестового репозитория."""

    def test_parse(self):
        """Комментарии и пустые строки пропускаются."""
        self.assertEqual(parse_text("# c\n\nA: B B\nB:\n"),
                         {"A": ["B"], "B": []})

    def test_errors(self):
        """Некорректные описания дают RepositoryError."""
        for text in ("A B", "a: B", "A: b", "A: B\nA: C"):
            with self.subTest(text=text):
                with self.assertRaises(RepositoryError):
                    parse_text(text)

    def test_missing_file_and_package(self):
        """Нет файла или нет корневого пакета — RepositoryError."""
        with self.assertRaises(RepositoryError):
            TestRepository.from_file(DATA / "absent.txt")
        with self.assertRaises(RepositoryError):
            graph_of("simple.txt", "Q", 3)


class BuildGraphTest(unittest.TestCase):
    """Построение графа обходом в ширину."""

    def test_bfs_order_and_depth(self):
        """Вершины перечисляются по уровням."""
        graph = graph_of("simple.txt", "A", 5)
        self.assertEqual(names(graph.nodes()), ["A", "B", "C", "D"])
        self.assertEqual(graph.depth[("D", "")], 2)
        self.assertEqual(names(graph.edges[("A", "")]), ["B", "C"])

    def test_depth_limit(self):
        """Глубина ограничивает обход цепочки."""
        graph = graph_of("chain.txt", "A", 2)
        self.assertEqual(names(graph.nodes()), ["A", "B", "C"])
        self.assertEqual(graph.edges[("C", "")], [])
        full = graph_of("chain.txt", "A", 10)
        self.assertEqual(len(full.nodes()), 5)

    def test_depth_one(self):
        """Глубина 1 даёт только прямые зависимости."""
        graph = graph_of("simple.txt", "A", 1)
        self.assertEqual(names(graph.nodes()), ["A", "B", "C"])

    def test_undefined_dependency(self):
        """Зависимость от неописанного пакета — ошибка репозитория."""
        with self.assertRaises(RepositoryError):
            graph_of("undefined.txt", "A", 3)

    def test_label(self):
        """Подпись с версией и без."""
        self.assertEqual(label(("A", "")), "A")
        self.assertEqual(label(("Lib", "1.0.0")), "Lib 1.0.0")


class CycleTest(unittest.TestCase):
    """Циклические зависимости."""

    def test_no_cycles(self):
        """В ациклическом графе циклов нет."""
        self.assertEqual(find_cycles(graph_of("simple.txt", "A", 5)), [])

    def test_cycle_terminates(self):
        """Цикл A-B-C-A: обход завершается, цикл найден."""
        graph = graph_of("cycle.txt", "A", 50)
        self.assertEqual(len(graph.nodes()), 4)
        cycles = find_cycles(graph)
        self.assertEqual([names(c) for c in cycles],
                         [["A", "B", "C", "A"]])
        self.assertEqual(back_edges(cycles), {(("C", ""), ("A", ""))})

    def test_self_loop(self):
        """Самозависимость и взаимная зависимость."""
        graph = graph_of("selfloop.txt", "A", 50)
        found = [names(c) for c in find_cycles(graph)]
        self.assertIn(["A", "A"], found)
        self.assertIn(["A", "B", "A"], found)


if __name__ == "__main__":
    unittest.main()
