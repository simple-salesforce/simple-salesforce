"""Tests for composite.py"""

import json
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

from simple_salesforce.api import (
    Salesforce,
)





class TestComposite(unittest.TestCase):
    """Tests of the composite API"""

    @responses.activate
    def test_composite_create(self):
        """Test the composite/sobjects create API"""
        records = [
            {
                'attributes':{'type':'Contact'},
                'LastName':'Smith',
                'Email':'example@example.com',
            },
            {
                'attributes':{'type':'Contact'},
                'LastName':'Jones',
                'Email':'test@test.com',
            },
        ]
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.POST,
            re.compile(r'^https://localhost/composite/sobjects$'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.create(records)
        self.assertEqual(res, resp)
        body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(body, {'records':records, 'allOrNone':False})

    @responses.activate
    def test_composite_create_allornone(self):
        """Test the composite/sobjects create API with all_or_none=True"""
        records = [
            {
                'attributes':{'type':'Contact'},
                'LastName':'Smith',
                'Email':'example@example.com',
            },
            {
                'attributes':{'type':'Contact'},
                'LastName':'Jones',
                'Email':'test@test.com',
            },
        ]
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.POST,
            re.compile(r'^https://localhost/composite/sobjects$'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.create(records, True)
        self.assertEqual(res, resp)
        body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(body, {'records':records, 'allOrNone':True})

    @responses.activate
    def test_composite_update(self):
        """Test the composite/sobjects update API"""
        records = [
            {
                'attributes':{'type':'Contact'},
                'Id':'0000000000AAAAA',
                'Email':'examplenew@example.com',
            },
            {
                'attributes':{'type':'Contact'},
                'Id':'0000000000BBBBB',
                'Email':'testnew@test.com',
            },
        ]
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.PATCH,
            re.compile(r'^https://localhost/composite/sobjects$'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.update(records)
        self.assertEqual(res, resp)
        body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(body, {'records':records, 'allOrNone':False})

    @responses.activate
    def test_composite_delete(self):
        """Test the composite/sobjects delete API"""
        ids = ['0000000000AAAAA', '0000000000BBBBB']
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.DELETE,
            re.compile(r'^https://localhost/composite/sobjects'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.delete(ids)
        self.assertEqual(res, resp)
        url = responses.calls[-1].request.url
        self.assertIn("ids=0000000000AAAAA%2C0000000000BBBBB", url)
        self.assertIn("allOrNone=False", url)

    @responses.activate
    def test_composite_get(self):
        """Test the composite/sobjects/SObjectType retrieve API"""
        ids = ['0000000000AAAAA', '0000000000BBBBB']
        fields = ['Name', 'Other']
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.POST,
            re.compile(r'^https://localhost/composite/sobjects/Account$'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.Account.get(ids, fields)
        self.assertEqual(res, resp)
        body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(body, {'ids':ids, 'fields':fields})

    @responses.activate
    def test_composite_tree_create(self):
        """Test the composite/tree/SObjectType tree create API"""
        records = ['stuff', 'and', 'nonsense']
        resp = ['whatever', 'Salesforce']
        responses.add(
            responses.POST,
            re.compile(r'^https://localhost/composite/tree/Account$'),
            body=json.dumps(resp),
            status=http.OK
        )

        client = Salesforce.__new__(Salesforce)
        client.session_id = '12345'
        client.composite_url = 'https://localhost/composite/'
        client.proxies = None
        client.session = requests.Session()
        res = client.composite.Account.tree_create(records)
        self.assertEqual(res, resp)
        body = json.loads(responses.calls[-1].request.body)
        self.assertEqual(body, {'records':records})
