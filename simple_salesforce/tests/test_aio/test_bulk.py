"""Test for bulk.py"""
import copy
import json
from unittest import mock

import httpx
import pytest

from simple_salesforce.exceptions import SalesforceGeneralError


def test_bulk_handler(sf_client, constants):
    """Test that BulkHandler Loads Properly"""
    bulk_handler = sf_client.bulk
    assert bulk_handler.session_id == sf_client.session_id
    assert bulk_handler.bulk_url == sf_client.bulk_url
    assert constants["BULK_HEADERS"] == bulk_handler.headers


def test_bulk_type(sf_client, constants):
    """Test bulk type creation"""
    contact = sf_client.bulk.Contact
    assert contact.bulk_url == sf_client.bulk_url
    assert constants["BULK_HEADERS"] == contact.headers
    assert "Contact" == contact.object_name


EXPECTED_RESULT = [
    {"success": True, "created": True, "id": "001xx000003DHP0AAO", "errors": []},
    {"success": True, "created": True, "id": "001xx000003DHP1AAO", "errors": []},
]
EXPECTED_QUERY = [
    {
        "Id": "001xx000003DHP0AAO",
        "AccountId": "ID-13",
        "Email": "contact1@example.com",
        "FirstName": "Bob",
        "LastName": "x",
    },
    {
        "Id": "001xx000003DHP1AAO",
        "AccountId": "ID-24",
        "Email": "contact2@example.com",
        "FirstName": "Alice",
        "LastName": "y",
    },
    {
        "Id": "001xx000003DHP0AAO",
        "AccountId": "ID-13",
        "Email": "contact1@example.com",
        "FirstName": "Bob",
        "LastName": "x",
    },
    {
        "Id": "001xx000003DHP1AAO",
        "AccountId": "ID-24",
        "Email": "contact2@example.com",
        "FirstName": "Alice",
        "LastName": "y",
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation,method_name",
    (
        ("delete", "delete"),
        ("insert", "insert"),
        ("update", "update"),
        ("hardDelete", "hard_delete"),
    ),
)
async def test_insert(operation, method_name, sf_client, mock_httpx_client):
    """Test bulk insert records"""
    _, mock_client, _ = mock_httpx_client
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = copy.deepcopy(body1)
    body3["state"] = "Closed"
    body4 = copy.deepcopy(body2)
    body4["state"] = "InProgress"
    body5 = copy.deepcopy(body2)
    body5["state"] = "Completed"
    body6 = [
        {"success": True, "created": True, "id": "001xx000003DHP0AAO", "errors": []},
        {"success": True, "created": True, "id": "001xx000003DHP1AAO", "errors": []},
    ]
    body7 = {}
    all_bodies = [body1, body2, body3, body4, body5, body6, body7]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)
    data = [
        {
            "AccountId": "ID-1",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "AccountId": "ID-2",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    function = getattr(sf_client.bulk.Contact, method_name)
    result = await function(data, wait=0.1)
    assert EXPECTED_RESULT == result


@pytest.mark.asyncio
async def test_upsert(sf_client, mock_httpx_client):
    """Test bulk upsert records"""
    _, mock_client, _ = mock_httpx_client
    operation = "delete"
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = copy.deepcopy(body1)
    body3["state"] = "Closed"
    body4 = copy.deepcopy(body2)
    body4["state"] = "InProgress"
    body5 = copy.deepcopy(body2)
    body5["state"] = "Completed"
    body6 = [
        {"success": True, "created": True, "id": "001xx000003DHP0AAO", "errors": []},
        {"success": True, "created": True, "id": "001xx000003DHP1AAO", "errors": []},
    ]
    body7 = {}
    all_bodies = [body1, body2, body3, body4, body5, body6, body7]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)
    data = [{"id": "ID-1"}, {"id": "ID-2"}]
    result = await sf_client.bulk.Contact.upsert(data, "some-field", wait=0.1)
    assert EXPECTED_RESULT == result


@pytest.mark.asyncio
async def test_query(mock_httpx_client, sf_client):
    """Test bulk query"""
    _, mock_client, _ = mock_httpx_client
    operation = "query"
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = copy.deepcopy(body1)
    body3["state"] = "Closed"
    body4 = copy.deepcopy(body2)
    body4["state"] = "InProgress"
    body5 = copy.deepcopy(body2)
    body5["state"] = "Completed"
    body6 = ["752x000000000F1", "752x000000000F2"]
    body7 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-13",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-24",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    body8 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-13",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-24",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    all_bodies = [body1, body2, body3, body4, body5, body6, body7, body8]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)
    data = "SELECT Id,AccountId,Email,FirstName,LastName FROM Contact"
    result = await sf_client.bulk.Contact.query(data, wait=0.1, lazy_operation=False)
    assert body7[0] in result
    assert body7[1] in result
    assert body8[0] in result
    assert body8[1] in result


