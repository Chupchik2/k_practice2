"""Тесты генерации Mermaid и SVG."""
import unittest
import xml.etree.ElementTree as element_tree
from pathlib import Path

from depgraph.graph import DependencyGraph, build_graph
from depgraph.mermaid import to_mermaid
from depgraph.svg import render_svg
from depgraph.testrepo import TestRepository

DATA = Path(__file__).parent / "data"
SVG_NS = "{http://www.w3.org/2000/svg}"


def graph_of(name, depth=10):
    """Строит граф с корнем A по тестовому файлу."""
    source = TestRepository.from_file(DATA / name)
    return build_graph(source, ("A", ""), depth)


class MermaidTest(unittest.TestCase):
    """Текст Mermaid."""

    def test_simple(self):
        """Вершины и рёбра присутствуют."""
        text = to_mermaid(graph_of("simple.txt"))
        self.assertTrue(text.startswith("graph TD\n"))
        self.assertIn('n0["A"]', text)
        self.assertIn("n0 --> n1", text)
        self.assertIn("n2 --> n3", text)
        self.assertIn("style n0", text)

    def test_cycle_edge_dashed(self):
        """Ребро, замыкающее цикл, пунктирное."""
        text = to_mermaid(graph_of("cycle.txt"))
        self.assertIn("n2 -.-> n0", text)

    def test_version_in_label(self):
        """Версия попадает в подпись."""
        graph = DependencyGraph(root=("Lib", "1.0.0"))
        graph.depth[("Lib", "1.0.0")] = 0
        graph.edges[("Lib", "1.0.0")] = []
        self.assertIn('["Lib 1.0.0"]', to_mermaid(graph))


class SvgTest(unittest.TestCase):
    """SVG-изображение."""

    def parse(self, name):
        """Возвращает корень разобранного SVG для файла name."""
        return element_tree.fromstring(render_svg(graph_of(name)))

    def test_well_formed_counts(self):
        """SVG корректен; число прямоугольников и стрелок верное."""
        root = self.parse("simple.txt")
        rects = root.findall(f"{SVG_NS}rect")
        paths = [p for p in root.findall(f"{SVG_NS}path")]
        self.assertEqual(len(rects), 4 + 1)
        self.assertEqual(len(paths), 4)

    def test_cycle_and_selfloop(self):
        """Циклы и самозависимость рисуются без ошибок."""
        for name in ("cycle.txt", "selfloop.txt"):
            with self.subTest(name=name):
                root = self.parse(name)
                self.assertIn("dasharray", element_tree.tostring(root).decode())

    def test_single_node(self):
        """Граф из одной вершины."""
        source = TestRepository({"A": []})
        graph = build_graph(source, ("A", ""), 3)
        root = element_tree.fromstring(render_svg(graph))
        self.assertEqual(len(root.findall(f"{SVG_NS}rect")), 2)


if __name__ == "__main__":
    unittest.main()
