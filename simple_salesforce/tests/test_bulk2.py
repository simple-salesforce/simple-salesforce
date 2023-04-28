"""Test for bulk2.py"""
import csv
import http.client as http
import json
import os
import re
import tempfile
import textwrap
import unittest
from contextlib import contextmanager
from functools import partial
from unittest.mock import patch

import requests
import responses

from simple_salesforce import tests
from simple_salesforce.api import Salesforce
from simple_salesforce.bulk2 import JobState, Operation

# pylint: disable=line-too-long,missing-docstring

to_body = partial(json.dumps, ensure_ascii=False)


@contextmanager
def to_csv_file(data):
    """Create a temporary csv file from a list of dicts, delete it when done."""
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        writer = csv.DictWriter(temp_file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        temp_file.flush()
        yield temp_file.name
    finally:
        if temp_file is not None:
            os.remove(temp_file.name)


@contextmanager
def temp_csv_file():
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        yield temp_file.name
    finally:
        if temp_file is not None:
            os.remove(temp_file.name)


class TestSFBulk2Handler(unittest.TestCase):
    """Test for SFBulkHandler"""

    def test_bulk2_handler(self):
        """Test bulk2 handler creation"""
        session = requests.Session()
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=session,
        )
        bulk2_handler = client.bulk2

        self.assertIs(tests.SESSION_ID, bulk2_handler.session_id)
        self.assertIs(client.bulk2_url, bulk2_handler.bulk2_url)
        self.assertEqual(tests.BULKv2_HEADERS, bulk2_handler.headers)


def ingest_responses(operation, processed, failed=0):
    """Mock responses for bulk2 ingest jobs"""
    responses.add(
        responses.POST,
        re.compile(r"^https://.*/jobs/ingest$"),
        body=to_body(
            {
                "apiVersion": 52.0,
                "columnDelimiter": "COMMA",
                "concurrencyMode": "Parallel",
                "contentType": "CSV",
                "id": "Job-1",
                "jobType": "V2Ingest",
                "lineEnding": "LF",
                "object": "Contact",
                "operation": operation,
                "state": JobState.open,
            }
        ),
        status=http.OK,
    )
    responses.add(
        responses.PUT,
        re.compile(r"^https://.*/jobs/ingest/Job-1/batches$"),
        body="",
        status=http.CREATED,
    )
    responses.add(
        responses.PATCH,
        re.compile(r"^https://.*/jobs/ingest/Job-1$"),
        body=to_body(
            {
                "apiVersion": 52.0,
                "columnDelimiter": "COMMA",
                "concurrencyMode": "Parallel",
                "contentType": "CSV",
                "id": "Job-1",
                "jobType": "V2Ingest",
                "lineEnding": "LF",
                "object": "Contact",
                "operation": operation,
                "state": JobState.upload_complete,
            }
        ),
        status=http.OK,
    )
    responses.add(
        responses.GET,
        re.compile(r"^https://.*/jobs/ingest/Job-1$"),
        body=to_body(
            {
                "apiVersion": 52.0,
                "columnDelimiter": "COMMA",
                "concurrencyMode": "Parallel",
                "contentType": "CSV",
                "id": "Job-1",
                "jobType": "V2Ingest",
                "lineEnding": "LF",
                "object": "Contact",
                "operation": operation,
                "state": JobState.in_progress,
            }
        ),
        status=http.OK,
    )
    responses.add(
        responses.GET,
        re.compile(r"^https://.*/jobs/ingest/Job-1$"),
        body=to_body(
            {
                "apiVersion": 52.0,
                "columnDelimiter": "COMMA",
                "concurrencyMode": "Parallel",
                "contentType": "CSV",
                "id": "Job-1",
                "jobType": "V2Ingest",
                "lineEnding": "LF",
                "numberRecordsFailed": failed,
                "numberRecordsProcessed": processed,
                "object": "Contact",
                "operation": operation,
                "state": JobState.job_complete,
            }
        ),
    )


