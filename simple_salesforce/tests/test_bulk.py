"""Tests for bulk.py"""

import re

try:
    # Python 2.6
    import unittest2 as unittest
except ImportError:
    import unittest

import responses

try:
    # Python 2.6/2.7
    import httplib as http
except ImportError:
    # Python 3
    import http.client as http

import requests

from simple_salesforce import tests
from simple_salesforce.api import (
    Salesforce,
)


class TestSFBulkType(unittest.TestCase):
    """Tests for SFBulkType instance"""
    @responses.activate
    def test_get_batch_results(self):
        """Ensure bulk API query interates over results"""
        # start a job
        responses.add(
            responses.POST,
            re.compile(r'^https://.*/services/async/38.0/job$'),
            body='''{
                       "apexProcessingTime" : 0,
                       "apiActiveProcessingTime" : 0,
                       "apiVersion" : 36.0,
                       "concurrencyMode" : "Parallel",
                       "contentType" : "JSON",
                       "createdById" : "005D0000001b0fFIAQ",
                       "createdDate" : "2015-12-15T20:45:25.000+0000",
                       "id" : "750D00000004SkGIAU",
                       "numberBatchesCompleted" : 0,
                       "numberBatchesFailed" : 0,
                       "numberBatchesInProgress" : 0,
                       "numberBatchesQueued" : 0,
                       "numberBatchesTotal" : 0,
                       "numberRecordsFailed" : 0,
                       "numberRecordsProcessed" : 0,
                       "numberRetries" : 0,
                       "object" : "Account",
                       "operation" : "insert",
                       "state" : "Open",
                       "systemModstamp" : "2015-12-15T20:45:25.000+0000",
                       "totalProcessingTime" : 0
                    }''',
            status=http.OK)
        # add batchs by callback
        batch_ids = ['751D00000004YGZIA2', '751D00000004YGZIA3']

        def batch_callback(res):
            """Provides dynamic responses"""
            btch = batch_ids.pop()
            res = '''
                    {
                        "apexProcessingTime": 0,
                        "apiActiveProcessingTime": 0,
                        "createdDate": "2015-12-15T21:56:43.000+0000",
                        "id": "%s",
                        "jobId": "750D00000004SkVIAU",
                        "numberRecordsFailed": 0,
                        "numberRecordsProcessed": 0,
                        "state": "Queued",
                        "systemModstamp": "2015-12-15T21:56:43.000+0000",
                        "totalProcessingTime": 0
                    }
                    ''' % (btch)
            return (200, {}, res)

        responses.add_callback(
            responses.POST,
            re.compile(r'^https://.*/job/750D00000004SkGIAU/batch$'),
            callback=batch_callback)
        # close job
        responses.add(
            responses.POST,
            re.compile(r'^https://.*/job/750D00000004SkGIAU$'),
            body='''{
                       "apexProcessingTime":0,
                       "apiActiveProcessingTime":0,
                       "createdDate":"2015-12-15T21:56:43.000+0000",
                       "id":"751D00000004YGZIA2",
                       "jobId":"750D00000004SkVIAU",
                       "numberRecordsFailed":0,
                       "numberRecordsProcessed":0,
                       "state":"Closed",
                       "systemModstamp":"2015-12-15T21:56:43.000+0000",
                       "totalProcessingTime":0
                    }''',
            status=http.OK)
        # batch status
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/job/750D00000004SkVIAU/'
                       r'batch/751D00000004YGZIA2$'),
            body='''{
                       "apexProcessingTime":0,
                       "apiActiveProcessingTime":0,
                       "createdDate":"2015-12-15T21:56:43.000+0000",
                       "id":"751D00000004YGZIA2",
                       "jobId":"750D00000004SkVIAU",
                       "numberRecordsFailed":0,
                       "numberRecordsProcessed":1,
                       "state":"Completed",
                       "systemModstamp":"2015-12-15T21:56:43.000+0000",
                       "totalProcessingTime":0
                    }''',
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/job/750D00000004SkVIAU/'
                       r'batch/751D00000004YGZIA3$'),
            body='''{
                       "apexProcessingTime":0,
                       "apiActiveProcessingTime":0,
                       "createdDate":"2015-12-15T21:56:43.000+0000",
                       "id":"751D00000004YGZIA3",
                       "jobId":"750D00000004SkVIAU",
                       "numberRecordsFailed":0,
                       "numberRecordsProcessed":1,
                       "state":"Completed",
                       "systemModstamp":"2015-12-15T21:56:43.000+0000",
                       "totalProcessingTime":0
                    }''',
            status=http.OK)
        # batch results
        responses.add(
            responses.GET,
            re.compile(r'^https://.*/job/750D00000004SkVIAU/'
                       r'batch/751D00000004YGZIA3/result$'),
            body=tests.RESULT_OUTPUT,
            status=http.OK)

        responses.add(
            responses.GET,
            re.compile(
                r'^https://.*/job/750D00000004SkVIAU/'
                r'batch/751D00000004YGZIA3/result/7520y0000061ADL$'),
            json=[{'result_1': 'json_1'}],
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(
                r'^https://.*/job/750D00000004SkVIAU/'
                r'batch/751D00000004YGZIA3/result/7520y0000061ADQ$'),
            json=[{'result_2': 'json_2'}],
            status=http.OK)
        responses.add(
            responses.GET,
            re.compile(
                r'^https://.*/job/750D00000004SkVIAU/'
                r'batch/751D00000004YGZIA3/result/7520y0000061ADa$'),
            json=[{'result_3': 'json_3'}],
            status=http.OK)

        session = requests.Session()
        client = Salesforce(session_id=tests.SESSION_ID,
                            instance_url=tests.SERVER_URL,
                            session=session)

        results = client.bulk.Account.query('')
        result_list = []
        for result in results:
            for line in result:
                result_list.append(line)
        self.assertEqual(
            result_list,
            [{'result_1': 'json_1'},
             {'result_2': 'json_2'},
             {'result_3': 'json_3'}]
        )
