"""Граф зависимостей: построение обходом в ширину и поиск циклов."""
from collections import deque
from dataclasses import dataclass, field

VISITING = "visiting"
DONE = "done"


def label(node):
    """Возвращает подпись вершины: 'имя версия' или просто 'имя'."""
    name, version = node
    return f"{name} {version}" if version else name


@dataclass
class DependencyGraph:
    """Граф: вершины — пары (имя, версия), рёбра — прямые зависимости."""

    root: tuple
    edges: dict = field(default_factory=dict)
    depth: dict = field(default_factory=dict)

    def nodes(self):
        """Возвращает вершины в порядке обнаружения (по уровням BFS)."""
        return list(self.depth)


def build_graph(source, root, max_depth):
    """Строит граф зависимостей обходом в ширину без рекурсии.

    Вершины на глубине max_depth включаются в граф, но не раскрываются.
    Уже посещённые вершины повторно не обходятся, поэтому циклы
    не приводят к зацикливанию.
    """
    graph = DependencyGraph(root=root)
    graph.depth[root] = 0
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if graph.depth[node] >= max_depth:
            graph.edges[node] = []
            continue
        children = list(dict.fromkeys(source.dependencies(*node)))
        graph.edges[node] = children
        for child in children:
            if child not in graph.depth:
                graph.depth[child] = graph.depth[node] + 1
                queue.append(child)
    return graph


def _walk_cycles(graph):
    """Итеративный DFS; возвращает список найденных циклов."""
    state = {graph.root: VISITING}
    path = [graph.root]
    stack = [iter(graph.edges.get(graph.root, []))]
    cycles = []
    while stack:
        descended = False
        for child in stack[-1]:
            if state.get(child) == VISITING:
                cycles.append(path[path.index(child):] + [child])
            elif child not in state:
                state[child] = VISITING
                path.append(child)
                stack.append(iter(graph.edges.get(child, [])))
                descended = True
                break
        if not descended:
            state[path.pop()] = DONE
            stack.pop()
    return cycles


def find_cycles(graph):
    """Возвращает циклы вида [v, ..., u, v]; пусто, если циклов нет."""
    return _walk_cycles(graph)


def back_edges(cycles):
    """Возвращает множество рёбер, замыкающих найденные циклы."""
    return {(cycle[-2], cycle[-1]) for cycle in cycles}
