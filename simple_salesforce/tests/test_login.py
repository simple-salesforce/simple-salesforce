"""Tests for login.py"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    # Python 2.6/2.7
    from mock import Mock, patch
except ImportError:
    # Python 3
    from unittest.mock import Mock, patch

from simple_salesforce.login import SalesforceLogin, SalesforceAuthenticationFailed

class TestExceptionHandler(unittest.TestCase):
    def setUp(self):
        request_patcher = patch('simple_salesforce.login.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    def test_failure(self):
        """Test A Failed Login Response"""
        return_mock = Mock()
        return_mock.status_code = 500
        return_mock.content = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sf="urn:fault.partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Body><soapenv:Fault><faultcode>INVALID_LOGIN</faultcode><faultstring>INVALID_LOGIN: Invalid username, password, security token; or user locked out.</faultstring><detail><sf:LoginFault xsi:type="sf:LoginFault"><sf:exceptionCode>INVALID_LOGIN</sf:exceptionCode><sf:exceptionMessage>Invalid username, password, security token; or user locked out.</sf:exceptionMessage></sf:LoginFault></detail></soapenv:Fault></soapenv:Body></soapenv:Envelope>'
        self.mockrequest.post.return_value = return_mock

        with self.assertRaises(SalesforceAuthenticationFailed):
            session_id, instance = SalesforceLogin(
                username='myemail@example.com.sandbox',
                password='password',
                security_token='token',
                sandbox=True
            )
        self.assertTrue(self.mockrequest.post.called)