@pytest.mark.asyncio
async def test_query_all(mock_httpx_client, sf_client):
    """Test bulk query all"""
    _, mock_client, _ = mock_httpx_client
    operation = "queryAll"
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = copy.deepcopy(body1)
    body3["state"] = "Closed"
    body4 = copy.deepcopy(body2)
    body4["state"] = "InProgress"
    body5 = copy.deepcopy(body2)
    body5["state"] = "Completed"
    body6 = ["752x000000000F1", "752x000000000F2"]
    body7 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-13",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-24",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    body8 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-13",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-24",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    all_bodies = [body1, body2, body3, body4, body5, body6, body7, body8]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)
    data = "SELECT Id,AccountId,Email,FirstName,LastName FROM Contact"
    result = await sf_client.bulk.Contact.query_all(
        data, wait=0.1, lazy_operation=False
    )
    assert body7[0] in result
    assert body7[1] in result
    assert body8[0] in result
    assert body8[1] in result


@pytest.mark.asyncio
async def test_query_lazy(mock_httpx_client, sf_client):
    """Test lazy bulk query"""
    _, mock_client, _ = mock_httpx_client
    operation = "queryAll"
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = copy.deepcopy(body1)
    body3["state"] = "Closed"
    body4 = copy.deepcopy(body2)
    body4["state"] = "InProgress"
    body5 = copy.deepcopy(body2)
    body5["state"] = "Completed"
    body6 = ["752x000000000F1", "752x000000000F2"]
    body7 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-13",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-24",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    body8 = [
        {
            "Id": "001xx000003DHP0AAO",
            "AccountId": "ID-15",
            "Email": "contact1@example.com",
            "FirstName": "Bob",
            "LastName": "x",
        },
        {
            "Id": "001xx000003DHP1AAO",
            "AccountId": "ID-26",
            "Email": "contact2@example.com",
            "FirstName": "Alice",
            "LastName": "y",
        },
    ]
    all_bodies = [body1, body2, body3, body4, body5, body6, body7, body8]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)
    data = "SELECT Id,AccountId,Email,FirstName,LastName FROM Contact"
    result = await sf_client.bulk.Contact.query_all(data, wait=0.1, lazy_operation=True)
    assert body7[0] in result[0]
    assert body7[1] in result[0]
    assert body8[0] in result[1]
    assert body8[1] in result[1]
    # [[{'Id': '001xx000003DHP0AAO', 'AccountId': 'ID-13',
    # 'Email': 'contact1@example.com', 'FirstName': 'Bob',
    # 'LastName': 'x'}, {'Id': '001xx000003DHP1AAO',
    # 'AccountId': 'ID-24', 'Email': 'contact2@example.com',
    # 'FirstName': 'Alice', 'LastName': 'y'}],
    # [{'Id': '001xx000003DHP0AAO', 'AccountId': 'ID-13',
    # 'Email': 'contact1@example.com', 'FirstName': 'Bob',
    # 'LastName': 'x'}, {'Id': '001xx000003DHP1AAO',
    # 'AccountId': 'ID-24', 'Email': 'contact2@example.com',
    # 'FirstName': 'Alice', 'LastName': 'y'}]]


@pytest.mark.asyncio
async def test_query_fail(mock_httpx_client, sf_client):
    """Test bulk query records failure"""
    _, mock_client, _ = mock_httpx_client
    operation = "query"
    body1 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Open",
    }
    body2 = {"id": "Batch-1", "jobId": "Job-1", "state": "Queued"}
    body3 = {
        "apiVersion": 42.0,
        "concurrencyMode": "Parallel",
        "contentType": "JSON",
        "id": "Job-1",
        "object": "Contact",
        "operation": operation,
        "state": "Closed",
    }
    body4 = {"id": "Batch-1", "jobId": "Job-1", "state": "InProgress"}
    body5 = {
        "id": "Batch-1",
        "jobId": "Job-1",
        "state": "Failed",
        "stateMessage": "InvalidBatch : Failed to process query",
    }
    all_bodies = [body1, body2, body3, body4, body5]
    responses = [httpx.Response(200, content=json.dumps(body)) for body in all_bodies]
    mock_client.request.side_effect = mock.AsyncMock(side_effect=responses)

    data = "SELECT ASDFASfgsds FROM Contact"
    with pytest.raises(SalesforceGeneralError) as exc:
        await sf_client.bulk.Contact.query(data, wait=0.1)
        assert exc.status == body5["state"]
        assert exc.resource_name == body5["jobId"]
        assert exc.content == body5["stateMessage"]
