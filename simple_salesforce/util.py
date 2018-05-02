"""Utility functions for simple-salesforce"""
import ssl
import xml.dom.minidom
from urllib3 import PoolManager

from requests import PreparedRequest
from requests.adapters import HTTPAdapter

from simple_salesforce.exceptions import (
    SalesforceGeneralError, SalesforceExpiredSession,
    SalesforceMalformedRequest, SalesforceMoreThanOneRecord,
    SalesforceRefusedRequest, SalesforceResourceNotFound
)


# pylint: disable=invalid-name
def getUniqueElementValueFromXmlString(xmlString, elementName):
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
        elementValue = elementsByName[0].toxml().replace(
            '<' + elementName + '>', '').replace('</' + elementName + '>', '')
    return elementValue


def date_to_iso8601(date):
    """Returns an ISO8601 string from a date"""
    datetimestr = date.strftime('%Y-%m-%dT%H:%M:%S')
    timezone_sign = date.strftime('%z')[0:1]
    timezone_str = '%s:%s' % (
        date.strftime('%z')[1:3], date.strftime('%z')[3:5])
    return '{datetimestr}{tzsign}{timezone}'.format(
        datetimestr=datetimestr,
        tzsign=timezone_sign,
        timezone=timezone_str
        ).replace(':', '%3A').replace('+', '%2B')


def exception_handler(result, name=""):
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


def call_salesforce(url, method, session, headers, **kwargs):
    """Utility that generates a request to salesforce using urllib3 instead of
    requests package. This is necessary for connections that use the mutual
    authentication with encrypted certificates, the package requests  can't
    handle it.

    PrepareRequest and HttpAdapter are used so that it returns a regular
    Response <requests.Response> that is expected for the rest of the process.
    """
    additional_headers = kwargs.pop('additional_headers', dict())
    headers.update(additional_headers or dict())

    request_args = {
        'url': url,
        'method': method.upper(),
        'headers': headers
    }

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    # We will try and load the cert file and pass from the environment variables
    cert_file = os.environ.get('SIMPLE_SALESFORCE_CERT_FILE', None)
    cert_pass = os.environ.get('SIMPLE_SALESFORCE_PASSWORD', None)
    if cert_file and cert_pass:
        context.load_cert_chain(certfile=cert_file, password=cert_pass)

    request = PreparedRequest()
    request.prepare(data=kwargs.get('data') or {}, **request_args)

    http = PoolManager(ssl_context=context, cert_reqs='CERT_REQUIRED')
    result = http.urlopen(
        body=request.body,
        redirect=False,
        assert_same_host=False,
        preload_content=False,
        decode_content=False, **request_args)

    adapter = HTTPAdapter()
    response = adapter.build_response(request, result)

    if response.status_code >= 300:
        from simple_salesforce.util import exception_handler
        exception_handler(response)

    return response
