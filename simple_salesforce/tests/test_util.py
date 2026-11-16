"""Tests for simple-salesforce utility functions"""
import datetime
import unittest
from unittest.mock import Mock

import pytz
from simple_salesforce.exceptions import (SalesforceExpiredSession,
                                          SalesforceGeneralError,
                                          SalesforceMalformedRequest,
                                          SalesforceMoreThanOneRecord,
                                          SalesforceRefusedRequest,
                                          SalesforceResourceNotFound)
from simple_salesforce.util import (date_to_iso8601, exception_handler,
                                    getUniqueElementValueFromXmlString,
                                    safe_urljoin)


class TestXMLParser(unittest.TestCase):
    """Test the XML parser utility function"""
    def test_returns_valid_value(self):
        """Test that when given the correct XML a valid response is returned"""
        result = getUniqueElementValueFromXmlString(
            '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
        self.assertEqual(result, 'bar')

    def test_date_to_iso8601(self):
        """Test date conversion"""
        # pylint: disable=no-value-for-parameter
        date = pytz.UTC.localize(datetime.datetime(2014, 3, 22, 00, 00, 00, 0))
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00%2B00%3A00'
        self.assertEqual(result, expected)

        date = pytz.timezone('America/Phoenix').localize(
            datetime.datetime(2014, 3, 22, 00, 00, 00, 0))
        result = date_to_iso8601(date)
        expected = '2014-03-22T00%3A00%3A00-07%3A00'
        self.assertEqual(result, expected)

        # Naive datetimes have no UTC offset; they must not produce a
        # dangling ':' (malformed for Salesforce). They are treated as UTC.
        naive = datetime.datetime(2014, 3, 22, 0, 0, 0, 0)
        result = date_to_iso8601(naive)
        expected = '2014-03-22T00%3A00%3A00%2B00%3A00'
        self.assertEqual(result, expected)
        self.assertFalse(result.endswith('%3A'))

        # A tzinfo whose utcoffset() is None (e.g. unlocalized pytz timezone)
        # also yields an empty %z and must get the same UTC treatment.
        class _NoneOffsetTz(datetime.tzinfo):
            def utcoffset(self, dt):
                return None

            def dst(self, dt):
                return None

        result = date_to_iso8601(
            datetime.datetime(2014, 3, 22, 0, 0, 0, 0, tzinfo=_NoneOffsetTz()))
        self.assertEqual(result, expected)
        self.assertFalse(result.endswith('%3A'))


class TestExceptionHandler(unittest.TestCase):
    """Test the exception router"""

    def setUp(self):
        """Setup the exception router tests"""
        self.mockresult = Mock()
        self.mockresult.url = 'http://www.example.com/'
        self.mockresult.json.return_value = 'Example Content'

    def test_multiple_records_returned(self):
        """Test multiple records returned (a 300 code)"""
        self.mockresult.status_code = 300
        with self.assertRaises(SalesforceMoreThanOneRecord) as cm:
            exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'More than one record for '
            'http://www.example.com/. Response content: Example Content'))

    def test_malformed_request(self):
        """Test a malformed request (400 code)"""
        self.mockresult.status_code = 400
        with self.assertRaises(SalesforceMalformedRequest) as cm:
            exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Malformed request '
            'http://www.example.com/. Response content: Example Content'))

    def test_expired_session(self):
        """Test an expired session (401 code)"""
        self.mockresult.status_code = 401
        with self.assertRaises(SalesforceExpiredSession) as cm:
            exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Expired session for '
            'http://www.example.com/. Response content: Example Content'))

    def test_request_refused(self):
        """Test a refused request (403 code)"""
        self.mockresult.status_code = 403
        with self.assertRaises(SalesforceRefusedRequest) as cm:
            exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Request refused for '
            'http://www.example.com/. Response content: Example Content'))

    def test_resource_not_found(self):
        """Test resource not found (404 code)"""
        self.mockresult.status_code = 404
        with self.assertRaises(SalesforceResourceNotFound) as cm:
            exception_handler(self.mockresult, 'SpecialContacts')

        self.assertEqual(str(cm.exception), (
            'Resource SpecialContacts Not'
            ' Found. Response content: Example Content'))

    def test_generic_error_code(self):
        """Test an error code that is otherwise not caught"""
        self.mockresult.status_code = 500
        with self.assertRaises(SalesforceGeneralError) as cm:
            exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Error Code 500. Response content'
            ': Example Content'))


class TestSafeUrljoin(unittest.TestCase):
    """Test joining caller-supplied paths onto a Salesforce resource URL"""
    BASE = 'https://my.salesforce.com/services/data/v59.0/sobjects/Case/'

    def test_relative_paths_are_joined(self):
        """Record ids, external id paths and query strings are allowed"""
        for path, expected in (
                ('500xx000000AbCd', self.BASE + '500xx000000AbCd'),
                ('ExtId__c/123', self.BASE + 'ExtId__c/123'),
                ('500xx?fields=Id', self.BASE + '500xx?fields=Id'),
                ('describe', self.BASE + 'describe'),
                ):
            with self.subTest(path=path):
                self.assertEqual(safe_urljoin(self.BASE, path), expected)

    def test_paths_escaping_base_are_rejected(self):
        """Absolute URLs, network paths and traversal raise ValueError"""
        for path in ('https://attacker.example/leak',
                     'HTTPS://attacker.example/leak',
                     '//attacker.example/leak',
                     '\t//attacker.example/leak',
                     '/services/data/v59.0/limits',
                     '../Account/001',
                     'a/../../Account/001'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    safe_urljoin(self.BASE, path)
