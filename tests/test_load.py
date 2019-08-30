import unittest
import io
import loader
from contextlib import redirect_stdout


class AppRunner:
    def run(self, main):
        app = main()
        app.run()


class TestCommandFactory(object):
    pass


class TestLoad(unittest.TestCase):
    def test_abc(self):
        runner = AppRunner()
        runner.commandFactory = TestCommandFactory()
        f = io.StringIO()
        with redirect_stdout(f):
            runner.run(loader.LoaderMain)

        self.assertEqual("", f.getvalue())
