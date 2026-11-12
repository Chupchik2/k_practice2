"""Проверка настоящей HTTP-загрузки на локальном сервере."""
import functools
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from depgraph.nuget import NuGetSource
from depgraph.repository import RepositoryError

SPEC = """<package><metadata><dependencies>
<group targetFramework=".NETStandard2.0">
<dependency id="Child" version="2.0.0"/></group>
</dependencies></metadata></package>"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик без вывода логов."""

    def log_message(self, *args):
        """Отключает журнал запросов."""


class LocalRepoTest(unittest.TestCase):
    """NuGetSource с реальным http_get и локальным сервером."""

    def setUp(self):
        """Поднимает сервер с одним пакетом parent 1.0.0."""
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name) / "parent" / "1.0.0"
        folder.mkdir(parents=True)
        (folder / "parent.nuspec").write_text(SPEC, encoding="utf-8")
        handler = functools.partial(QuietHandler, directory=self.tmp.name)
        self.server = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever,
                         daemon=True).start()
        port = self.server.server_address[1]
        self.source = NuGetSource(f"http://127.0.0.1:{port}/",
                                  ".NETStandard2.0")

    def tearDown(self):
        """Останавливает сервер."""
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_found(self):
        """Зависимости читаются по HTTP."""
        self.assertEqual(self.source.dependencies("Parent", "1.0.0"),
                         [("Child", "2.0.0")])

    def test_not_found(self):
        """Ответ 404 превращается в RepositoryError."""
        with self.assertRaises(RepositoryError):
            self.source.dependencies("Absent", "1.0.0")


if __name__ == "__main__":
    unittest.main()
