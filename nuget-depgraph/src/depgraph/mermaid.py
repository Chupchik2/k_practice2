"""Текстовое представление графа на языке диаграмм Mermaid."""
from depgraph.graph import back_edges, find_cycles, label

ROOT_STYLE = "fill:#ffe9a8,stroke:#b8860b,stroke-width:2px"


def _escape(text):
    """Экранирует символы, недопустимые в подписи Mermaid."""
    return text.replace('"', "#quot;")


def to_mermaid(graph):
    """Возвращает описание графа в формате Mermaid (flowchart, сверху вниз).

    Рёбра, замыкающие циклы, рисуются пунктиром.
    """
    ids = {node: f"n{index}" for index, node in enumerate(graph.nodes())}
    loops = back_edges(find_cycles(graph))
    lines = ["graph TD"]
    for node, node_id in ids.items():
        lines.append(f'    {node_id}["{_escape(label(node))}"]')
    for node in graph.nodes():
        for dep in graph.edges[node]:
            arrow = "-.->" if (node, dep) in loops else "-->"
            lines.append(f"    {ids[node]} {arrow} {ids[dep]}")
    lines.append(f"    style {ids[graph.root]} {ROOT_STYLE}")
    return "\n".join(lines) + "\n"
