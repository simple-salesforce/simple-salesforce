"""Utility functions for simple-salesforce"""

import datetime
import xml.dom.minidom
from typing import Any, Iterable, List, Mapping, MutableMapping, NamedTuple, \
    NoReturn, \
    Optional, \
    TypeVar, Union

import requests

from .exceptions import (SalesforceExpiredSession, SalesforceGeneralError,
                         SalesforceMalformedRequest,
                         SalesforceMoreThanOneRecord, SalesforceRefusedRequest,
                         SalesforceResourceNotFound)

Headers = MutableMapping[str, str]
Proxies = MutableMapping[str, str]
BulkDataAny = List[Mapping[str, Any]]
BulkDataStr = List[Mapping[str, str]]
T = TypeVar('T')

class Usage(NamedTuple):
    """Usage information for a Salesforce org"""
    used: int
    total: int

class PerAppUsage(NamedTuple):
    """Per App Usage information for a Salesforce org"""
    used: int
    total: int
    name: str

# pylint: disable=invalid-name
def getUniqueElementValueFromXmlString(
        xmlString: Union[str, bytes],
        elementName: str) -> Optional[str]:
    """
    Extracts an element value from an XML string.

    For example, invoking
    getUniqueElementValueFromXmlString(
        '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
    elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
    elementValue = None
    if len(elementsByName) > 0:
        elementValue = (
            elementsByName[0]
            .toxml()
            .replace('<' + elementName + '>', '')
            .replace('</' + elementName + '>', '')
        )
    return elementValue


def date_to_iso8601(date: datetime.date) -> str:
    """Returns an ISO8601 string from a date"""
    datetimestr = date.strftime('%Y-%m-%dT%H:%M:%S')
    timezonestr = date.strftime('%z')
    return (
        f'{datetimestr}{timezonestr[0:3]}:{timezonestr[3:5]}'
        .replace(':', '%3A')
        .replace('+', '%2B')
    )


def exception_handler(
        result: requests.Response,
        name: str = "") -> NoReturn:
    """Exception router. Determines which error to raise for bad results"""
    try:
        response_content = result.json()
    # pylint: disable=broad-except
    except Exception:
        response_content = result.text

    exc_map = {
        300: SalesforceMoreThanOneRecord,
        400: SalesforceMalformedRequest,
        401: SalesforceExpiredSession,
        403: SalesforceRefusedRequest,
        404: SalesforceResourceNotFound,
    }
    exc_cls = exc_map.get(result.status_code, SalesforceGeneralError)

    raise exc_cls(result.url, result.status_code, name, response_content)


def call_salesforce(
        url: str,
        method: str,
        session: requests.Session,
        headers: Headers,
        **kwargs: Any) -> requests.Response:
    """Utility method for performing HTTP call to Salesforce.

    Returns a `requests.result` object.
    """

    additional_headers = kwargs.pop('additional_headers', {})
    headers.update(additional_headers or {})
    result = session.request(method, url, headers=headers, **kwargs)

    if result.status_code >= 300:
        exception_handler(result)

    return result

def list_from_generator(
        generator_function: Iterable[Iterable[T]]
) -> List[T]:
    """Utility method for constructing a list from a generator function"""
    ret_val: List[T] = []
    for list_results in generator_function:
        ret_val.extend(list_results)
    return ret_val
