import json
import unittest
from dataclasses import dataclass, asdict

from hamcrest import *

from mrmkt.common.sql import JsonField, InsecureSqlGenerator
from mrmkt.common.util import EnhancedJSONEncoder


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
    def test_insert_with_values(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert('table', asdict(TestRow(x=5, y="b")))
        self.assertEqual("insert into table (x, y) values (%s, %s)", insert)
        assert_that(values, equal_to((5, "b")))

    def test_insert_with_different_order(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert('table', TestRow2(b="z", a=11))
        self.assertEqual("insert into table (b, a) values (%s, %s)", insert)
        assert_that(values, equal_to(("z", 11)))

    def test_insert_json(self):
        converter = InsecureSqlGenerator()
        insert, values = converter.to_insert('table', JsonRow(data=JsonField(data=TestRow(x=5, y="b"))))
        self.assertEqual("insert into table (data) values (%s)", insert)
        assert_that(values, equal_to(tuple([json.dumps(TestRow(x=5, y="b"), cls=EnhancedJSONEncoder)])))
