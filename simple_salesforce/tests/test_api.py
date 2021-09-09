# pylint: disable-msg=C0302
"""Tests for api.py"""
import http.client as http
import re
import unittest
from collections import OrderedDict
from datetime import datetime
from unittest.mock import patch

import requests
import responses
from simple_salesforce import tests
from simple_salesforce.api import PerAppUsage, Salesforce, SFType, Usage


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
                                instance_url=tests.SERVER_URL, session=session,
                                proxies={})
            self.assertIn('ignoring proxies', mock_log.call_args[0][0])
            self.assertIs(tests.PROXIES, client.session.proxies)

    @responses.activate
    def test_api_usage_simple(self):
        """Make sure a header response is recorded"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*$'),
            body='{"example": 1}',
            adding_headers={"Sforce-Limit-Info": "api-usage=18/5000"},
            status=http.OK
            )

        client = Salesforce.__new__(Salesforce)
        client.session = requests.Session()
        client.headers = {}
        client.base_url = 'https://localhost'
        client.query('q')

        self.assertDictEqual(client.api_usage, {'api-usage': Usage(18, 5000)})

    @responses.activate
    def test_api_usage_per_app(self):
        """Make sure a header response is recorded"""

        pau = "api-usage=25/5000; per-app-api-usage=17/250(appName=sample-app)"
        responses.add(
            responses.GET,
            re.compile(r'^https://.*$'),
            body='{"example": 1}',
            adding_headers={"Sforce-Limit-Info": pau},
            status=http.OK
            )

        client = Salesforce.__new__(Salesforce)
        client.session = requests.Session()
        client.headers = {}
        client.base_url = 'https://localhost'
        client.query('q')

        self.assertDictEqual(client.api_usage,
                             {
                                 'api-usage': Usage(25, 5000),
                                 'per-app-api-usage': PerAppUsage(17, 250,
                                                                  'sample-app')
                             })

    @responses.activate
    def test_query(self):
        """Test querying generates the expected request"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/\?q=SELECT\+ID\+FROM\+Account$'),
            body='{}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query('SELECT ID FROM Account')
        self.assertEqual(result, {})

    @responses.activate
    def test_query_include_deleted(self):
        """Test querying for all records generates the expected request"""
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/queryAll/\?q=SELECT\+ID\+FROM\+Account$'),
            body='{}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query('SELECT ID FROM Account', include_deleted=True)
        self.assertEqual(result, {})

    @responses.activate
    def test_query_more_id_not_url(self):
        """
        Test fetching additional results by ID generates the expected request
        """
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/next-records-id$'),
            body='{}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query_more('next-records-id', identifier_is_url=False)
        self.assertEqual(result, {})

    @responses.activate
    def test_query_more_id_not_url_include_deleted(self):
        """
        Test fetching additional results by ID generates the expected request
        """
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/queryAll/next-records-id$'),
            body='{}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query_more(
            'next-records-id', identifier_is_url=False, include_deleted=True)
        self.assertEqual(result, {})

    @responses.activate
    def test_query_all_iter(self):
        """
        Test that we get data only once we ask for them (lazily).
        """
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/\?q=SELECT\+ID\+FROM\+Account$'),
            body='{"records": [{"ID": "1"}], "done": false, "nextRecordsUrl": '
                 '"https://example.com/query/next-records-id", "totalSize": 2}',
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/next-records-id$'),
            body='{"records": [{"ID": "2"}], "done": true, "totalSize": 2}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query_all_iter('SELECT ID FROM Account')
        self.assertEqual(next(result), OrderedDict([('ID', '1')]))
        self.assertEqual(next(result), OrderedDict([('ID', '2')]))
        with self.assertRaises(StopIteration):
            next(result)

    @responses.activate
    def test_query_all(self):
        """
        Test that we query and fetch additional result sets automatically.
        """
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/\?q=SELECT\+ID\+FROM\+Account$'),
            body='{"records": [{"ID": "1"}], "done": false, "nextRecordsUrl": '
                 '"https://example.com/query/next-records-id", "totalSize": 2}',
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/query/next-records-id$'),
            body='{"records": [{"ID": "2"}], "done": true, "totalSize": 2}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query_all('SELECT ID FROM Account')
        self.assertEqual(
            result,
            OrderedDict([('records', [
                OrderedDict([('ID', '1')]),
                OrderedDict([('ID', '2')])
                ]), ('done', True), ('totalSize', 2)]))

    @responses.activate
    def test_query_all_include_deleted(self):
        """
        Test that we query all and fetch additional result sets automatically.
        """
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/queryAll/\?q=SELECT\+ID\+FROM\+Account$'),
            body='{"records": [{"ID": "1"}], "done": false, "nextRecordsUrl": '
                 '"https://example.com/queryAll/next-records-id",'
                 '"totalSize": 2}',
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/queryAll/next-records-id$'),
            body='{"records": [{"ID": "2"}], "done": true, "totalSize": 2}',
            status=http.OK)
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.query_all('SELECT ID FROM Account',
                                  include_deleted=True)
        self.assertEqual(
            result,
            OrderedDict([('records', [
                OrderedDict([('ID', '1')]),
                OrderedDict([('ID', '2')])
                ]), ('done', True), ('totalSize', 2)]))

    @responses.activate
    def test_api_limits(self):
        """Test method for getting Salesforce organization limits"""

        responses.add(
            responses.GET,
            re.compile(r'^https://.*/limits/$'),
            json=tests.ORGANIZATION_LIMITS_RESPONSE,
            status=http.OK
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        result = client.limits()

        self.assertEqual(result, tests.ORGANIZATION_LIMITS_RESPONSE)

    @responses.activate
    @patch("simple_salesforce.metadata.SfdcMetadataApi._read_deploy_zip")
    def test_md_deploy_success(self, mock_read_zip):
        """"
        Test method for metadata deployment
        """
        #pylint: disable=unused-argument
        mock_response = '<?xml version="1.0" ' \
                        'encoding="UTF-8"?><soapenv:Envelope ' \
                        'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                        '/envelope/" ' \
                        'xmlns="http://soap.sforce.com/2006/04/metadata' \
                        '"><soapenv:Body><deployResponse><result><done' \
                        '>false</done><id>0Af3B00001CMyfASAT</id><state' \
                        '>Queued</state></result></deployResponse></soapenv' \
                        ':Body></soapenv:Envelope>'
        responses.add(
            responses.POST,
            re.compile(r'^https://.*/deployRequest'),
            body=mock_response,
            status=200
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)
        result = client.deploy("path/to/fake/zip.zip", sandbox=False)
        self.assertEqual(result.get('asyncId'), "0Af3B00001CMyfASAT")
        self.assertEqual(result.get('state'), "Queued")

    @responses.activate
    @patch("simple_salesforce.metadata.SfdcMetadataApi._read_deploy_zip")
    def test_md_deploy_failed_status_code(self, mock_read_zip):
        """"
        Test method for metadata deployment
        """
        #pylint: disable=unused-argument
        responses.add(
            responses.POST,
            re.compile(r'^https://.*'),
            body="Unrecognized Error",
            status=2599
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)
        with self.assertRaises(Exception):
            client.deploy("path/to/fake/zip.zip", sandbox=False)

    @responses.activate
    def test_check_status_pending(self):
        """"
        Test method for metadata deployment
        """
        # pylint: disable-msg=C0301
        mock_response = '<?xml version="1.0" ' \
                        'encoding="UTF-8"?><soapenv:Envelope ' \
                        'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                        '/envelope/" ' \
                        'xmlns="http://soap.sforce.com/2006/04/metadata' \
                        '"><soapenv:Body><checkDeployStatusResponse><result' \
                        '><checkOnly>true</checkOnly><createdBy' \
                        '>0053D0000052Xaq</createdBy><createdByName>User ' \
                        'User</createdByName><createdDate>2020-10-28T15:38:34' \
                        '.000Z</createdDate><details><runTestResult' \
                        '><numFailures>0</numFailures><numTestsRun>0' \
                        '</numTestsRun><totalTime>0.0</totalTime' \
                        '></runTestResult></details><done>false</done><id' \
                        '>0Af3D00001NViC1SAL</id><ignoreWarnings>false' \
                        '</ignoreWarnings><lastModifiedDate>2020-10-28T15:38' \
                        ':34.000Z</lastModifiedDate><numberComponentErrors>0' \
                        '</numberComponentErrors><numberComponentsDeployed>0' \
                        '</numberComponentsDeployed><numberComponentsTotal>0' \
                        '</numberComponentsTotal><numberTestErrors>0' \
                        '</numberTestErrors><numberTestsCompleted>0' \
                        '</numberTestsCompleted><numberTestsTotal>0' \
                        '</numberTestsTotal><rollbackOnError>true' \
                        '</rollbackOnError><runTestsEnabled>false' \
                        '</runTestsEnabled><status>Pending</status><success' \
                        '>false</success></result></checkDeployStatusResponse' \
                        '></soapenv:Body></soapenv:Envelope>'

        responses.add(
            responses.POST,
            re.compile(r'^https://.*/deployRequest/abdcefg'),
            body=mock_response,
            status=http.OK
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)

        result = client.checkDeployStatus(
            "abdcefg", sandbox=False)

        self.assertEqual(result.get('state'), "Pending")
        self.assertEqual(result.get('state_detail'), None)
        self.assertEqual(result.get('deployment_detail'), {
            'total_count': '0', 'failed_count': '0', 'deployed_count': '0',
            'errors': []
            })
        self.assertEqual(result.get('unit_test_detail'), {
            'total_count': '0', 'failed_count': '0', 'completed_count': '0',
            'errors': []
            })

    @responses.activate
    def test_check_status_success(self):
        """"
        Test method for metadata deployment
        """
        # pylint: disable-msg=C0301
        mock_response = '<?xml version="1.0" ' \
                        'encoding="UTF-8"?><soapenv:Envelope ' \
                        'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                        '/envelope/" ' \
                        'xmlns="http://soap.sforce.com/2006/04/metadata' \
                        '"><soapenv:Body><checkDeployStatusResponse><result' \
                        '><checkOnly>false</checkOnly><completedDate>2020-10' \
                        '-28T13:33:29.000Z</completedDate><createdBy' \
                        '>0053D0000052Xaq</createdBy><createdByName>User ' \
                        'User</createdByName><createdDate>2020-10-28T13:33:25' \
                        '.000Z</createdDate><details><componentSuccesses' \
                        '><changed>true</changed><componentType>ApexSettings' \
                        '</componentType><created>false</created><createdDate' \
                        '>2020-10-28T13:33:29.000Z</createdDate><deleted' \
                        '>false</deleted><fileName>shape/settings/Apex' \
                        '.settings</fileName><fullName>Apex</fullName' \
                        '><success>true</success></componentSuccesses' \
                        '><componentSuccesses><changed>true</changed' \
                        '><componentType>ChatterSettings</componentType' \
                        '><created>false</created><createdDate>2020-10-28T13' \
                        ':33:29.000Z</createdDate><deleted>false</deleted' \
                        '><fileName>shape/settings/Chatter.settings</fileName' \
                        '><fullName>Chatter</fullName><success>true</success' \
                        '></componentSuccesses><componentSuccesses><changed' \
                        '>true</changed><componentType></componentType' \
                        '><created>false</created><createdDate>2020-10-28T13' \
                        ':33:29.000Z</createdDate><deleted>false</deleted' \
                        '><fileName>shape/package.xml</fileName><fullName' \
                        '>package.xml</fullName><success>true</success' \
                        '></componentSuccesses><componentSuccesses><changed' \
                        '>true</changed><componentType>LightningExperienceSettings</componentType><created>false</created><createdDate>2020-10-28T13:33:29.000Z</createdDate><deleted>false</deleted><fileName>shape/settings/LightningExperience.settings</fileName><fullName>LightningExperience</fullName><success>true</success></componentSuccesses><componentSuccesses><changed>true</changed><componentType>LanguageSettings</componentType><created>false</created><createdDate>2020-10-28T13:33:29.000Z</createdDate><deleted>false</deleted><fileName>shape/settings/Language.settings</fileName><fullName>Language</fullName><success>true</success></componentSuccesses><runTestResult><numFailures>0</numFailures><numTestsRun>0</numTestsRun><totalTime>0.0</totalTime></runTestResult></details><done>true</done><id>0Af3D00001NVCnwSAH</id><ignoreWarnings>false</ignoreWarnings><lastModifiedDate>2020-10-28T13:33:29.000Z</lastModifiedDate><numberComponentErrors>0</numberComponentErrors><numberComponentsDeployed>4</numberComponentsDeployed><numberComponentsTotal>4</numberComponentsTotal><numberTestErrors>0</numberTestErrors><numberTestsCompleted>0</numberTestsCompleted><numberTestsTotal>0</numberTestsTotal><rollbackOnError>true</rollbackOnError><runTestsEnabled>false</runTestsEnabled><startDate>2020-10-28T13:33:26.000Z</startDate><status>Succeeded</status><success>true</success></result></checkDeployStatusResponse></soapenv:Body></soapenv:Envelope>'

        responses.add(
            responses.POST,
            re.compile(r'^https://.*/deployRequest/abdcefg'),
            body=mock_response,
            status=http.OK
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)
        result = client.checkDeployStatus(
            "abdcefg", sandbox=False)
        self.assertEqual(result.get('state'), "Succeeded")
        self.assertEqual(result.get('state_detail'), None)
        self.assertEqual(result.get('deployment_detail'), {
            'total_count': '4', 'failed_count': '0', 'deployed_count': '4',
            'errors': []
            })
        self.assertEqual(result.get('unit_test_detail'), {
            'total_count': '0', 'failed_count': '0', 'completed_count': '0',
            'errors': []
            })

    @responses.activate
    def test_check_status_payload_error(self):
        """"
        Test method for metadata deployment
        """
        # pylint: disable-msg=C0301
        mock_response = '<?xml version="1.0" ' \
                        'encoding="UTF-8"?><soapenv:Envelope ' \
                        'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                        '/envelope/" ' \
                        'xmlns="http://soap.sforce.com/2006/04/metadata' \
                        '"><soapenv:Body><checkDeployStatusResponse><result' \
                        '><checkOnly>true</checkOnly><completedDate>2020-10' \
                        '-28T13:37:48.000Z</completedDate><createdBy' \
                        '>0053D0000052Xaq</createdBy><createdByName>User ' \
                        'User</createdByName><createdDate>2020-10-28T13:37:46' \
                        '.000Z</createdDate><details><componentFailures' \
                        '><changed>false</changed><componentType' \
                        '></componentType><created>false</created' \
                        '><createdDate>2020-10-28T13:37:47.000Z</createdDate' \
                        '><deleted>false</deleted><fileName>package.xml' \
                        '</fileName><fullName>package.xml</fullName><problem' \
                        '>No package.xml ' \
                        'found</problem><problemType>Error</problemType' \
                        '><success>false</success></componentFailures' \
                        '><runTestResult><numFailures>0</numFailures' \
                        '><numTestsRun>0</numTestsRun><totalTime>0.0' \
                        '</totalTime></runTestResult></details><done>true' \
                        '</done><id>0Af3D00001NVD0TSAX</id><ignoreWarnings' \
                        '>false</ignoreWarnings><lastModifiedDate>2020-10' \
                        '-28T13:37:48.000Z</lastModifiedDate' \
                        '><numberComponentErrors>0</numberComponentErrors' \
                        '><numberComponentsDeployed>0</numberComponentsDeployed><numberComponentsTotal>0</numberComponentsTotal><numberTestErrors>0</numberTestErrors><numberTestsCompleted>0</numberTestsCompleted><numberTestsTotal>0</numberTestsTotal><rollbackOnError>true</rollbackOnError><runTestsEnabled>false</runTestsEnabled><startDate>2020-10-28T13:37:47.000Z</startDate><status>Failed</status><success>false</success></result></checkDeployStatusResponse></soapenv:Body></soapenv:Envelope>'

        responses.add(
            responses.POST,
            re.compile(r'^https://.*/deployRequest/abdcefg'),
            body=mock_response,
            status=http.OK
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)
        result = client.checkDeployStatus(
            "abdcefg", sandbox=False)
        self.assertEqual(result.get('state'), "Failed")
        self.assertEqual(result.get('state_detail'), None)
        self.assertEqual(result.get('deployment_detail'), {
            'total_count': '0', 'failed_count': '0', 'deployed_count': '0',
            'errors': [{
                'type': None, 'file': 'package.xml',
                'status': 'Error', 'message': 'No package.xml found'
                }]
            })
        self.assertEqual(result.get('unit_test_detail'), {
            'total_count': '0', 'failed_count': '0', 'completed_count': '0',
            'errors': []
            })

    @responses.activate
    def test_check_status_in_progress(self, ):
        """"
        Test method for metadata deployment
        """
        mock_response = '<?xml version="1.0" ' \
                        'encoding="UTF-8"?><soapenv:Envelope ' \
                        'xmlns:soapenv="http://schemas.xmlsoap.org/soap' \
                        '/envelope/" ' \
                        'xmlns="http://soap.sforce.com/2006/04/metadata' \
                        '"><soapenv:Body><checkDeployStatusResponse><result' \
                        '><checkOnly>false</checkOnly><createdBy' \
                        '>0053D0000052Xaq</createdBy><createdByName>User ' \
                        'User</createdByName><createdDate>2020-10-28T17:24:30' \
                        '.000Z</createdDate><details><runTestResult' \
                        '><numFailures>0</numFailures><numTestsRun>0' \
                        '</numTestsRun><totalTime>0.0</totalTime' \
                        '></runTestResult></details><done>false</done><id' \
                        '>0Af3D00001NW8mnSAD</id><ignoreWarnings>false' \
                        '</ignoreWarnings><lastModifiedDate>2020-10-28T17:37' \
                        ':08.000Z</lastModifiedDate><numberComponentErrors>0' \
                        '</numberComponentErrors><numberComponentsDeployed>2' \
                        '</numberComponentsDeployed><numberComponentsTotal>3' \
                        '</numberComponentsTotal><numberTestErrors>0' \
                        '</numberTestErrors><numberTestsCompleted>0' \
                        '</numberTestsCompleted><numberTestsTotal>0' \
                        '</numberTestsTotal><rollbackOnError>true' \
                        '</rollbackOnError><runTestsEnabled>false' \
                        '</runTestsEnabled><startDate>2020-10-28T17:24:30' \
                        '.000Z</startDate><status>InProgress</status><success' \
                        '>false</success></result></checkDeployStatusResponse' \
                        '></soapenv:Body></soapenv:Envelope>'

        responses.add(
            responses.POST,
            re.compile(r'^https://.*/deployRequest/abdcefg'),
            body=mock_response,
            status=http.OK
            )

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance=tests.INSTANCE_URL,
                            session=session)

        result = client.checkDeployStatus(
            "abdcefg", sandbox=False)
        self.assertEqual(result.get('state'), "InProgress")
        self.assertEqual(result.get('state_detail'), None)
        self.assertEqual(result.get('deployment_detail'), {
            'total_count': '3', 'failed_count': '0', 'deployed_count': '2',
            'errors': []
            })
        self.assertEqual(result.get('unit_test_detail'), {
            'total_count': '0', 'failed_count': '0', 'completed_count': '0',
            'errors': []
            })
