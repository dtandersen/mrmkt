import unittest
from dataclasses import dataclass

from sql import InsecureSqlConverter


@dataclass
class TestRow:
    x: int
    y: str


class TestStringMethods(unittest.TestCase):
    def test_insert_dict(self):
        converter = InsecureSqlConverter()
        insert = converter.to_insert('table', {"a": "z", "b": 1})
        self.assertEqual("insert into table (a, b) values ('z', 1)", insert)

    def test_insert_database(self):
        converter = InsecureSqlConverter()
        insert = converter.to_insert('table', TestRow(x=5, y="b"))
        self.assertEqual("insert into table (x, y) values (5, 'b')", insert)
