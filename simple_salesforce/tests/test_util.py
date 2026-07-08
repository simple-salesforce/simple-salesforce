"""Tests for simple-salesforce utility functions"""
import datetime
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

import pytz
from simple_salesforce.exceptions import (SalesforceExpiredSession,
                                          SalesforceGeneralError,
                                          SalesforceMalformedRequest,
                                          SalesforceMoreThanOneRecord,
                                          SalesforceRefusedRequest,
                                          SalesforceResourceNotFound)
from simple_salesforce.util import (date_to_iso8601, exception_handler,
                                    getUniqueElementValueFromXmlString,
                                    get_cli_session)

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

class TestUtilCli(unittest.TestCase):
    
    # 1. We mock 'shutil.which' to pretend we found the installed CLI
    @patch('shutil.which')
    # 2. We mock 'subprocess.run' to fake the execution
    @patch('subprocess.run')
    def test_get_cli_session_success(self, mock_subprocess, mock_which):
        """Test parsing valid JSON when 'sf' is found"""
        
        # A. Setup 'shutil.which' to return a fake path
        # This simulates finding the CLI at /usr/bin/sf
        mock_which.return_value = '/usr/bin/sf'

        # B. Setup 'subprocess' to return valid JSON
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            "status": 0,
            "result": {
                "accessToken": "REAL_TOKEN",
                "instanceUrl": "https://real-instance.salesforce.com"
            }
        })
        mock_subprocess.return_value = mock_result

        # C. Run the function
        token, url = get_cli_session()

        # D. Verify Logic
        self.assertEqual(token, "REAL_TOKEN")
        
        # Verify it verified the existence of 'sf' first
        mock_which.assert_called_with('sf')
        
        # Verify it used the path returned by shutil (/usr/bin/sf)
        args, _ = mock_subprocess.call_args
        self.assertEqual(args[0][0], '/usr/bin/sf')

    @patch('shutil.which')
    def test_cli_not_found(self, mock_which):
        """Test that we raise ValueError if neither sf nor sfdx is found"""
        
        # Setup: Return None for both checks
        mock_which.return_value = None
        
        # Verify it raises ValueError
        with self.assertRaises(ValueError) as context:
            get_cli_session()
        
        self.assertIn("Salesforce CLI not found", str(context.exception))

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_get_cli_session_with_alias(self, mock_subprocess, mock_which):
        # 1. Setup
        mock_which.return_value = '/bin/sf'
        mock_subprocess.return_value.stdout = '{"result": {"accessToken": "x", "instanceUrl": "y"}}'

        # 2. This runs the function WITH an argument, forcing it into the 'if target_org' block
        get_cli_session(target_org="MyAlias")
        
        # 3. Verify the command list actually grew larger
        args, _ = mock_subprocess.call_args
        self.assertIn('--target-org', args[0])
    
    @patch('shutil.which')
    @patch('subprocess.run')
    def test_get_cli_runtime_error(self, mock_subprocess, mock_which):
        """Test the specific block: except subprocess.CalledProcessError"""
        
        # 1. CRITICAL: We must pretend 'sf' exists so the code proceeds to the try/except block
        mock_which.return_value = '/bin/sf'

        # 2. CRITICAL: We force subprocess to RAISE an error (simulating a crash)
        # We simulate a "Session Expired" error from the CLI
        # args: (returncode, cmd, output, stderr)
        fake_error = subprocess.CalledProcessError(1, ['sf'], output="", stderr="Session expired")
        mock_subprocess.side_effect = fake_error

        # 3. VERIFY
        # Your code catches CalledProcessError and raises ValueError
        # So we assert that ValueError is raised
        with self.assertRaises(ValueError) as context:
            get_cli_session()
            
        # 4. Check if we caught the error message
        self.assertIn("Session expired", str(context.exception))