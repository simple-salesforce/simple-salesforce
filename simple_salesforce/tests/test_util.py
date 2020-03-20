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
                                    getUniqueElementValueFromXmlString)


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
