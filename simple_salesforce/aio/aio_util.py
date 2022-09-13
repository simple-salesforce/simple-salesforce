"""Utility functions for simple-salesforce async calls"""
from functools import partial
from typing import Callable, Dict, Optional

import httpx

from simple_salesforce.util import exception_handler


def create_session_factory(
    proxies=None, timeout: Optional[int] = None
) -> Callable[[], httpx.AsyncClient]:
    """
    Convenience function for repeatedly returning the properly constructed
    AsyncClient.
    """
    if proxies and timeout:
        return partial(
            httpx.AsyncClient,
            proxies=proxies,
            timeout=timeout
        )
    elif proxies:
        return partial(
            httpx.AsyncClient,
            proxies=proxies
        )
    elif timeout:
        return partial(
            httpx.AsyncClient,
            timeout=timeout
        )

    return partial(httpx.AsyncClient)


async def call_salesforce(
    url: str = "",
    method: str = "GET",
    headers: Optional[Dict] = None,
    session_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    **kwargs
):
    """Utility method for performing HTTP call to Salesforce.

    Returns a `httpx.Response` object.
    """
    if session_factory:
        client = session_factory()
    else:
        client = httpx.AsyncClient()

    headers = headers or dict()
    additional_headers = kwargs.pop("additional_headers", dict())
    headers.update(additional_headers or dict())
    async with client as session:
        result = await session.request(method, url, headers=headers, **kwargs)
    if result.status_code >= 300:
        exception_handler(result)

    return result
