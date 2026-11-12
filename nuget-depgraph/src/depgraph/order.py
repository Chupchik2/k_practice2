"""Порядок загрузки зависимостей: зависимости раньше зависимых."""


def load_order(graph):
    """Возвращает вершины в порядке загрузки (топологический порядок).

    Итеративный обход в глубину с выдачей вершины после всех её
    зависимостей. Рёбра, ведущие в вершину, обход которой ещё не
    завершён (цикл), пропускаются, поэтому порядок определён и для
    графов с циклами. Корневой пакет всегда последний.
    """
    seen = {graph.root}
    order = []
    path = [graph.root]
    stack = [iter(graph.edges.get(graph.root, []))]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            order.append(path.pop())
            stack.pop()
        elif child not in seen:
            seen.add(child)
            path.append(child)
            stack.append(iter(graph.edges.get(child, [])))
    return order
