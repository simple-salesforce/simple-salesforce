"""
Common fixtures for tests in this directory
"""
from unittest import mock

import httpx
import pytest

from simple_salesforce.aio import AsyncSalesforce


SESSION_ID = "12345"
INSTANCE_URL = "https://na15.salesforce.com"
TOKEN_ID = "https://na15.salesforce.com/id/00Di0000000icUB/0DFi00000008UYO"
METADATA_URL = "https://na15.salesforce.com/services/Soap/m/29.0/00Di0000000icUB"
SERVER_URL = (
    "https://na15.salesforce.com/services/Soap/c/29.0/00Di0000000icUB/0DFi00000008UYO"
)
PROXIES = {
    "http": "http://10.10.1.10:3128",
    "https": "http://10.10.1.10:1080",
}

LOGIN_RESPONSE_SUCCESS = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:enterprise.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
   <soapenv:Body>
      <loginResponse>
         <result>
            <metadataServerUrl>%s</metadataServerUrl>
            <passwordExpired>false</passwordExpired>
            <sandbox>false</sandbox>
            <serverUrl>%s</serverUrl>
            <sessionId>%s</sessionId>
            <userId>005i0000002MUqLAAW</userId>
            <userInfo>
               <accessibilityMode>false</accessibilityMode>
               <currencySymbol>$</currencySymbol>
               <orgAttachmentFileSizeLimit>5242880</orgAttachmentFileSizeLimit>
               <orgDefaultCurrencyIsoCode>USD</orgDefaultCurrencyIsoCode>
               <orgDisallowHtmlAttachments>false</orgDisallowHtmlAttachments>
               <orgHasPersonAccounts>false</orgHasPersonAccounts>
               <organizationId>00Di0000000icUBEAY</organizationId>
               <organizationMultiCurrency>false</organizationMultiCurrency>
               <organizationName>salesforce.com</organizationName>
               <profileId>00ei0000001CMKcAAO</profileId>
               <roleId xsi:nil="true" />
               <sessionSecondsValid>7200</sessionSecondsValid>
               <userDefaultCurrencyIsoCode xsi:nil="true" />
               <userEmail>you@yourdomain.com</userEmail>
               <userFullName>Wade Wegner</userFullName>
               <userId>1234</userId>
               <userLanguage>en_US</userLanguage>
               <userLocale>en_US</userLocale>
               <userName>you@yourdomain.com</userName>
               <userTimeZone>America/Los_Angeles</userTimeZone>
               <userType>Standard</userType>
               <userUiSkin>Theme3</userUiSkin>
            </userInfo>
         </result>
      </loginResponse>
   </soapenv:Body>
