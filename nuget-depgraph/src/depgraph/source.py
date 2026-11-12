"""Выбор источника зависимостей по конфигурации."""
from depgraph.nuget import NuGetSource
from depgraph.testrepo import TestRepository


def create_source(config):
    """Возвращает тестовый репозиторий или NuGet в зависимости от режима."""
    if config.test_mode:
        return TestRepository.from_file(config.repository)
    return NuGetSource(config.repository, config.framework)


def root_node(config):
    """Возвращает корневую вершину (в тестовом режиме версии нет)."""
    version = "" if config.test_mode else config.version
    return (config.package_name, version)
