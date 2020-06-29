""" Tests for format.py """

import unittest
from datetime import datetime, date, timezone
from simple_salesforce import format_soql, format_external_id


class TestFormatSoql(unittest.TestCase):
    """ Test quoting/escaping of SOQL strings """

    def test_plain_string(self):
        """ Case where there is no quoting """
        query = "select foo from bar where x = 'y'"
        quoted = format_soql(query)
        self.assertEqual(quoted, query)

    def test_no_escape_needed(self):
        """ Quotes but doesn't escape simple values """
        query = "select foo from bar where x = {} and y = {named}"
        expected = "select foo from bar where x = 'value1' and y = 'value2'"
        quoted = format_soql(query, 'value1', named='value2')
        self.assertEqual(quoted, expected)

    def test_escaped_chars(self):
        """ Quotes and escape special chars """
        query = "select foo from bar where x = {} and y = {named}"
        expected = (
            "select foo from bar where"
            " x = 'val\\'ue1\\n' and y = 'val\\'ue2\\n'"
        )
        quoted = format_soql(query, 'val\'ue1\n', named='val\'ue2\n')
        self.assertEqual(quoted, expected)

    def test_lists(self):
        """ Conversion of lists to parentheses groups """
        query = "select foo from bar where x in {} and y in {named}"
        expected = (
            "select foo from bar where"
            " x in ('value1','val\\'ue1\\n')"
            " and y in ('value2','val\\'ue2\\n')"
        )
        quoted = format_soql(
            query,
            ['value1', 'val\'ue1\n'],
            named=['value2', 'val\'ue2\n']
        )
        self.assertEqual(quoted, expected)

    def test_number(self):
        """ Numbers are inserted without quoting """
        query = "select foo from bar where x = {} and y = {named}"
        expected = "select foo from bar where x = 1 and y = 2.37"
        quoted = format_soql(query, 1, named=2.37)
        self.assertEqual(quoted, expected)

    def test_booleans(self):
        """ Boolean literals are inserted """
        query = "select foo from bar where truth = {} and lies = {}"
        expected = "select foo from bar where truth = false and lies = true"
        quoted = format_soql(query, False, True)
        self.assertEqual(quoted, expected)

    def test_null(self):
        """ Null literals are inserted """
        query = "select foo from bar where name != {}"
        expected = "select foo from bar where name != null"
        quoted = format_soql(query, None)
        self.assertEqual(quoted, expected)

    def test_date(self):
        """ Date literals are inserted """
        query = "select foo from bar where date = {}"
        expected = "select foo from bar where date = 1987-02-01"
        quoted = format_soql(query, date(1987, 2, 1))
        self.assertEqual(quoted, expected)

    def test_datetime(self):
        """ Datetime literals are inserted """
        query = "select foo from bar where date = {}"
        expected = "select foo from bar where date = 1987-02-01T01:02:03+00:00"
        quoted = format_soql(
            query,
            datetime(1987, 2, 1, 1, 2, 3, tzinfo=timezone.utc)
        )
        self.assertEqual(quoted, expected)

    def test_literal(self):
        """ :literal format spec """
        query = "select foo from bar where income > {amt:literal}"
        expected = "select foo from bar where income > USD100"
        quoted = format_soql(query, amt='USD100')
        self.assertEqual(quoted, expected)

    def test_like(self):
        """ :like format spec """
        query = "select foo from bar where name like '%{:like}%'"
        expected = "select foo from bar where name like '%foo\\'\\%bar\\_%'"
        quoted = format_soql(query, 'foo\'%bar_')
        self.assertEqual(quoted, expected)

    def test_invalid(self):
        """ Unexpected value type """
        with self.assertRaises(ValueError):
            format_soql('select foo from bar where x = {}', {'x': 'y'})


class TestFormatExternalId(unittest.TestCase):
    """ Test formatting external IDs """

    def test_plain_string(self):
        """ Case where no escaping is needed """
        ext_id = format_external_id('name', 'something')
        self.assertEqual(ext_id, 'name/something')

    def test_quoted(self):
        """ Value requring some quoting """
        ext_id = format_external_id('name', 'some/other\'type value')
        self.assertEqual(ext_id, 'name/some%2Fother%27type%20value')
