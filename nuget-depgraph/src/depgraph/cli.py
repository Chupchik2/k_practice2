"""Интерфейс командной строки."""
import argparse
import sys
from pathlib import Path

from depgraph.config import ConfigError, load_config
from depgraph.graph import build_graph, find_cycles, label
from depgraph.mermaid import to_mermaid
from depgraph.order import load_order
from depgraph.repository import RepositoryError
from depgraph.source import create_source, root_node
from depgraph.svg import render_svg

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def build_parser():
    """Создаёт разборщик аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Визуализация графа зависимостей пакетов NuGet.",
    )
    parser.add_argument(
        "--config", required=True, help="путь к конфигурационному JSON"
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="вывести параметры в формате ключ-значение (этап 1)",
    )
    parser.add_argument(
        "--direct-deps",
        action="store_true",
        help="вывести прямые зависимости пакета (этап 2)",
    )
    parser.add_argument(
        "--load-order",
        action="store_true",
        help="вывести порядок загрузки зависимостей (этап 4)",
    )
    return parser


def print_config(config):
    """Печатает параметры конфигурации в формате ключ-значение."""
    for key, value in config.as_pairs():
        print(f"{key}: {value}")


def print_direct(config, source):
    """Печатает прямые зависимости заданной версии пакета."""
    root = root_node(config)
    print(f"Прямые зависимости {label(root)}:")
    deps = source.dependencies(*root)
    for dep in deps:
        print(f"  {label(dep)}")
    if not deps:
        print("  (нет)")


def print_graph(graph, max_depth):
    """Печатает граф списком смежности и найденные циклы."""
    print(f"Граф зависимостей (глубина <= {max_depth}), "
          f"вершин: {len(graph.depth)}")
    for node in graph.nodes():
        deps = ", ".join(label(dep) for dep in graph.edges[node])
        print(f"  {label(node)} -> {deps or '(нет)'}")
    cycles = find_cycles(graph)
    if not cycles:
        print("Циклические зависимости: нет")
    for cycle in cycles:
        print("Цикл: " + " -> ".join(label(node) for node in cycle))


def print_order(graph):
    """Печатает порядок загрузки: сначала зависимости, в конце корень."""
    print("Порядок загрузки (зависимости раньше зависимых):")
    for number, node in enumerate(load_order(graph), start=1):
        print(f"  {number}. {label(node)}")


def save_outputs(graph, output_file):
    """Печатает Mermaid-описание и сохраняет .mmd и .svg файлы."""
    mermaid = to_mermaid(graph)
    print("Описание графа на языке Mermaid:")
    print(mermaid, end="")
    svg_path = Path(output_file)
    mmd_path = svg_path.with_suffix(".mmd")
    mmd_path.write_text(mermaid, encoding="utf-8")
    svg_path.write_text(render_svg(graph), encoding="utf-8")
    print(f"Mermaid сохранён: {mmd_path}")
    print(f"Изображение сохранено: {svg_path}")


def run(config, args):
    """Выполняет выбранные режимы работы."""
    if args.show_config:
        print_config(config)
    if args.direct_deps:
        print_direct(config, create_source(config))
    if args.show_config or args.direct_deps:
        return
    source = create_source(config)
    graph = build_graph(source, root_node(config), config.max_depth)
    if args.load_order:
        print_order(graph)
        return
    print_graph(graph, config.max_depth)
    save_outputs(graph, config.output_file)


def main(argv=None):
    """Запускает приложение и возвращает код завершения."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as err:
        print(f"Ошибка конфигурации: {err}", file=sys.stderr)
        return EXIT_USAGE
    try:
        run(config, args)
    except RepositoryError as err:
        print(f"Ошибка репозитория: {err}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as err:
        print(f"Ошибка записи файла: {err}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
