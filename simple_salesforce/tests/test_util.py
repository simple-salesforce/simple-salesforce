# coding=utf-8

"""Tests for simple-salesforce utility functions"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import datetime
import pytz
from simple_salesforce.util import (
    getUniqueElementValueFromXmlString, date_to_iso8601, SalesforceError
)


class TestXMLParser(unittest.TestCase):
    """Test the XML parser utility function"""
    def test_returns_valid_value(self):
        """Test that when given the correct XML a valid response is returned"""
        result = getUniqueElementValueFromXmlString(
            '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
        self.assertEqual(result, 'bar')

    def test_date_to_iso8601(self):
        """Test date conversion"""
        date = pytz.UTC.localize(datetime.datetime(2014, 3, 22, 00, 00, 00, 0))
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00%2B00%3A00'
        self.assertEqual(result, expected)

        date = pytz.timezone('America/Phoenix').localize(
            datetime.datetime(2014, 3, 22, 00, 00, 00, 0))
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00-07%3A00'
        self.assertEqual(result, expected)


class TestSalesforceError(unittest.TestCase):
    """Test SalesforceError"""
    def test_str(self):
        """Test that str(SalesforceError) works correctly"""
        err = SalesforceError(
            u"http://example.com/føø", 400, u"résource", u"nøn-àscìi")

        # This is correct for both python2 and python3
        self.assertIsInstance(str(err), str)
