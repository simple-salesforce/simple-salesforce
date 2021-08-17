"""Tests for login.py"""
import json
import os
from urllib.parse import urlparse
import warnings

import httpx
import pytest

from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from simple_salesforce.aio.login import AsyncSalesforceLogin


PARENT_DIR = os.path.dirname(os.path.dirname(__file__))
SOAP_URL = "https://login.salesforce.com/services/Soap/u/"
OAUTH_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"


@pytest.mark.asyncio
async def test_default_domain_success(constants, mock_httpx_client):
    """Test login for default domain"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(200, content=constants["LOGIN_RESPONSE_SUCCESS"])
    inner(happy_result)
    mock_client.custom_session_attrib = "X-1-2-3"

    (session_id, instance_url) = await AsyncSalesforceLogin(
        session=mock_client,
        username="foo@bar.com",
        password="password",
        security_token="token",
    )
    assert session_id == constants["SESSION_ID"]
    assert instance_url == urlparse(constants["INSTANCE_URL"]).netloc
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0].startswith(SOAP_URL)
    assert "SOAPAction" in call[2]["headers"]
    assert call[2]["headers"]["SOAPAction"] == "login"


@pytest.mark.asyncio
async def test_custom_domain_success(constants, mock_httpx_client):
    """Test login for custom domain"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(200, content=constants["LOGIN_RESPONSE_SUCCESS"])
    inner(happy_result)
    mock_client.custom_session_attrib = "X-1-2-3"

    (session_id, instance_url) = await AsyncSalesforceLogin(
        session=mock_client,
        username="foo@bar.com",
        password="password",
        domain="testdomain.my",
    )
    assert session_id == constants["SESSION_ID"]
    assert instance_url == urlparse(constants["INSTANCE_URL"]).netloc
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0] == ("https://testdomain.my.salesforce.com/services/Soap/u/42.0")
    assert "SOAPAction" in call[2]["headers"]
    assert call[2]["headers"]["SOAPAction"] == "login"


@pytest.mark.asyncio
async def test_failure(mock_httpx_client):
    """Test login for custom domain"""
    _, mock_client, inner = mock_httpx_client
    mock_response = (
        '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope '
        'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:sf="urn:fault.partner.soap.sforce.com" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<soapenv:Body><soapenv:Fault><faultcode>INVALID_LOGIN</faultcode>"
        "<faultstring>INVALID_LOGIN: Invalid username, password, "
        "security token; or user locked out.</faultstring><detail>"
        '<sf:LoginFault xsi:type="sf:LoginFault"><sf:exceptionCode>'
        "INVALID_LOGIN</sf:exceptionCode><sf:exceptionMessage>Invalid "
        "username, password, security token; or user locked out."
        "</sf:exceptionMessage></sf:LoginFault></detail></soapenv:Fault>"
        "</soapenv:Body></soapenv:Envelope>"
    )
    fail_result = httpx.Response(
        500,
        request=httpx.Request("POST", "login.my.salesforce.com"),
        content=mock_response,
    )
    inner(fail_result)
    mock_client.custom_session_attrib = "X-1-2-3"

    with pytest.raises(SalesforceAuthenticationFailed):
        await AsyncSalesforceLogin(
            session=mock_client,
            username="foo@bar.com",
            password="password",
            security_token="token",
        )
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0].startswith(SOAP_URL)
    assert "SOAPAction" in call[2]["headers"]
    assert call[2]["headers"]["SOAPAction"] == "login"


@pytest.fixture()
def sample_key_filepath():
    """Path to sample-key fixture"""
    return os.path.join(PARENT_DIR, "sample-key.pem")


@pytest.fixture()
def sample_key(sample_key_filepath):
    """File-handle in bytes for sample-key fixture"""
    with open(sample_key_filepath, "rb") as key_file:
        return key_file.read()


