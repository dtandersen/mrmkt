import os
import subprocess
import unittest


class TestLoad(unittest.TestCase):
    def test_1(self):
        console = subprocess.run(
            ["python", "loader.py"],
            cwd=os.getcwd()+"/..",
            capture_output=True,
            text=True)\
            .stdout

        self.assertEqual("", console)