def ingest_data(operation, data, **kwargs):
    """Upload data into Salesforce"""
    operation = (
        "hard_delete" if operation == Operation.hard_delete else operation
    )
    with to_csv_file(data) as csv_file:
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        results = getattr(client.bulk2.Contact, operation)(csv_file, **kwargs)
    return results


class TestSFBulk2Type(unittest.TestCase):
    """Test SFBulk2Type"""

    def setUp(self):
        request_patcher = patch("simple_salesforce.api.requests")
        self.mockrequest = request_patcher.start()
        self.addCleanup(request_patcher.stop)
        self.expected_results = [
            {
                "numberRecordsFailed": 0,
                "numberRecordsProcessed": 2,
                "numberRecordsTotal": 2,
                "job_id": "Job-1",
            }
        ]
        self.expected_query = [
            textwrap.dedent(
                """
                "Id","AccountId","Email","FirstName","LastName"
                "001xx000003DHP0AAO","ID-13","contact1@example.com","Bob","x"
                "001xx000003DHP1AAO","ID-24","contact2@example.com","Alice","y"
                "001xx000003DHP0AAO","ID-13","contact1@example.com","Bob","x"
                "001xx000003DHP1AAO","ID-24","contact2@example.com","Alice","y"
                """
            )
        ]
        self.insert_data = [
            {
                "Custom_Id__c": "CustomID1",
                "AccountId": "ID-13",
                "Email": "contact1@example.com",
                "FirstName": "Bob",
                "LastName": "x",
            },
            {
                "Custom_Id__c": "CustomID2",
                "AccountId": "ID-24",
                "Email": "contact2@example.com",
                "FirstName": "Alice",
                "LastName": "y",
            },
        ]
        self.upsert_data = [
            {
                "Custom_Id__c": "CustomID1",
                "LastName": "X",
            },
            {
                "Custom_Id__c": "CustomID2",
                "LastName": "Y",
            },
        ]
        self.delete_data = [
            {"Id": "a011s00000DTU9zAAH"},
            {"Id": "a011s00000DTUA0AAP"},
        ]

    def test_bulk2_type(self):
        """Test bulk2 type creation"""
        session = requests.Session()
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=session,
        )
        contact = client.bulk2.Contact
        self.assertIs("Contact", contact.object_name)
        self.assertIs(client.bulk2_url, contact.bulk2_url)
        self.assertEqual(tests.BULKv2_HEADERS, contact.headers)

    @responses.activate
    def test_insert(self):
        """Test bulk2 insert records"""
        operation = Operation.insert
        total = len(self.insert_data)
        ingest_responses(operation, processed=total, failed=0)
        results = ingest_data(operation, self.insert_data)
        self.assertEqual(self.expected_results, results)

        responses.add(
            responses.GET,
            re.compile(r"^https://.*/jobs/ingest/Job-1/successfulResults$"),
            body=textwrap.dedent(
                """
                "sf__Id","sf__Created","Custom_Id__c","AccountId","Email","FirstName","LastName"
                "a011s00000DML8XAAX","true","CustomID1","ID-13","contact1@example.com","Bob","x"
                "a011s00000DML8YAAX","true","CustomID2","ID-24","contact2@example.com","Alice","y"
                """
            ),
            status=http.OK,
        )
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        results = client.bulk2.Contact.get_successful_records("Job-1")
        self.assertEqual(
            textwrap.dedent(
                """
                "sf__Id","sf__Created","Custom_Id__c","AccountId","Email","FirstName","LastName"
                "a011s00000DML8XAAX","true","CustomID1","ID-13","contact1@example.com","Bob","x"
                "a011s00000DML8YAAX","true","CustomID2","ID-24","contact2@example.com","Alice","y"
            """
            ),
            results,
        )

    @responses.activate
    def test_upsert(self):
        """Test bulk2 upsert records"""
        operation = Operation.upsert
        total = len(self.upsert_data)
        ingest_responses(operation, processed=total, failed=0)
        results = ingest_data(
            operation, self.upsert_data, external_id_field="Custom_Id__c"
        )
        self.assertEqual(self.expected_results, results)

        responses.add(
            responses.GET,
            re.compile(r"^https://.*/jobs/ingest/Job-1/successfulResults$"),
            body=textwrap.dedent(
                """
                "sf__Id","sf__Created","Custom_Id__c","LastName"
                "a011s00000DML8XAAX","false","CustomID1","X"
                "a011s00000DML8YAAX","false","CustomID2","Y"
                """
            ),
            status=http.OK,
        )
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        results = client.bulk2.Contact.get_successful_records("Job-1")
        self.assertEqual(
            textwrap.dedent(
                """
                 "sf__Id","sf__Created","Custom_Id__c","LastName"
                 "a011s00000DML8XAAX","false","CustomID1","X"
                 "a011s00000DML8YAAX","false","CustomID2","Y"
                """
            ),
            results,
        )

    @responses.activate
    def test_hard_delete(self):
        """Test bulk2 hardDelete records"""
        operation = Operation.hard_delete
        total = len(self.delete_data)
        ingest_responses(operation, processed=total, failed=0)
        results = ingest_data(operation, self.delete_data)
        self.assertEqual(self.expected_results, results)

        responses.add(
            responses.GET,
            re.compile(r"^https://.*/jobs/ingest/Job-1/successfulResults$"),
            body=textwrap.dedent(
                """
                "sf__Id","sf__Created","Id"
                "a011s00000DTU9zAAH","false","a011s00000DTU9zAAH"
                "a011s00000DTUA0AAP","false","a011s00000DTUA0AAP"
                """
            ),
            status=http.OK,
        )
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        results = client.bulk2.Contact.get_successful_records("Job-1")
        self.assertEqual(
            textwrap.dedent(
                """
                "sf__Id","sf__Created","Id"
                "a011s00000DTU9zAAH","false","a011s00000DTU9zAAH"
                "a011s00000DTUA0AAP","false","a011s00000DTUA0AAP"
                """
            ),
            results,
        )

    @responses.activate
    def test_query(self):
        """Test bulk2 query records"""
        operation = Operation.query
        responses.add(
            responses.POST,
            re.compile(r"^https://.*/jobs/query$"),
            body=to_body(
                {
                    "apiVersion": 52.0,
                    "columnDelimiter": "COMMA",
                    "concurrencyMode": "Parallel",
                    "contentType": "CSV",
                    "id": "Job-1",
                    "lineEnding": "LF",
                    "object": "Contact",
                    "operation": operation,
                    "state": JobState.upload_complete,
                }
            ),
            status=http.OK,
        )
        responses.add(
            responses.GET,
            re.compile(r"^https://.*/jobs/query/Job-1$"),
            body=to_body(
                {
                    "apiVersion": 52.0,
                    "columnDelimiter": "COMMA",
                    "concurrencyMode": "Parallel",
                    "contentType": "CSV",
                    "id": "Job-1",
                    "jobType": "V2Query",
                    "lineEnding": "LF",
                    "numberRecordsProcessed": 4,
                    "object": "Contact",
                    "operation": operation,
                    "state": JobState.in_progress,
                }
            ),
            status=http.OK,
        )
        responses.add(
            responses.GET,
            re.compile(r"^https://.*/jobs/query/Job-1$"),
            body=to_body(
                {
                    "apiVersion": 52.0,
                    "columnDelimiter": "COMMA",
                    "concurrencyMode": "Parallel",
                    "contentType": "CSV",
                    "id": "Job-1",
                    "jobType": "V2Query",
                    "lineEnding": "LF",
                    "numberRecordsProcessed": 4,
                    "object": "Contact",
                    "operation": operation,
                    "state": JobState.job_complete,
                }
            ),
            status=http.OK,
        )
        responses.add(
            responses.GET,
            re.compile(
                r"^https://.*/jobs/query/Job-1/results\?maxRecords=\d+$"
            ),
            body=textwrap.dedent(
                """
                "Id","AccountId","Email","FirstName","LastName"
                "001xx000003DHP0AAO","ID-13","contact1@example.com","Bob","x"
                "001xx000003DHP1AAO","ID-24","contact2@example.com","Alice","y"
                "001xx000003DHP0AAO","ID-13","contact1@example.com","Bob","x"
                "001xx000003DHP1AAO","ID-24","contact2@example.com","Alice","y"
                """
            ),
            headers={
                "Sforce-NumberOfRecords": "4",
                "Sforce-Query-Locator": "",
            },
            status=http.OK,
        )

        query = "SELECT Id,AccountId,Email,FirstName,LastName FROM Contact"
        session = requests.Session()
        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=session,
        )
        results = client.bulk2.Contact.query(query)
        results = list(results)
        self.assertEqual(self.expected_query, results)

    @responses.activate
    def test_get_failed_record_results(self):
        """Test bulk2 get failed records"""
        operation = Operation.insert
        total = len(self.insert_data)
        ingest_responses(
            operation,
            processed=total,
            failed=total,
        )
        results = ingest_data(operation, self.insert_data)
        self.assertEqual(
            [
                {
                    "numberRecordsFailed": total,
                    "numberRecordsProcessed": total,
                    "numberRecordsTotal": total,
                    "job_id": "Job-1",
                }
            ],
            results,
        )

        def make_responses():
            responses.add(
                responses.GET,
                re.compile(r"^https://.*/jobs/ingest/Job-1/failedResults$"),
                body=textwrap.dedent(
                    """
                        "sf__Id","sf__Error","Custom_Id__c","AccountId","Email","FirstName","LastName"
                        "","UNABLE_TO_LOCK_ROW","CustomID1","ID-13","contact1@example.com","Bob","x"
                        "","UNABLE_TO_LOCK_ROW","CustomID2","ID-24","contact2@example.com","Alice","y"
                        """
                ),
                status=http.OK,
            )

        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        expected_results = textwrap.dedent(
            """
                "sf__Id","sf__Error","Custom_Id__c","AccountId","Email","FirstName","LastName"
                "","UNABLE_TO_LOCK_ROW","CustomID1","ID-13","contact1@example.com","Bob","x"
                "","UNABLE_TO_LOCK_ROW","CustomID2","ID-24","contact2@example.com","Alice","y"
                """
        )

        make_responses()
        failed_results = client.bulk2.Contact.get_failed_records("Job-1")
        self.assertEqual(expected_results, failed_results)

        make_responses()
        with temp_csv_file() as csv_file:
            client.bulk2.Contact.get_failed_records("Job-1", file=csv_file)
            with open(csv_file, "r", encoding="utf-8") as bis:
                self.assertEqual(expected_results, bis.read())

    @responses.activate
    def test_get_unprocessed_record_results(self):
        """Test bulk2 get unprocessed records"""
        operation = Operation.insert
        total = len(self.insert_data)
        ingest_responses(
            operation,
            processed=total - 1,
            failed=0,
        )
        results = ingest_data(operation, self.insert_data)
        self.assertEqual(
            [
                {
                    "numberRecordsFailed": 0,
                    "numberRecordsProcessed": total - 1,
                    "numberRecordsTotal": total,
                    "job_id": "Job-1",
                }
            ],
            results,
        )

        def make_responses():
            responses.add(
                responses.GET,
                re.compile(
                    r"^https://.*/jobs/ingest/Job-1/unprocessedRecords$"
                ),
                body=textwrap.dedent(
                    """
                        "Custom_Id__c","AccountId","Email","FirstName","LastName"
                        "CustomID2","ID-24","contact2@example.com","Alice","y"
                        """
                ),
                status=http.OK,
            )

        client = Salesforce(
            session_id=tests.SESSION_ID,
            instance_url=tests.SERVER_URL,
            session=requests.Session(),
        )
        expected_results = textwrap.dedent(
            """
            "Custom_Id__c","AccountId","Email","FirstName","LastName"
            "CustomID2","ID-24","contact2@example.com","Alice","y"
            """
        )

        make_responses()
        results = client.bulk2.Contact.get_unprocessed_records("Job-1")
        self.assertEqual(expected_results, results)

        make_responses()
        with temp_csv_file() as csv_file:
            client.bulk2.Contact.get_unprocessed_records("Job-1", file=csv_file)
            with open(csv_file, "r", encoding="utf-8") as bis:
                self.assertEqual(expected_results, bis.read())
