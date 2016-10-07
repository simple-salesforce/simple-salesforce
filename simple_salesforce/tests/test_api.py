"""Tests for api.py"""

import re
from datetime import datetime
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
    SalesforceGeneralError,
    SFType
)


def _create_sf_type(
    object_name='Case',
    session_id='5',
    sf_instance='my.salesforce.com'
):
    """Creates SFType instances"""
    return SFType(
        object_name=object_name,
        session_id=session_id,
        sf_instance=sf_instance,
        session=requests.Session()
    )


class TestSFType(unittest.TestCase):
    """Tests for the SFType instance"""
    def setUp(self):
        request_patcher = patch('simple_salesforce.api.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)

    @responses.activate
    def test_metadata_with_additional_request_headers(self):
        """Ensure custom headers are used for metadata requests"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.metadata(
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_metadata_without_additional_request_headers(self):
        """Ensure metadata requests without additional headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()

        self.assertEqual(sf_type.metadata(), {})

    @responses.activate
    def test_describe_with_additional_request_headers(self):
        """Ensure custom headers are used for describe requests"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/describe$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.describe(
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_describe_without_additional_request_headers(self):
        """Ensure describe requests without additional headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/describe$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()

        self.assertEqual(sf_type.describe(), {})

    @responses.activate
    def test_describe_layout_with_additional_request_headers(self):
        """Ensure custom headers are used for describe_layout requests"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/describe/layouts/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.describe_layout(
            record_id='444',
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_describe_layout_without_additional_request_headers(self):
        """Ensure describe_layout requests without additional headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/describe/layouts/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()

        self.assertEqual(sf_type.describe_layout(record_id='444'), {})

    @responses.activate
    def test_get_with_additional_request_headers(self):
        """Ensure custom headers are used for get requests"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.get(
            record_id='444',
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_get_without_additional_request_headers(self):
        """Ensure get requests without additional headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()

        self.assertEqual(sf_type.get(record_id='444'), {})

    @responses.activate
    def test_get_by_custom_id_with_additional_request_headers(self):
        """Ensure custom headers are used for get_by_custom_id requests"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/some-field/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.get_by_custom_id(
            custom_id_field='some-field',
            custom_id='444',
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_get_by_custom_id_without_additional_request_headers(self):
        """Ensure get_by_custom_id requests without additional headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/some-field/444$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.get_by_custom_id(
            custom_id_field='some-field',
            custom_id='444'
        )

        self.assertEqual(result, {})

    @responses.activate
    def test_create_with_additional_request_headers(self):
        """Ensure custom headers are used for create requests"""
        responses.add(
            responses.POST,
            re.compile(r'^https://.*/Case/$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.create(
            data={'some': 'data'},
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_create_without_additional_request_headers(self):
        """Ensure create requests without additional headers"""
        responses.add(
            responses.POST,
            re.compile(r'^https://.*/Case/$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.create(data={'some': 'data'})

        self.assertEqual(result, {})

    @responses.activate
    def test_update_with_additional_request_headers(self):
        """Ensure custom headers are used for updates"""
        responses.add(
            responses.PATCH,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.update(
            record_id='some-case-id',
            data={'some': 'data'},
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, http.OK)

    @responses.activate
    def test_update_without_additional_request_headers(self):
        """Ensure updates work without custom headers"""
        responses.add(
            responses.PATCH,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.update(
            record_id='some-case-id',
            data={'some': 'data'}
        )

        self.assertEqual(result, http.OK)

    @responses.activate
    def test_upsert_with_additional_request_headers(self):
        """Ensure custom headers are used for upserts"""
        responses.add(
            responses.PATCH,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.upsert(
            record_id='some-case-id',
            data={'some': 'data'},
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, http.OK)

    @responses.activate
    def test_upsert_without_additional_request_headers(self):
        """Ensure upserts work without custom headers"""
        responses.add(
            responses.PATCH,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.upsert(
            record_id='some-case-id',
            data={'some': 'data'}
        )

        self.assertEqual(result, http.OK)

    @responses.activate
    def test_delete_with_additional_request_headers(self):
        """Ensure custom headers are used for deletes"""
        responses.add(
            responses.DELETE,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.delete(
            record_id='some-case-id',
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, http.OK)

    @responses.activate
    def test_delete_without_additional_request_headers(self):
        """Ensure deletes work without custom headers"""
        responses.add(
            responses.DELETE,
            re.compile(r'^https://.*/Case/some-case-id$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.delete(record_id='some-case-id')

        self.assertEqual(result, http.OK)

    @responses.activate
    def test_deleted_with_additional_request_headers(self):
        """Ensure custom headers are used for deleted"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/deleted/\?start=.+&end=.+$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.deleted(
            start=datetime.now(), end=datetime.now(),
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_deleted_without_additional_request_headers(self):
        """Ensure deleted works without custom headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/deleted/\?start=.+&end=.+$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.deleted(
            start=datetime.now(), end=datetime.now())

        self.assertEqual(result, {})

    @responses.activate
    def test_updated_with_additional_request_headers(self):
        """Ensure custom headers are used for updated"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/updated/\?start=.+&end=.+$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.updated(
            start=datetime.now(), end=datetime.now(),
            headers={'Sforce-Auto-Assign': 'FALSE'}
        )

        request_headers = responses.calls[0].request.headers
        additional_request_header = request_headers['Sforce-Auto-Assign']
        self.assertEqual(additional_request_header, 'FALSE')
        self.assertEqual(result, {})

    @responses.activate
    def test_updated_without_additional_request_headers(self):
        """Ensure updated works without custom headers"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/Case/updated/\?start=.+&end=.+$'),
            body='{}',
            status=http.OK
        )

        sf_type = _create_sf_type()
        result = sf_type.updated(
            start=datetime.now(), end=datetime.now())

        self.assertEqual(result, {})


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
        self.assertEqual(session, client.session)

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

    def test_shared_session_to_sftype(self):
        """Test Salesforce and SFType instances share default `Session`"""
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL)

        self.assertIs(client.session, client.Contact.session)

    def test_shared_custom_session_to_sftype(self):
        """Test Salesforce and SFType instances share custom `Session`"""
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        self.assertIs(session, client.session)
        self.assertIs(session, client.Contact.session)

    def test_proxies_inherited_default(self):
        """Test Salesforce and SFType use same proxies"""
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        self.assertIs(session.proxies, client.session.proxies)
        self.assertIs(session.proxies, client.Contact.session.proxies)

    def test_proxies_inherited_set_on_session(self):
        """Test Salesforce and SFType use same custom proxies"""
        session = requests.Session()
        session.proxies = tests.PROXIES
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        self.assertIs(tests.PROXIES, client.session.proxies)
        self.assertIs(tests.PROXIES, client.Contact.session.proxies)

    def test_proxies_ignored(self):
        """Test overridden proxies are ignored"""
        session = requests.Session()
        session.proxies = tests.PROXIES

        with patch('simple_salesforce.api.logger.warning') as mock_log:
            client = Salesforce(session_id=tests.SESSION_ID,
                instance_url=tests.SERVER_URL, session=session, proxies={})
            self.assertIn('ignoring proxies', mock_log.call_args[0][0])
            self.assertIs(tests.PROXIES, client.session.proxies)


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
