"""Рисование графа зависимостей в формате SVG без внешних библиотек."""
from xml.sax.saxutils import escape

from depgraph.graph import back_edges, find_cycles, label

BOX_H = 34
CHAR_W = 8
PAD_X = 14
GAP_X = 30
GAP_Y = 64
MARGIN = 30
LOOP_STEP = 26
FILL = "#e8f0fe"
FILL_ROOT = "#ffe9a8"
STROKE = "#34495e"
BACK_COLOR = "#c0392b"


def _layers(graph):
    """Группирует вершины по глубине: список списков."""
    layers = {}
    for node in graph.nodes():
        layers.setdefault(graph.depth[node], []).append(node)
    return [layers[depth] for depth in sorted(layers)]


def _width(node):
    """Возвращает ширину прямоугольника вершины."""
    return len(label(node)) * CHAR_W + 2 * PAD_X


def _positions(layers):
    """Вычисляет для каждой вершины (x, y, ширина) и ширину холста."""
    rows = [sum(_width(n) for n in row) + GAP_X * (len(row) - 1)
            for row in layers]
    total = max(rows)
    pos = {}
    for level, row in enumerate(layers):
        x = MARGIN + (total - rows[level]) / 2
        y = MARGIN + level * (BOX_H + GAP_Y)
        for node in row:
            pos[node] = (x, y, _width(node))
            x += _width(node) + GAP_X
    return pos, total + 2 * MARGIN


def _node_svg(node, geom, is_root):
    """Возвращает SVG-фрагмент вершины."""
    x, y, width = geom
    fill = FILL_ROOT if is_root else FILL
    text = escape(label(node))
    return (
        f'<rect x="{x:.1f}" y="{y}" width="{width}" height="{BOX_H}" '
        f'rx="6" fill="{fill}" stroke="{STROKE}"/>'
        f'<text x="{x + width / 2:.1f}" y="{y + BOX_H / 2 + 5}" '
        f'text-anchor="middle">{text}</text>'
    )


def _down_edge(src, dst):
    """Путь ребра вниз, на следующий уровень."""
    x1, y1 = src[0] + src[2] / 2, src[1] + BOX_H
    x2, y2 = dst[0] + dst[2] / 2, dst[1]
    mid = (y2 - y1) / 2
    return (f"M{x1:.1f},{y1} C{x1:.1f},{y1 + mid} "
            f"{x2:.1f},{y2 - mid} {x2:.1f},{y2}")


def _side_edge(src, dst, bulge):
    """Путь ребра вверх, в тот же уровень или в петлю (справа)."""
    x1, y1 = src[0] + src[2] / 2, src[1] + BOX_H / 3
    x2, y2 = dst[0] + dst[2] / 2, dst[1] + 2 * BOX_H / 3
    out = max(x1, x2) + bulge
    return (f"M{x1:.1f},{y1:.1f} C{out:.1f},{y1 - BOX_H:.1f} "
            f"{out:.1f},{y2 + BOX_H:.1f} {x2:.1f},{y2:.1f}")


def _edges_svg(graph, pos, loops):
    """Возвращает SVG-фрагменты всех рёбер и число боковых петель."""
    parts = []
    side = 0
    for node in graph.nodes():
        for dep in graph.edges[node]:
            back = (node, dep) in loops
            if graph.depth[dep] > graph.depth[node]:
                path = _down_edge(pos[node], pos[dep])
            else:
                side += 1
                path = _side_edge(pos[node], pos[dep], LOOP_STEP * side)
            color, marker = (BACK_COLOR, "arrow-back") if back else (
                STROKE, "arrow")
            dash = ' stroke-dasharray="6 4"' if back else ""
            parts.append(
                f'<path d="{path}" fill="none" stroke="{color}"{dash} '
                f'marker-end="url(#{marker})"/>'
            )
    return parts, side


def _defs():
    """Возвращает определения стрелок."""
    def marker(name, color):
        """Стрелка заданного цвета."""
        return (
            f'<marker id="{name}" markerWidth="10" markerHeight="8" '
            f'refX="9" refY="4" orient="auto">'
            f'<path d="M0,0 L10,4 L0,8 z" fill="{color}"/></marker>'
        )
    return "<defs>" + marker("arrow", STROKE) + marker(
        "arrow-back", BACK_COLOR) + "</defs>"


def render_svg(graph):
    """Возвращает текст SVG-изображения графа зависимостей."""
    pos, width = _positions(_layers(graph))
    loops = back_edges(find_cycles(graph))
    edges, side = _edges_svg(graph, pos, loops)
    width += LOOP_STEP * (side + 1)
    height = MARGIN * 2 + len(_layers(graph)) * (BOX_H + GAP_Y) - GAP_Y
    nodes = [_node_svg(n, pos[n], n == graph.root) for n in graph.nodes()]
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height}" viewBox="0 0 {width:.0f} {height}" '
        f'font-family="Arial, sans-serif" font-size="14">'
    )
    body = [f"<title>Граф зависимостей {escape(label(graph.root))}</title>",
            _defs(), '<rect width="100%" height="100%" fill="white"/>']
    return head + "".join(body + edges + nodes) + "</svg>\n"
