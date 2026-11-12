"""Тестовый репозиторий: граф из текстового файла.

Формат: по строке на пакет, ``A: B C`` — пакет A зависит от B и C.
Имена — заглавные латинские буквы. Пустые строки и строки,
начинающиеся с ``#``, игнорируются.
"""
import re
from pathlib import Path

from depgraph.repository import RepositoryError

NAME_RE = re.compile(r"^[A-Z]+$")


def _parse_line(number, line):
    """Разбирает строку 'A: B C' в пару (имя, [зависимости])."""
    head, sep, tail = line.partition(":")
    if not sep:
        raise RepositoryError(f"строка {number}: нет символа ':'")
    name = head.strip()
    deps = tail.split()
    for item in [name, *deps]:
        if not NAME_RE.match(item):
            raise RepositoryError(
                f"строка {number}: недопустимое имя пакета '{item}'"
            )
    return name, list(dict.fromkeys(deps))


def parse_text(text):
    """Разбирает текст описания и возвращает словарь имя -> зависимости."""
    packages = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, deps = _parse_line(number, line)
        if name in packages:
            raise RepositoryError(f"строка {number}: дубль пакета '{name}'")
        packages[name] = deps
    return packages


class TestRepository:
    """Источник зависимостей, читающий граф из файла."""

    __test__ = False

    def __init__(self, packages):
        """Создаёт репозиторий из словаря имя -> зависимости."""
        self.packages = packages

    @classmethod
    def from_file(cls, path):
        """Загружает репозиторий из файла."""
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as err:
            msg = f"не удалось прочитать '{path}': {err}"
            raise RepositoryError(msg) from err
        return cls(parse_text(text))

    def dependencies(self, name, version=""):
        """Возвращает зависимости как пары (имя, ''); версия игнорируется."""
        if name not in self.packages:
            raise RepositoryError(f"пакет '{name}' не описан в репозитории")
        return [(dep, "") for dep in self.packages[name]]
