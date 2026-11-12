"""Загрузка и проверка конфигурационного файла JSON."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FRAMEWORK = ".NETStandard2.0"
MIN_DEPTH = 1
REQUIRED_KEYS = (
    "package_name",
    "repository",
    "test_mode",
    "version",
    "output_file",
    "max_depth",
)
OPTIONAL_KEYS = ("framework",)

NUGET_ID_RE = re.compile(r"^[A-Za-z0-9_]+([.\-][A-Za-z0-9_]+)*$")
TEST_ID_RE = re.compile(r"^[A-Z]+$")
VERSION_RE = re.compile(
    r"^\d+(\.\d+){0,3}(-[0-9A-Za-z.\-]+)?(\+[0-9A-Za-z.\-]+)?$"
)


class ConfigError(Exception):
    """Ошибка в конфигурационном файле."""


@dataclass(frozen=True)
class Config:
    """Параметры, настраиваемые пользователем."""

    package_name: str
    repository: str
    test_mode: bool
    version: str
    output_file: str
    max_depth: int
    framework: str = DEFAULT_FRAMEWORK

    def as_pairs(self):
        """Возвращает параметры как список пар (ключ, значение)."""
        return list(vars(self).items())


def _require_str(data, key):
    """Возвращает непустую строку по ключу или бросает ConfigError."""
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{key}': ожидается непустая строка")
    return value.strip()


def _check_package_name(name, test_mode):
    """Проверяет имя пакета для выбранного режима."""
    if test_mode and not TEST_ID_RE.match(name):
        raise ConfigError(
            "'package_name': в тестовом режиме имя состоит из "
            f"заглавных латинских букв, получено '{name}'"
        )
    if not test_mode and not NUGET_ID_RE.match(name):
        raise ConfigError(f"'package_name': недопустимый id '{name}'")


def _check_repository(repo, test_mode):
    """Проверяет URL репозитория или путь к тестовому файлу."""
    if test_mode:
        if not Path(repo).is_file():
            raise ConfigError(f"'repository': файл '{repo}' не найден")
    elif not re.match(r"^https?://\S+$", repo):
        raise ConfigError(f"'repository': ожидается http(s) URL: '{repo}'")


def _check_version(data, test_mode):
    """Возвращает версию; в тестовом режиме она может быть пустой."""
    value = data["version"]
    if not isinstance(value, str):
        raise ConfigError("'version': ожидается строка")
    value = value.strip()
    if test_mode and not value:
        return value
    if not VERSION_RE.match(value):
        raise ConfigError(f"'version': некорректная версия '{value}'")
    return value


def _check_output(data):
    """Проверяет имя выходного SVG-файла."""
    value = _require_str(data, "output_file")
    path = Path(value)
    if path.suffix.lower() != ".svg":
        raise ConfigError("'output_file': ожидается файл с расширением .svg")
    if not path.resolve().parent.is_dir():
        raise ConfigError(f"'output_file': нет каталога '{path.parent}'")
    return value


def _check_depth(data):
    """Проверяет максимальную глубину анализа."""
    value = data["max_depth"]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError("'max_depth': ожидается целое число")
    if value < MIN_DEPTH:
        raise ConfigError(f"'max_depth': значение должно быть >= {MIN_DEPTH}")
    return value


def _check_keys(data):
    """Проверяет набор ключей: обязательные есть, лишних нет."""
    if not isinstance(data, dict):
        raise ConfigError("корень конфигурации должен быть объектом JSON")
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise ConfigError("отсутствуют параметры: " + ", ".join(missing))
    unknown = set(data) - set(REQUIRED_KEYS) - set(OPTIONAL_KEYS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"неизвестные параметры: {names}")


def parse_config(data):
    """Проверяет словарь параметров и возвращает Config."""
    _check_keys(data)
    test_mode = data["test_mode"]
    if not isinstance(test_mode, bool):
        raise ConfigError("'test_mode': ожидается true или false")
    name = _require_str(data, "package_name")
    _check_package_name(name, test_mode)
    repo = _require_str(data, "repository")
    _check_repository(repo, test_mode)
    framework = DEFAULT_FRAMEWORK
    if "framework" in data:
        framework = _require_str(data, "framework")
    return Config(
        package_name=name,
        repository=repo,
        test_mode=test_mode,
        version=_check_version(data, test_mode),
        output_file=_check_output(data),
        max_depth=_check_depth(data),
        framework=framework,
    )


def load_config(path):
    """Читает JSON-файл и возвращает проверенный Config."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as err:
        raise ConfigError(f"не удалось прочитать '{path}': {err}") from err
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"некорректный JSON: {err}") from err
    return parse_config(data)
