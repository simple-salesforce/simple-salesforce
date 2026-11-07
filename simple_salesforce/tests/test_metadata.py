"""Tests for the Metadata SOAP transport."""

import unittest
from unittest.mock import patch

import requests
import responses

from simple_salesforce.api import Salesforce


DESCRIBE_METADATA_RESPONSE = (
    '<soapenv:Envelope '
    'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
    'xmlns="http://soap.sforce.com/2006/04/metadata">'
    '<soapenv:Body><describeMetadataResponse><result>'
    '<organizationNamespace>example</organizationNamespace>'
    '<partialSaveAllowed>true</partialSaveAllowed>'
    '<testRequired>false</testRequired>'
    '</result></describeMetadataResponse></soapenv:Body>'
    '</soapenv:Envelope>'
)


class TestMetadataSession(unittest.TestCase):
    """Metadata calls must retain the Salesforce HTTP session configuration."""

    def mock_metadata_response(self, client):
        """Return a local SOAP response without contacting Salesforce."""
        responses.add(
            responses.POST,
            client.metadata_url,
            content_type='text/xml',
            body=DESCRIBE_METADATA_RESPONSE,
        )

    @responses.activate
    def test_describe_metadata_uses_configured_session(self):
        """Retain the supplied session's TLS, proxy and header settings."""
        session = requests.Session()
        session.verify = '/test-only/organization-ca.pem'
        session.cert = ('/test-only/client.pem', '/test-only/client.key')
        session.proxies = {'https': 'http://test-only-proxy.invalid:8080'}
        session.headers['X-Custom-Session'] = 'metadata-session'
        client = Salesforce(
            session_id='test-token',
            instance_url='https://example.my.salesforce.com',
            session=session,
        )
        self.mock_metadata_response(client)

        metadata = client.mdapi
        with patch.object(session, 'send', wraps=session.send) as send:
            result = metadata.describe_metadata()

        self.assertEqual(result.organizationNamespace, 'example')
        send.assert_called_once()
        request = send.call_args.args[0]
        options = send.call_args.kwargs
        self.assertEqual(
            request.headers['X-Custom-Session'], 'metadata-session'
        )
        self.assertEqual(options['verify'], session.verify)
        self.assertEqual(options['cert'], session.cert)
        self.assertEqual(options['proxies']['https'], session.proxies['https'])
        self.assertIn(
            b'<ns0:sessionId>test-token</ns0:sessionId>', request.body
        )

    @responses.activate
    def test_describe_metadata_uses_default_session_headers(self):
        """Share changes to the default Salesforce session with SOAP calls."""
        client = Salesforce(
            session_id='test-token',
            instance_url='https://example.my.salesforce.com',
        )
        client.session.headers['X-Custom-Session'] = 'default-session'
        self.mock_metadata_response(client)

        result = client.mdapi.describe_metadata()

        self.assertEqual(result.organizationNamespace, 'example')
        self.assertEqual(
            responses.calls[0].request.headers['X-Custom-Session'],
            'default-session',
        )