</soapenv:Envelope>
""" % (
    METADATA_URL,
    SERVER_URL,
    SESSION_ID,
)

TOKEN_LOGIN_RESPONSE_SUCCESS = """{
    "access_token": "%s",
    "scope": "web api",
    "instance_url": "%s",
    "id": "%s",
    "token_type": "Bearer"
}""" % (
    SESSION_ID,
    INSTANCE_URL,
    TOKEN_ID,
)

TOKEN_WARNING = """
    If your connected app policy is set to "All users may
    self-authorize", you may need to authorize this
    application first. Browse to
    https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id=12345.abcde&redirect_uri=<approved URI>
    in order to Allow Access. Check first to ensure you have a valid
    <approved URI>."""

ORGANIZATION_LIMITS_RESPONSE = {
    "ConcurrentAsyncGetReportInstances": {"Max": 200, "Remaining": 200},
    "ConcurrentSyncReportRuns": {"Max": 20, "Remaining": 20},
    "DailyApiRequests": {"Max": 15000, "Remaining": 14998},
    "DailyAsyncApexExecutions": {"Max": 250000, "Remaining": 250000},
    "DailyBulkApiRequests": {"Max": 5000, "Remaining": 5000},
    "DailyDurableGenericStreamingApiEvents": {"Max": 10000, "Remaining": 10000},
    "DailyDurableStreamingApiEvents": {"Max": 10000, "Remaining": 10000},
    "DailyGenericStreamingApiEvents": {"Max": 10000, "Remaining": 10000},
    "DailyStreamingApiEvents": {"Max": 10000, "Remaining": 10000},
    "DailyWorkflowEmails": {"Max": 390, "Remaining": 390},
    "DataStorageMB": {"Max": 5, "Remaining": 5},
    "DurableStreamingApiConcurrentClients": {"Max": 20, "Remaining": 20},
    "FileStorageMB": {"Max": 20, "Remaining": 20},
    "HourlyAsyncReportRuns": {"Max": 1200, "Remaining": 1200},
    "HourlyDashboardRefreshes": {"Max": 200, "Remaining": 200},
    "HourlyDashboardResults": {"Max": 5000, "Remaining": 5000},
    "HourlyDashboardStatuses": {"Max": 999999999, "Remaining": 999999999},
    "HourlyODataCallout": {"Max": 10000, "Remaining": 9999},
    "HourlySyncReportRuns": {"Max": 500, "Remaining": 500},
    "HourlyTimeBasedWorkflow": {"Max": 50, "Remaining": 50},
    "MassEmail": {"Max": 10, "Remaining": 10},
    "SingleEmail": {"Max": 15, "Remaining": 15},
    "StreamingApiConcurrentClients": {"Max": 20, "Remaining": 20},
}

BULK_HEADERS = {
    "Content-Type": "application/json",
    "X-SFDC-Session": "%s" % SESSION_ID,
    "X-PrettyPrint": "1",
}

ALL_CONSTANTS = {
    "LOGIN_RESPONSE_SUCCESS": LOGIN_RESPONSE_SUCCESS,
    "TOKEN_LOGIN_RESPONSE_SUCCESS": TOKEN_LOGIN_RESPONSE_SUCCESS,
    "TOKEN_WARNING": TOKEN_WARNING,
    "ORGANIZATION_LIMITS_RESPONSE": ORGANIZATION_LIMITS_RESPONSE,
    "BULK_HEADERS": BULK_HEADERS,
    "SESSION_ID": "12345",
    "INSTANCE_URL": "https://na15.salesforce.com",
    "TOKEN_ID": "https://na15.salesforce.com/id/00Di0000000icUB/0DFi00000008UYO",
    "METADATA_URL": "https://na15.salesforce.com/services/Soap/m/29.0/00Di0000000icUB",
    "SERVER_URL": "https://na15.salesforce.com/services/Soap/c/29.0/00Di0000000icUB/0DFi00000008UYO",
    "PROXIES": {
        "http://": "http://10.10.1.10:3128",
        "https://": "http://10.10.1.10:1080",
    },
}


@pytest.fixture()
def constants():
    """Constants defined above as a pytest fixture"""
    return ALL_CONSTANTS


@pytest.fixture(autouse=True)
def mock_httpx_client(monkeypatch):
    """
    Build a mock httpx interface to prevent http calls
    """
    mock_httpx = mock.MagicMock(httpx)
    # prep client
    mock_client = mock.MagicMock(httpx.AsyncClient)
    mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mock.AsyncMock()
    mock_client.get = mock.AsyncMock()
    mock_client.post = mock.AsyncMock()
    mock_client.put = mock.AsyncMock()
    mock_client.delete = mock.AsyncMock()

    mock_httpx.AsyncClient.return_value = mock_client

    def inner(resp):
        """
        Allows callers to dynamically set the response value on each method.
        They can also do this with `mock_client` object as well.
        """
        mock_client.request = mock.AsyncMock(return_value=resp)
        mock_client.get = mock.AsyncMock(return_value=resp)
        mock_client.post = mock.AsyncMock(return_value=resp)
        mock_client.put = mock.AsyncMock(return_value=resp)
        mock_client.delete = mock.AsyncMock(return_value=resp)
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", mock_httpx.AsyncClient)

    return mock_httpx, mock_client, inner


# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
@pytest.fixture()
def sf_client(constants, mock_httpx_client):
    """Simple fixture for crafting the client used below"""
    client = AsyncSalesforce(
        session_id=constants["SESSION_ID"], proxies=constants["PROXIES"]
    )
    client.headers = {}
    client.base_url = "https://localhost/"
    client.metadata_url = "https://localhost/metadata/"
    client.bulk_url = "https://localhost/async/"
    client.apex_url = "https://localhost/apexrest/"
    client.tooling_url = "https://localhost/tooling/"
    return client
