"""Test for bulk.py"""
import http.client as http
import re
import unittest
from unittest.mock import patch

import requests
import responses
from simple_salesforce import tests
from simple_salesforce.api import Salesforce
from simple_salesforce.exceptions import SalesforceGeneralError


class TestSFBulkHandler(unittest.TestCase):
    """Test for SFBulkHandler"""

    def test_bulk_handler(self):
        """Test bulk handler creation"""
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        bulk_handler = client.bulk

        self.assertIs(tests.SESSION_ID, bulk_handler.session_id)
        self.assertIs(client.bulk_url, bulk_handler.bulk_url)
        self.assertEqual(tests.BULK_HEADERS, bulk_handler.headers)


class TestSFBulkType(unittest.TestCase):
    """Test SFBulkType"""

    def setUp(self):
        request_patcher = patch('simple_salesforce.api.requests')
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)
        self.expected = [
            {
                "success": True,
                "created": True,
                "id": "001xx000003DHP0AAO",
                "errors": []
            },
            {
                "success": True,
                "created": True,
                "id": "001xx000003DHP1AAO",
                "errors": []
            }
        ]
        self.expected_query = [
            {"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",
             "Email": "contact1@example.com",
             "FirstName": "Bob", "LastName": "x"},
            {"Id": "001xx000003DHP1AAO", "AccountId": "ID-24",
             "Email": "contact2@example.com",
             "FirstName": "Alice", "LastName": "y"},
            {"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",
             "Email": "contact1@example.com",
             "FirstName": "Bob", "LastName": "x"},
            {"Id": "001xx000003DHP1AAO", "AccountId": "ID-24",
             "Email": "contact2@example.com",
             "FirstName": "Alice", "LastName": "y"}
        ]

    def test_bulk_type(self):
        """Test bulk type creation"""
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact
        self.assertIs('Contact', contact.object_name)
        self.assertIs(client.bulk_url, contact.bulk_url)
        self.assertEqual(tests.BULK_HEADERS, contact.headers)

    @responses.activate
    def test_delete(self):
        """Test bulk delete records"""
        operation = 'delete'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='[{"success": true,"created": true,"id": "001xx000003DHP0AAO",'
            '"errors": []},{"success": true,"created": true,'
            '"id": "001xx000003DHP1AAO","errors": []}]',
            status=http.OK
        )
        data = [{
            'id': 'ID-1',
        }, {
            'id': 'ID-2',
        }]
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.delete(data)
        self.assertEqual(self.expected, contact)

    @responses.activate
    def test_insert(self):
        """Test bulk insert records"""
        operation = 'insert'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='[{"success": true,"created": true,"id": "001xx000003DHP0AAO",'
            '"errors": []},{"success": true,"created": true,'
            '"id": "001xx000003DHP1AAO","errors": []}]',
            status=http.OK
        )

        data = [{
            'AccountId': 'ID-1',
            'Email': 'contact1@example.com',
            'FirstName': 'Bob',
            'LastName': 'x'
        }, {
            'AccountId': 'ID-2',
            'Email': 'contact2@example.com',
            'FirstName': 'Alice',
            'LastName': 'y'
        }]
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.insert(data)
        self.assertEqual(self.expected, contact)

    @responses.activate
    def test_upsert(self):
        """Test bulk upsert records"""
        operation = 'upsert'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='[{"success": true,"created": true,"id": "001xx000003DHP0AAO",'
            '"errors": []},{"success": true,"created": true,'
            '"id": "001xx000003DHP1AAO","errors": []}]',
            status=http.OK
        )

        data = [{
            'Custom_Id__c': 'CustomID1',
            'AccountId': 'ID-13',
            'Email': 'contact1@example.com',
            'FirstName': 'Bob',
            'LastName': 'x'
        }, {
            'Custom_Id__c': 'CustomID2',
            'AccountId': 'ID-24',
            'Email': 'contact2@example.com',
            'FirstName': 'Alice',
            'LastName': 'y'
        }]
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.upsert(data, 'Custom_Id__c')
        self.assertEqual(self.expected, contact)

    @responses.activate
    def test_update(self):
        """Test bulk update records"""
        operation = 'upsert'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='[{"success": true,"created": true,"id": "001xx000003DHP0AAO",'
            '"errors": []},{"success": true,"created": true,'
            '"id": "001xx000003DHP1AAO","errors": []}]',
            status=http.OK
        )

        data = [{
            'Id': '001xx000003DHP0AAO',
            'AccountId': 'ID-13',
            'Email': 'contact1@example.com',
            'FirstName': 'Bob',
            'LastName': 'x'
        }, {
            'Id': '001xx000003DHP1AAO',
            'AccountId': 'ID-24',
            'Email': 'contact2@example.com',
            'FirstName': 'Alice',
            'LastName': 'y'
        }]
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.update(data)
        self.assertEqual(self.expected, contact)

    @responses.activate
    def test_query(self):
        """Test bulk query records"""
        operation = 'query'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='["752x000000000F1","752x000000000F2"]',
            status=http.OK
        )

        responses.add(
            responses.GET,
            re.compile(r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
            /752x000000000F1$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
                /752x000000000F2$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )

        data = 'SELECT Id,AccountId,Email,FirstName,LastName FROM Contact'
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.query(data)
        self.assertEqual(self.expected_query, contact)


    @responses.activate
    def test_query_fail(self):
        """Test bulk query records failure"""
        operation = 'query'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Failed",'
            '"stateMessage": "InvalidBatch : Failed to process query"}',
            status=http.OK
        )

        data = 'SELECT ASDFASfgsds FROM Contact'
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        self.assertRaises(SalesforceGeneralError,
                          client.bulk.Contact.query, data)

    @responses.activate
    def test_query_lazy(self):
        """Test bulk query records"""
        operation = 'query'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='["752x000000000F1","752x000000000F2"]',
            status=http.OK
        )

        responses.add(
            responses.GET,
            re.compile(r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
            /752x000000000F1$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
                /752x000000000F2$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )

        data = 'SELECT Id,AccountId,Email,FirstName,LastName FROM Contact'
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        contact = []
        for list_results in client.bulk.Contact.query(data, True):
            contact.extend(list_results)

        self.assertEqual(self.expected_query, contact)

    @responses.activate
    def test_query_all(self):
        """Test bulk queryAll records"""
        operation = 'queryAll'
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job$'),
            body='{"apiVersion": 42.0, "concurrencyMode": "Parallel",'
            '"contentType": "JSON","id": "Job-1","object": "Contact",'
            '"operation": "%s","state": "Open"}' % operation,
            status=http.OK)
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1/batch$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Queued"}',
            status=http.OK
        )
        responses.add(
            responses.POST,
            re.compile(r'^https://[^/job].*/job/Job-1$'),
            body='{"apiVersion" : 42.0, "concurrencyMode" : "Parallel",'
            '"contentType" : "JSON","id" : "Job-1","object" : "Contact",'
            '"operation" : "%s","state" : "Closed"}' % operation,
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "InProgress"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r'^https://[^/job].*/job/Job-1/batch/Batch-1$'),
            body='{"id": "Batch-1","jobId": "Job-1","state": "Completed"}',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r'^https://[^/job].*/job/Job-1/batch/Batch-1/result$'),
            body='["752x000000000F1","752x000000000F2"]',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
            /752x000000000F1$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )
        responses.add(
            responses.GET,
            re.compile(
                r"""^https://[^/job].*/job/Job-1/batch/Batch-1/result
                /752x000000000F2$""", re.X),
            body='[{"Id": "001xx000003DHP0AAO", "AccountId": "ID-13",'
            '"Email": "contact1@example.com","FirstName": "Bob",'
            '"LastName": "x"},{"Id": "001xx000003DHP1AAO",'
            '"AccountId": "ID-24","Email": "contact2@example.com",'
            '"FirstName": "Alice","LastName": "y"}]',
            status=http.OK
        )

        data = 'SELECT Id,AccountId,Email,FirstName,LastName FROM Contact'
        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)
        contact = client.bulk.Contact.query_all(data)
        self.assertEqual(self.expected_query, contact)
