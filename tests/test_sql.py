import json
import unittest
from dataclasses import dataclass, asdict

from common.sql import InsecureSqlGenerator
from hamcrest import *

from common.sqlfinrepo import JsonField
from common.util import EnhancedJSONEncoder


@dataclass
class TestRow:
    x: int
    y: str


@dataclass
class TestRow2:
    b: str
    a: int


@dataclass
class JsonRow:
    data: JsonField


class TestStringMethods(unittest.TestCase):
    def test_insert_dict(self):
        converter = InsecureSqlGenerator()
        insert = converter.to_insert('table', {"a": "z", "b": 1, "c": 2.1})
        self.assertEqual("insert into table (a, b, c) values ('z', 1, 2.1)", insert)

    def test_insert_database(self):
        converter = InsecureSqlGenerator()
        insert = converter.to_insert('table', TestRow(x=5, y="b"))
        self.assertEqual("insert into table (x, y) values (5, 'b')", insert)

    def test_insert_with_values(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert2('table', asdict(TestRow(x=5, y="b")))
        self.assertEqual("insert into table (x, y) values (%s, %s)", insert)
        assert_that(values, equal_to((5, "b")))

    def test_insert_with_different_order(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert2('table', TestRow2(b="z", a=11))
        self.assertEqual("insert into table (b, a) values (%s, %s)", insert)
        assert_that(values, equal_to(("z", 11)))

    def test_insert_json(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert2('table', JsonRow(data=JsonField(data=TestRow(x=5, y="b"))))
        self.assertEqual("insert into table (data) values (%s)", insert)
        assert_that(values, equal_to(tuple([json.dumps(TestRow(x=5, y="b"), cls=EnhancedJSONEncoder)])))