@pytest.mark.asyncio
async def test_token_login_success_with_key_file(
    sample_key_filepath, constants, mock_httpx_client
):
    """Test a successful JWT Token login with a key file"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(
        200, content=constants["TOKEN_LOGIN_RESPONSE_SUCCESS"]
    )
    inner(happy_result)

    (session_id, instance_url) = await AsyncSalesforceLogin(
        session=mock_client,
        username="foo@bar.com",
        consumer_key="12345.abcde",
        privatekey_file=sample_key_filepath,
    )
    assert session_id == constants["SESSION_ID"]
    assert instance_url == urlparse(constants["INSTANCE_URL"]).netloc
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0].startswith(OAUTH_TOKEN_URL)
    assert call[2]["data"]["grant_type"] == (
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    )


@pytest.mark.asyncio
async def test_token_login_success_with_key_string(
    sample_key, constants, mock_httpx_client
):
    """Test a successful JWT Token login with a private key"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(
        200, content=constants["TOKEN_LOGIN_RESPONSE_SUCCESS"]
    )
    inner(happy_result)
    (session_id, instance_url) = await AsyncSalesforceLogin(
        session=mock_client,
        username="foo@bar.com",
        consumer_key="12345.abcde",
        privatekey=sample_key.decode(),
    )

    assert session_id == constants["SESSION_ID"]
    assert instance_url == urlparse(constants["INSTANCE_URL"]).netloc
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0].startswith(OAUTH_TOKEN_URL)
    assert call[2]["data"]["grant_type"] == (
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    )


@pytest.mark.asyncio
async def test_token_login_success_with_key_bytes(
    sample_key, constants, mock_httpx_client
):
    """Test a successful JWT Token login with a private key"""
    _, mock_client, inner = mock_httpx_client
    happy_result = httpx.Response(
        200, content=constants["TOKEN_LOGIN_RESPONSE_SUCCESS"]
    )
    inner(happy_result)
    (session_id, instance_url) = await AsyncSalesforceLogin(
        session=mock_client,
        username="foo@bar.com",
        consumer_key="12345.abcde",
        privatekey=sample_key,
    )

    assert session_id == constants["SESSION_ID"]
    assert instance_url == urlparse(constants["INSTANCE_URL"]).netloc
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]
    assert call[0] == "post"
    assert call[1][0].startswith(OAUTH_TOKEN_URL)
    assert call[2]["data"]["grant_type"] == (
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    )


@pytest.mark.asyncio
async def test_token_login_failure(mock_httpx_client, sample_key_filepath):
    """Test login for custom domain"""
    _, mock_client, inner = mock_httpx_client
    fail_result = httpx.Response(
        400,
        request=httpx.Request("POST", "login.my.salesforce.com"),
        content=json.dumps(
            {
                "error": "invalid_client_id",
                "error_description": "client identifier invalid",
            }
        ),
    )
    inner(fail_result)

    with pytest.raises(SalesforceAuthenticationFailed):
        await AsyncSalesforceLogin(
            session=mock_client,
            username="foo@bar.com",
            consumer_key="12345.abcde",
            privatekey_file=sample_key_filepath,
        )
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]

    assert call[0] == "post"
    assert call[1][0].startswith(OAUTH_TOKEN_URL)
    assert call[2]["data"]["grant_type"] == (
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    )


@pytest.mark.asyncio
async def test_token_login_failure_with_warning(
    mock_httpx_client, constants, sample_key_filepath
):
    """Test login for custom domain"""
    _, mock_client, inner = mock_httpx_client
    fail_result = httpx.Response(
        400,
        request=httpx.Request("POST", "login.my.salesforce.com"),
        content=json.dumps(
            {
                "error": "invalid_grant",
                "error_description": "user hasn't approved this consumer",
            }
        ),
    )
    inner(fail_result)
    with warnings.catch_warnings(record=True) as warning:
        with pytest.raises(SalesforceAuthenticationFailed):
            await AsyncSalesforceLogin(
                session=mock_client,
                username="foo@bar.com",
                consumer_key="12345.abcde",
                privatekey_file=sample_key_filepath,
            )
    assert len(mock_client.method_calls) == 1
    call = mock_client.method_calls[0]

    assert call[0] == "post"
    assert call[1][0].startswith(OAUTH_TOKEN_URL)
    assert call[2]["data"]["grant_type"] == (
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    )
    assert len(warning) >= 1
    assert issubclass(warning[-1].category, UserWarning)
    assert str(warning[-1].message) == constants["TOKEN_WARNING"]
