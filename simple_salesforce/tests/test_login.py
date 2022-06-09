"""Tests for login.py"""

import http.client as http
import os
import re
import unittest
import warnings
from unittest.mock import Mock, patch
from urllib.parse import urlparse

import requests
import responses
from simple_salesforce import tests
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from simple_salesforce.login import SalesforceLogin


class TestCreateInstance(unittest.TestCase):
    """
    Test for the Salesforce SF Instance
    These tests are mainly concerned with the the values passed in to the SF Class
    when instantiated. We want to make sure that an appropiate exception is raised if
    if incorrect login parameters are provided. 
    """

    # For these tests, we can patch the login methods uses for each one
    # We are not concerened with the login response, but what happens
    # when different parameters are provided for login, both valid and invalid 

    # Adding these tests will make sure 

    @patch('simple_salesforce.login.soap_login')
    def test_username_password_token(self, mock_login):
        "Valid user, pass, and token for soap login. Domain is optional."

        mock_login.return_value = ("1234", "https://na15.salesforce.com")
        
        # Should not raise an exception
        Salesforce(username="user", password="pass", security_token="token")

    @patch('simple_salesforce.login.soap_login')
    def test_username_password_missing_token(self, mock_login):
        "Valid user, pass with missing token for soap login"

        mock_login.return_value = ("1234", "https://na15.salesforce.com")
        
        # Should raise a value error since the all 3 username, password, and token are required
        self.assertRaises(ValueError,  Salesforce, username="user", password="pass")

    @patch('simple_salesforce.login.soap_login')
    def test_username_password_invalid_token(self, mock_login):
        "Valid user, pass with invalid token as int for soap login"

        mock_login.return_value = ("1234", "https://na15.salesforce.com")
        
        # Should raise a value error since the all 3 username, password, and token are required
        # and all should be string values 
        self.assertRaises(ValueError,  Salesforce, username="user", password="pass", security_token=123)


    @patch('simple_salesforce.login.token_login')
    def test_username_consumerkey_privatekey(self, mock_login):
        "Valid user, consumer key and private key"

        mock_login.return_value = ("1234", "https://na15.salesforce.com")

        # Should pass and not raise exception since all parameters are provided in correct format 
        Salesforce(username="user", consumer_key="16ed2757debf646833e8ce6c1fb9594841b167f659b8163c820ea0522924d6ba", privatekey="feae1c8ed273bff90e581e9aca3008e8024ba4cd4605c222c8b658cdb2a9dcbb")


    def test_empty(self):
        "No login parameters provided"

        try:
            # Should raise exception for no paramaters provided
            self.assertRaises(ValueError, Salesforce()) 
        except ValueError:
            pass

    

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

    @responses.activate
    def test_token_login_success_with_key_file(self):
        """Test a successful JWT Token login with a key file"""
        pkey_file = os.path.join(os.path.dirname(__file__), 'sample-key.pem')
        login_args = {
            'consumer_key': '12345.abcde',
            'privatekey_file': pkey_file
        }
        self._test_login_success(
            re.compile(r'^https://login.salesforce.com/.*$'), login_args,
            response_body=tests.TOKEN_LOGIN_RESPONSE_SUCCESS)

    @responses.activate
    def test_token_login_success_with_key(self):
        """Test a successful JWT Token login with a key from a string"""
        pkey_file = os.path.join(os.path.dirname(__file__), 'sample-key.pem')
        with open(pkey_file, 'rb') as key_file:
            key = key_file.read().decode("utf-8")

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
        pkey_file = os.path.join(os.path.dirname(__file__), 'sample-key.pem')
        with open(pkey_file, 'rb') as key:
            key_bytes = key.read()

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
        return_mock.content = '{"error": "invalid_client_id", "error_description": "client identifier invalid"}'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            SalesforceLogin(
                username='myemail@example.com.sandbox',
                consumer_key='12345.abcde',
                privatekey_file=os.path.join(
                    os.path.dirname(__file__), 'sample-key.pem'
                )
            )
        self.assertTrue(self.mockrequest.post.called)

    @responses.activate
    def test_token_login_failure_with_warning(self):
        """Test a failed JWT Token login that also produces a helful warning"""
        responses.add(
            responses.POST,
            re.compile(r'^https://login.*$'),
            # pylint: disable=line-too-long
            body='{"error": "invalid_grant", "error_description": "user hasn\'t approved this consumer"}',
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
                    privatekey_file=os.path.join(
                        os.path.dirname(__file__), 'sample-key.pem'
                    )
                )
            assert len(warning) >= 1
            assert issubclass(warning[-1].category, UserWarning)
            assert str(warning[-1].message) == tests.TOKEN_WARNING
        self.assertTrue(session_state['used'])
