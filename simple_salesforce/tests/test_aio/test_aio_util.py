"""Tests for simple-salesforce aio utility functions"""
import httpx

import pytest

from simple_salesforce.exceptions import (
    SalesforceExpiredSession,
    SalesforceMalformedRequest,
    SalesforceMoreThanOneRecord,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
)
from simple_salesforce.aio.aio_util import call_salesforce


@pytest.mark.asyncio
async def test_call_salesforce_happy_path(mock_httpx_client):
    """Test happy path responses: <= 300"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(200)
    inner(happy_result)
    # no exceptions
    assert (
        await call_salesforce(
            method="GET", url="www.example.com", async_client=mock_client
        )
        is happy_result
    )
    assert await call_salesforce(method="GET", url="www.example.com",) is happy_result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,exception_class",
    (
        (300, SalesforceMoreThanOneRecord),
        (400, SalesforceMalformedRequest),
        (401, SalesforceExpiredSession),
        (403, SalesforceRefusedRequest),
        (404, SalesforceResourceNotFound),
    ),
)
async def test_call_salesforce_exceptions(
    status_code, exception_class, mock_httpx_client
):
    """Test exception-handling responses: => 300"""
    _, mock_client, inner = mock_httpx_client
    exc_result = httpx.Response(
        status_code, request=httpx.Request("GET", "www.example.com")
    )
    inner(exc_result)
    with pytest.raises(exception_class):
        await call_salesforce(
            method="GET", url="www.example.com", async_client=mock_client
        )
    with pytest.raises(exception_class):
        await call_salesforce(method="GET", url="www.example.com")
