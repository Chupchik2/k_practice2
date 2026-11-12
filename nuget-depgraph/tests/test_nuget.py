"""Тесты получения зависимостей NuGet (без сети, с подменой fetch)."""
import unittest

from depgraph.nuget import (
    NuGetSource,
    lower_bound,
    normalize_version,
    parse_nuspec,
)
from depgraph.repository import RepositoryError

NS = "http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd"
GROUPED = f"""<?xml version="1.0"?>
<package xmlns="{NS}"><metadata><id>Demo</id><version>1.0.0</version>
<dependencies>
  <group targetFramework=".NETStandard2.0">
    <dependency id="Lib.One" version="1.2.3" />
    <dependency id="Lib.Two" version="[2.0.0, 3.0.0)" />
  </group>
  <group targetFramework="net6.0">
    <dependency id="Only.Net6" version="9.0.0" />
  </group>
</dependencies></metadata></package>"""
LEGACY = f"""<package xmlns="{NS}"><metadata><dependencies>
  <dependency id="Old.Lib" version="1.0" />
</dependencies></metadata></package>"""
EMPTY = f'<package xmlns="{NS}"><metadata><id>X</id></metadata></package>'


class HelpersTest(unittest.TestCase):
    """Версии и диапазоны."""

    def test_normalize(self):
        """Нормализация версий."""
        self.assertEqual(normalize_version("13.0"), "13.0.0")
        self.assertEqual(normalize_version("1.0.0.0"), "1.0.0")
        self.assertEqual(normalize_version("1.0.0.1"), "1.0.0.1")
        self.assertEqual(normalize_version("1.0.0-Beta+x"), "1.0.0-beta")

    def test_lower_bound(self):
        """Нижняя граница диапазона."""
        self.assertEqual(lower_bound("1.0"), "1.0")
        self.assertEqual(lower_bound("[1.0]"), "1.0")
        self.assertEqual(lower_bound("[1.0, 2.0)"), "1.0")
        self.assertEqual(lower_bound("(1.0,)"), "1.0")
        self.assertIsNone(lower_bound("(, 2.0]"))
        self.assertIsNone(lower_bound(""))


class ParseNuspecTest(unittest.TestCase):
    """Разбор .nuspec."""

    def test_exact_framework(self):
        """Выбирается группа нужной платформы."""
        deps = parse_nuspec(GROUPED, ".NETStandard2.0")
        self.assertEqual([d for d, _ in deps], ["Lib.One", "Lib.Two"])
        deps = parse_nuspec(GROUPED, "NET6.0")
        self.assertEqual([d for d, _ in deps], ["Only.Net6"])

    def test_fallback_last_group(self):
        """Неизвестная платформа: берётся последняя группа."""
        deps = parse_nuspec(GROUPED, "net99.0")
        self.assertEqual([d for d, _ in deps], ["Only.Net6"])

    def test_legacy_and_empty(self):
        """Старый формат без групп и пакет без зависимостей."""
        self.assertEqual(parse_nuspec(LEGACY, "x"), [("Old.Lib", "1.0")])
        self.assertEqual(parse_nuspec(EMPTY, "x"), [])

    def test_bad_xml(self):
        """Битый XML даёт RepositoryError."""
        with self.assertRaises(RepositoryError):
            parse_nuspec("<a>", "x")


class NuGetSourceTest(unittest.TestCase):
    """Источник NuGet с поддельной сетью."""

    def make(self, pages):
        """Создаёт источник, отвечающий из словаря pages."""
        def fetch(url):
            """Поддельная загрузка страницы."""
            if url not in pages:
                raise RepositoryError(f"не найдено: {url}")
            return pages[url]
        return NuGetSource("https://repo.test/v3/", ".NETStandard2.0", fetch)

    def test_url(self):
        """URL строится в нижнем регистре и нормализуется."""
        source = self.make({})
        self.assertEqual(
            source.nuspec_url("Demo.Pkg", "1.0"),
            "https://repo.test/v3/demo.pkg/1.0.0/demo.pkg.nuspec",
        )

    def test_dependencies(self):
        """Прямые зависимости с подобранными версиями."""
        source = self.make({
            "https://repo.test/v3/demo/1.0.0/demo.nuspec": GROUPED,
        })
        self.assertEqual(
            source.dependencies("Demo", "1.0.0"),
            [("Lib.One", "1.2.3"), ("Lib.Two", "2.0.0")],
        )

    def test_open_lower_bound(self):
        """Нет нижней границы — берётся наименьшая версия из индекса."""
        spec = GROUPED.replace("[2.0.0, 3.0.0)", "(, 3.0.0)")
        source = self.make({
            "https://repo.test/v3/demo/1.0.0/demo.nuspec": spec,
            "https://repo.test/v3/lib.two/index.json":
                '{"versions": ["0.5.0", "1.0.0"]}',
        })
        self.assertEqual(source.dependencies("Demo", "1.0.0")[1],
                         ("Lib.Two", "0.5.0"))

    def test_missing_package(self):
        """Отсутствующий пакет даёт RepositoryError."""
        with self.assertRaises(RepositoryError):
            self.make({}).dependencies("Nope", "1.0.0")


if __name__ == "__main__":
    unittest.main()
