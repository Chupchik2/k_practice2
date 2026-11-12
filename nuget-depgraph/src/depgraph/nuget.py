"""Получение зависимостей пакетов NuGet по HTTP (flat container API).

Для пакета id версии ver читается спецификация
``{repo}/{id}/{ver}/{id}.nuspec`` (id и ver в нижнем регистре).
Менеджеры пакетов и сторонние библиотеки не используются.
"""
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from depgraph.repository import RepositoryError

HTTP_TIMEOUT = 20
HTTP_NOT_FOUND = 404
USER_AGENT = "depgraph-study/0.1"
VERSION_PARTS = 3


def http_get(url):
    """Скачивает url и возвращает тело ответа как строку."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as resp:
            return resp.read().decode("utf-8-sig")
    except urllib.error.HTTPError as err:
        if err.code == HTTP_NOT_FOUND:
            raise RepositoryError(f"не найдено: {url}") from err
        raise RepositoryError(f"HTTP {err.code}: {url}") from err
    except (urllib.error.URLError, OSError) as err:
        raise RepositoryError(f"ошибка сети для {url}: {err}") from err


def normalize_version(version):
    """Приводит версию к нормализованной форме NuGet (нижний регистр)."""
    core, sep, suffix = version.strip().lower().partition("-")
    core = core.split("+")[0]
    parts = core.split(".")
    while len(parts) < VERSION_PARTS:
        parts.append("0")
    if len(parts) > VERSION_PARTS and int(parts[VERSION_PARTS]) == 0:
        parts = parts[:VERSION_PARTS]
    suffix = suffix.split("+")[0]
    return ".".join(parts) + (sep + suffix if sep else "")


def lower_bound(version_range):
    """Возвращает нижнюю границу диапазона версий или None, если её нет.

    ``1.0`` и ``[1.0]`` дают 1.0; ``[1.0, 2.0)`` и ``(1.0,)`` дают 1.0;
    ``(, 2.0]`` и пустая строка дают None.
    """
    text = version_range.strip()
    if text[:1] in "[(":
        text = text[1:]
    if text[-1:] in "])":
        text = text[:-1]
    low = text.split(",")[0].strip()
    return low or None


def _local(tag):
    """Возвращает имя тега без пространства имён."""
    return tag.rsplit("}", 1)[-1]


def _read_dependencies(parent):
    """Возвращает список пар (id, диапазон) из элемента-контейнера."""
    result = []
    for node in parent:
        if _local(node.tag) == "dependency" and node.get("id"):
            result.append((node.get("id"), node.get("version", "")))
    return result


def collect_groups(root):
    """Собирает группы зависимостей [(targetFramework, [(id, range)])]."""
    groups = []
    legacy = []
    for deps in root.iter():
        if _local(deps.tag) != "dependencies":
            continue
        for child in deps:
            if _local(child.tag) == "group":
                framework = child.get("targetFramework", "")
                groups.append((framework, _read_dependencies(child)))
            elif _local(child.tag) == "dependency":
                legacy.extend(_read_dependencies(deps))
                break
    if legacy:
        groups.append(("", legacy))
    return groups


def select_group(groups, framework):
    """Выбирает группу: точное совпадение, группа без платформы, последняя."""
    wanted = framework.lower()
    for name, deps in groups:
        if name.lower() == wanted:
            return deps
    for name, deps in groups:
        if not name:
            return deps
    return groups[-1][1] if groups else []


def parse_nuspec(text, framework):
    """Разбирает .nuspec и возвращает зависимости для платформы."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        raise RepositoryError(f"некорректный .nuspec: {err}") from err
    unique = {}
    for dep_id, dep_range in select_group(collect_groups(root), framework):
        unique.setdefault(dep_id, dep_range)
    return list(unique.items())


class NuGetSource:
    """Источник зависимостей: реальный репозиторий NuGet."""

    def __init__(self, base_url, framework, fetch=http_get):
        """Создаёт источник; fetch можно подменить в тестах."""
        self.base_url = base_url.rstrip("/")
        self.framework = framework
        self.fetch = fetch

    def nuspec_url(self, name, version):
        """Возвращает URL файла .nuspec пакета."""
        pkg = name.lower()
        ver = normalize_version(version)
        return f"{self.base_url}/{pkg}/{ver}/{pkg}.nuspec"

    def lowest_version(self, name):
        """Возвращает наименьшую опубликованную версию пакета."""
        url = f"{self.base_url}/{name.lower()}/index.json"
        try:
            versions = json.loads(self.fetch(url)).get("versions", [])
        except (ValueError, AttributeError) as err:
            raise RepositoryError(f"некорректный ответ: {url}") from err
        if not versions:
            raise RepositoryError(f"нет версий пакета {name}")
        return versions[0]

    def resolve(self, name, version_range):
        """Подбирает версию по диапазону (как NuGet: наименьшая подходящая)."""
        low = lower_bound(version_range)
        return normalize_version(low) if low else self.lowest_version(name)

    def dependencies(self, name, version):
        """Возвращает прямые зависимости как список пар (имя, версия)."""
        text = self.fetch(self.nuspec_url(name, version))
        pairs = parse_nuspec(text, self.framework)
        return [(dep, self.resolve(dep, rng)) for dep, rng in pairs]
