"""Tests for simple-salesforce utility functions"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from simple_salesforce.util import getUniqueElementValueFromXmlString

class TestXMLParser(unittest.TestCase):
    """Test the XML parser utility function"""
    def test_returns_valid_value(self):
        """Test that when given the correct XML a valid response is returned"""
        result = getUniqueElementValueFromXmlString(
            '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
        self.assertEqual(result, 'bar')
