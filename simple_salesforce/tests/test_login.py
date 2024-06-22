"""Tests for login.py"""

import http.client as http
import re
import unittest
import warnings
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import requests
import responses

from simple_salesforce import tests
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from simple_salesforce.login import SalesforceLogin


class TestSalesforceLogin(unittest.TestCase):
    """Tests for the SalesforceLogin function"""

    def setUp(self):
        """Setup the SalesforceLogin tests"""
        request_patcher = patch('simple_salesforce.login.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    def _test_login_success(self, url_regex, salesforce_login_kwargs,
                            response_body=tests.LOGIN_RESPONSE_SUCCESS):
        """Test SalesforceLogin with one set of arguments.

        Mock login requests at url_regex, returning a successful response,
        response_body. Check that the fake-login process works when passing
        salesforce_login_kwargs as keyword arguments to SalesforceLogin in
        addition to the mocked session and a default username.
        """
        responses.add(
            responses.POST,
            url_regex,
            body=response_body,
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
            **salesforce_login_kwargs
            )
        self.assertTrue(session_state['used'])
        self.assertEqual(session_id, tests.SESSION_ID)
        self.assertEqual(instance, urlparse(tests.SERVER_URL).netloc)

    @responses.activate
    def test_default_domain_success(self):
        """Test default domain logic and login"""
        login_args = {'password': 'password', 'security_token': 'token'}
        self._test_login_success(re.compile(r'^https://login.*$'), login_args)

    @responses.activate
    def test_custom_domain_success(self):
        """Test custom domain login"""
        login_args = {
            'password': 'password',
            'security_token': 'token',
            'domain': 'testdomain.my'
            }
        self._test_login_success(
            re.compile(r'^https://testdomain.my.salesforce.com/.*$'),
            login_args)

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
        return_mock.content = '<?xml version="1.0" ' \
                              'encoding="UTF-8"?><soapenv:Envelope ' \
                              'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                              '/envelope/" ' \
                              'xmlns:sf="urn:fault.partner.soap.sforce.com" ' \
                              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><soapenv:Fault><faultcode>INVALID_LOGIN</faultcode><faultstring>INVALID_LOGIN: Invalid username, password, security token; or user locked out.</faultstring><detail><sf:LoginFault xsi:type="sf:LoginFault"><sf:exceptionCode>INVALID_LOGIN</sf:exceptionCode><sf:exceptionMessage>Invalid username, password, security token; or user locked out.</sf:exceptionMessage></sf:LoginFault></detail></soapenv:Fault></soapenv:Body></soapenv:Envelope>'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                security_token='token',
                domain='test'
                )
        self.assertTrue(self.mockrequest.post.called)

    @responses.activate
    def test_token_login_success_with_key_file(self):
        """Test a successful JWT Token login with a key file"""
        pkey_path = Path(__file__).parent / 'sample-key.pem'
        login_args = {
            'consumer_key': '12345.abcde',
            'privatekey_file': str(pkey_path)
            }
        self._test_login_success(
            re.compile(r'^https://login.salesforce.com/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)

    @responses.activate
    def test_token_login_success_with_key(self):
        """Test a successful JWT Token login with a key from a string"""
        pkey_path = Path(__file__).parent / 'sample-key.pem'
        key = pkey_path.read_bytes().decode()

        login_args = {
            'consumer_key': '12345.abcde',
            'privatekey': key
            }
        self._test_login_success(
            re.compile(r'^https://login.salesforce.com/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)

    @responses.activate
    def test_token_login_success_with_key_bytes(self):
        """Test a successful JWT Token login with key bytes"""
        pkey_path = Path(__file__).parent / 'sample-key.pem'
        key_bytes = pkey_path.read_bytes()

        login_args = {
            'consumer_key': '12345.abcde',
            'privatekey': key_bytes
            }
        self._test_login_success(
            re.compile(r'^https://login.salesforce.com/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)

    def test_token_login_failure(self):
        """Test a failed JWT Token login"""
        return_mock = Mock()
        return_mock.status_code = 400
        # pylint: disable=line-too-long
        return_mock.content = '{"error": "invalid_client_id", ' \
                              '"error_description": "client identifier ' \
                              'invalid"}'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                consumer_key='12345.abcde',
                privatekey_file=str(Path(__file__).parent / 'sample-key.pem')
                )
        self.assertTrue(self.mockrequest.post.called)

    @responses.activate
    def test_token_login_failure_with_warning(self):
        """Test a failed JWT Token login that also produces a helful warning"""
        responses.add(
            responses.POST,
            re.compile(r'^https://login.*$'),
            # pylint: disable=line-too-long
            body='{"error": "invalid_grant", "error_description": "user '
                 'hasn\'t approved this consumer"}',
            status=400
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
        with warnings.catch_warnings(record=True) as warning:
            with self.assertRaises(SalesforceAuthenticationFailed):
                # pylint: disable=unused-variable
                session_id, instance = SalesforceLogin(
                    session=session,
                    username='foo@bar.com',
                    consumer_key='12345.abcde',
                    privatekey_file=str(
                        Path(__file__).parent / 'sample-key.pem'
                        )
                    )
            assert len(warning) >= 1
            assert issubclass(warning[-1].category, UserWarning)
            assert str(warning[-1].message) == tests.TOKEN_WARNING
        self.assertTrue(session_state['used'])

    @responses.activate
    def test_connected_app_login_success(self):
        """Test a successful connected app login with a key file"""
        login_args = {
            'password': 'password',
            'consumer_key': '12345.abcde',
            'consumer_secret': '12345.abcde'
            }
        self._test_login_success(
            re.compile(r'^https://login.salesforce.com/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)

    def test_connected_app_login_failure(self):
        """Test a failed connected app login"""
        return_mock = Mock()
        return_mock.status_code = 400
        # pylint: disable=line-too-long
        return_mock.content = '{"error": "invalid_client_id", ' \
                              '"error_description": "client identifier ' \
                              'invalid"}'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                consumer_key='12345.abcde',
                consumer_secret='12345.abcde'
                )
        self.assertTrue(self.mockrequest.post.called)

    @responses.activate
    def test_connected_app_client_credentials_login_success(self):
        """Test a successful connected app login with client credentials"""
        login_args = {
            'consumer_key': '12345.abcde',
            'consumer_secret': '12345.abcde',
            'domain': urlparse(tests.INSTANCE_URL).hostname.split(
                '.salesforce.com')[0],
            }
        self._test_login_success(
            re.compile(rf'^{tests.INSTANCE_URL}/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)
