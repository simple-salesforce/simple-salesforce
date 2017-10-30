"""Tests for login.py"""

import re
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import responses
import requests
try:
    # Python 2.6/2.7
    import httplib as http
    from urlparse import urlparse
    from mock import Mock, patch
except ImportError:
    # Python 3
    import http.client as http
    from unittest.mock import Mock, patch
    from urllib.parse import urlparse

from simple_salesforce import tests
from simple_salesforce.login import SalesforceLogin
from simple_salesforce.exceptions import SalesforceAuthenticationFailed


class TestSalesforceLogin(unittest.TestCase):
    """Tests for the SalesforceLogin function"""
    def setUp(self):
        """Setup the SalesforceLogin tests"""
        request_patcher = patch('simple_salesforce.login.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    @responses.activate
    def test_default_domain_success(self):
        """Test default domain logic and login"""
        responses.add(
            responses.POST,
            re.compile(r'^https://login.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'used': False,
        }

        # pylint: disable=missing-docstring,unused-argument
        def on_response(*args, **kwargs):
            session_state['used'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        session_id, instance = SalesforceLogin(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token')
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    @responses.activate
    def test_custom_domain_success(self):
        """Test custom domain login"""
        responses.add(
            responses.POST,
            re.compile(r'^https://testdomain.my.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'used': False,
        }

        # pylint: disable=missing-docstring,unused-argument
        def on_response(*args, **kwargs):
            session_state['used'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        session_id, instance = SalesforceLogin(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token',
            domain='testdomain.my')
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    @responses.activate
    def test_deprecated_sandbox_disabled_success(self):
        """Test sandbox argument set to False"""
        responses.add(
            responses.POST,
            re.compile(r'^https://login.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'used': False,
        }

        # pylint: disable=missing-docstring,unused-argument
        def on_response(*args, **kwargs):
            session_state['used'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        session_id, instance = SalesforceLogin(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token',
            sandbox=False)
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    @responses.activate
    def test_deprecated_sandbox_enabled_success(self):
        """Test sandbox argument set to True"""
        responses.add(
            responses.POST,
            re.compile(r'^https://test.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'used': False,
        }

        # pylint: disable=missing-docstring,unused-argument
        def on_response(*args, **kwargs):
            session_state['used'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        session_id, instance = SalesforceLogin(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token',
            sandbox=True)
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    def test_domain_sandbox_mutual_exclusion_failure(self):
        """Test sandbox and domain mutual exclusion"""

        with self.assertRaises(ValueError):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                security_token='token',
                domain='login',
                sandbox=False
            )

    @responses.activate
    def test_custom_session_success(self):
        """Test custom session"""
        responses.add(
            responses.POST,
            re.compile(r'^https://.*$'),
            body=tests.LOGIN_RESPONSE_SUCCESS,
            status=http.OK
        )
        session_state = {
            'used': False,
        }

        # pylint: disable=missing-docstring,unused-argument
        def on_response(*args, **kwargs):
            session_state['used'] = True

        session = requests.Session()
        session.hooks = {
            'response': on_response,
        }
        session_id, instance = SalesforceLogin(
            session=session,
            username='foo@bar.com',
            password='password',
            security_token='token')
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    def test_failure(self):
        """Test A Failed Login Response"""
        return_mock = Mock()
        return_mock.status_code = 500
        # pylint: disable=line-too-long
        return_mock.content = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sf="urn:fault.partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><soapenv:Fault><faultcode>INVALID_LOGIN</faultcode><faultstring>INVALID_LOGIN: Invalid username, password, security token; or user locked out.</faultstring><detail><sf:LoginFault xsi:type="sf:LoginFault"><sf:exceptionCode>INVALID_LOGIN</sf:exceptionCode><sf:exceptionMessage>Invalid username, password, security token; or user locked out.</sf:exceptionMessage></sf:LoginFault></detail></soapenv:Fault></soapenv:Body></soapenv:Envelope>'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                security_token='token',
                domain='test'
            )
        self.assertTrue(self.mockrequest.post.called)
