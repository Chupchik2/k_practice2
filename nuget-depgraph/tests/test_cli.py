"""Тесты интерфейса командной строки (этап 1)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from depgraph.cli import EXIT_ERROR, EXIT_OK, EXIT_USAGE, main


class CliStage1Test(unittest.TestCase):
    """Вывод параметров и обработка ошибок."""

    def run_cli(self, data):
        """Запускает main с конфигом data, возвращает (код, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with contextlib.redirect_stdout(out):
                with contextlib.redirect_stderr(err):
                    code = main(["--config", str(path), "--show-config"])
        return code, out.getvalue(), err.getvalue()

    def test_prints_pairs(self):
        """Параметры выводятся как ключ: значение."""
        code, out, _ = self.run_cli({
            "package_name": "Serilog",
            "repository": "https://api.nuget.org/v3-flatcontainer/",
            "test_mode": False,
            "version": "3.1.1",
            "output_file": "g.svg",
            "max_depth": 2,
        })
        self.assertEqual(code, EXIT_OK)
        self.assertIn("package_name: Serilog", out)
        self.assertIn("max_depth: 2", out)

    def test_error_exit_code(self):
        """Ошибка конфигурации даёт код 2 и сообщение в stderr."""
        code, _, err = self.run_cli({"package_name": "X"})
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("Ошибка конфигурации", err)


DATA = Path(__file__).parent / "data"


class CliStage3Test(unittest.TestCase):
    """Режим тестирования на файле репозитория."""

    def run_test_mode(self, repo, package, depth):
        """Запускает main в тестовом режиме, возвращает (код, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps({
                "package_name": package, "repository": str(DATA / repo),
                "test_mode": True, "version": "",
                "output_file": str(Path(tmp) / "g.svg"),
                "max_depth": depth,
            }), encoding="utf-8")
            with contextlib.redirect_stdout(out):
                with contextlib.redirect_stderr(err):
                    code = main(["--config", str(path)])
        return code, out.getvalue(), err.getvalue()

    def test_graph_output(self):
        """Печатается список смежности."""
        code, out, _ = self.run_test_mode("simple.txt", "A", 3)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("A -> B, C", out)
        self.assertIn("Циклические зависимости: нет", out)

    def test_cycle_output(self):
        """Цикл выводится в тексте."""
        _, out, _ = self.run_test_mode("cycle.txt", "A", 9)
        self.assertIn("Цикл: A -> B -> C -> A", out)

    def test_repository_error(self):
        """Ошибка репозитория даёт код 1."""
        code, _, err = self.run_test_mode("broken.txt", "A", 3)
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("Ошибка репозитория", err)


if __name__ == "__main__":
    unittest.main()
