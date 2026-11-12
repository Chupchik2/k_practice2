"""Тесты загрузки и проверки конфигурации."""
import json
import tempfile
import unittest
from pathlib import Path

from depgraph.config import ConfigError, load_config, parse_config

DATA = Path(__file__).parent / "data" / "simple.txt"


def valid(**changes):
    """Возвращает корректный словарь параметров с заменами."""
    data = {
        "package_name": "Newtonsoft.Json",
        "repository": "https://api.nuget.org/v3-flatcontainer/",
        "test_mode": False,
        "version": "13.0.3",
        "output_file": "graph.svg",
        "max_depth": 3,
    }
    data.update(changes)
    return data


class ParseConfigTest(unittest.TestCase):
    """Проверка parse_config."""

    def test_valid(self):
        """Корректная конфигурация принимается."""
        config = parse_config(valid())
        self.assertEqual(config.package_name, "Newtonsoft.Json")
        self.assertEqual(config.max_depth, 3)

    def test_test_mode(self):
        """Тестовый режим: буквенное имя и существующий файл."""
        config = parse_config(
            valid(package_name="A", repository=str(DATA),
                  test_mode=True, version="")
        )
        self.assertTrue(config.test_mode)

    def test_errors(self):
        """Каждый некорректный параметр даёт ConfigError."""
        bad = [
            valid(package_name=""),
            valid(package_name="bad name!"),
            valid(repository="ftp://x"),
            valid(test_mode="yes"),
            valid(version="1.x"),
            valid(output_file="graph.png"),
            valid(output_file="/no/such/dir/g.svg"),
            valid(max_depth=0),
            valid(max_depth="3"),
            valid(max_depth=True),
            valid(package_name="a", repository=str(DATA), test_mode=True),
            valid(repository="/no/file.txt", test_mode=True,
                  package_name="A"),
            valid(unknown=1),
        ]
        for data in bad:
            with self.subTest(data=data):
                with self.assertRaises(ConfigError):
                    parse_config(data)

    def test_missing_key(self):
        """Отсутствие обязательного ключа — ошибка."""
        data = valid()
        del data["version"]
        with self.assertRaises(ConfigError):
            parse_config(data)


class LoadConfigTest(unittest.TestCase):
    """Проверка load_config."""

    def test_file_errors(self):
        """Нет файла и битый JSON дают ConfigError."""
        with self.assertRaises(ConfigError):
            load_config("/no/such/config.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text("{oops", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_roundtrip(self):
        """Файл с корректным JSON загружается."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps(valid()), encoding="utf-8")
            self.assertEqual(load_config(path).version, "13.0.3")


if __name__ == "__main__":
    unittest.main()
