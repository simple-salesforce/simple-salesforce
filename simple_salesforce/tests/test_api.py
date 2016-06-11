"""Tests for api.py"""

import re
try:
    # Python 2.6
    import unittest2 as unittest
except ImportError:
    import unittest

import responses

try:
    # Python 2.6/2.7
    import httplib as http
    from mock import Mock, patch
except ImportError:
    # Python 3
    import http.client as http
    from unittest.mock import Mock, patch

import requests

from simple_salesforce import tests
from simple_salesforce.api import (
    _exception_handler,
    Salesforce,
    SalesforceMoreThanOneRecord,
    SalesforceMalformedRequest,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError
)


class TestSalesforce(unittest.TestCase):
    """Tests for the Salesforce instance"""
    def setUp(self):
        """Setup the SalesforceLogin tests"""
        request_patcher = patch('simple_salesforce.api.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    @responses.activate
    def test_custom_session_success(self):
        """Ensure custom session is used"""
        responses.add(
            responses.POST,
            re.compile(r'^https://.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'called': False,
        }

        # pylint: disable=unused-argument,missing-docstring
        def on_response(*args, **kwargs):
            session_state['called'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        client = Salesforce(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token')

        self.assertEqual(tests.SESSION_ID, client.session_id)
        self.assertEqual(session, client.request)

    @responses.activate
    def test_custom_version_success(self):
        """Test custom version"""
        responses.add(
            responses.POST,
            re.compile(r'^https://.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )

        # Use an invalid version that is guaranteed to never be used
        expected_version = '4.2'
        client = Salesforce(
            session=requests.Session(), username='foo@bar.com',
            password='password', security_token='token',
            version=expected_version)

        self.assertEqual(
            client.base_url.split('/')[-2], 'v%s' % expected_version)


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
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'More than one record for '
            'http://www.example.com/. Response content: Example Content'))

    def test_malformed_request(self):
        """Test a malformed request (400 code)"""
        self.mockresult.status_code = 400
        with self.assertRaises(SalesforceMalformedRequest) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Malformed request '
            'http://www.example.com/. Response content: Example Content'))

    def test_expired_session(self):
        """Test an expired session (401 code)"""
        self.mockresult.status_code = 401
        with self.assertRaises(SalesforceExpiredSession) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Expired session for '
            'http://www.example.com/. Response content: Example Content'))

    def test_request_refused(self):
        """Test a refused request (403 code)"""
        self.mockresult.status_code = 403
        with self.assertRaises(SalesforceRefusedRequest) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Request refused for '
            'http://www.example.com/. Response content: Example Content'))

    def test_resource_not_found(self):
        """Test resource not found (404 code)"""
        self.mockresult.status_code = 404
        with self.assertRaises(SalesforceResourceNotFound) as cm:
            _exception_handler(self.mockresult, 'SpecialContacts')

        self.assertEqual(str(cm.exception), (
            'Resource SpecialContacts Not'
            ' Found. Response content: Example Content'))

    def test_generic_error_code(self):
        """Test an error code that is otherwise not caught"""
        self.mockresult.status_code = 500
        with self.assertRaises(SalesforceGeneralError) as cm:
            _exception_handler(self.mockresult)

        self.assertEqual(str(cm.exception), (
            'Error Code 500. Response content'
            ': Example Content'))
