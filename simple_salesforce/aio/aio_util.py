"""Utility functions for simple-salesforce async calls"""
from typing import Dict, Optional

import httpx

from simple_salesforce.util import exception_handler


async def call_salesforce(
    url: str = "",
    method: str = "GET",
    async_client: Optional[httpx.AsyncClient] = None,
    headers: Optional[Dict] = None,
    **kwargs
):
    """Utility method for performing HTTP call to Salesforce.

    Returns a `httpx.Response` object.
    """
    if not async_client:
        async_client = httpx.AsyncClient()

    headers = headers or dict()
    additional_headers = kwargs.pop("additional_headers", dict())
    headers.update(additional_headers or dict())
    result = await async_client.request(method, url, headers=headers, **kwargs)
    if result.status_code >= 300:
        exception_handler(result)
    if not async_client:
        await async_client.aclose()

    return result
