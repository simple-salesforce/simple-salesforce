"""Login classes and functions for Simple-Salesforce

Heavily Modified from RestForce 1.0.0
"""
import base64

DEFAULT_CLIENT_ID_PREFIX = 'simple-salesforce'

import warnings
from datetime import datetime, timedelta, timezone
from html import escape, unescape
from json.decoder import JSONDecodeError
from pathlib import Path

import requests
import jwt

from .api import DEFAULT_API_VERSION
from .exceptions import SalesforceAuthenticationFailed
from .util import getUniqueElementValueFromXmlString


# pylint: disable=invalid-name,too-many-arguments,too-many-locals,too-many-branches
def SalesforceLogin(
        username=None,
        password=None,
        security_token=None,
        organizationId=None,
        sf_version=DEFAULT_API_VERSION,
        proxies=None,
        session=None,
        client_id=None,
        domain=None,
        consumer_key=None,
        consumer_secret=None,
        privatekey_file=None,
        privatekey=None,
        ):
    """Return a tuple of `(session_id, sf_instance)` where `session_id` is the
    session ID to use for authentication to Salesforce and `sf_instance` is
    the domain of the instance of Salesforce to use for the session.

    Arguments:

    * username -- the Salesforce username to use for authentication
    * password -- the password for the username
    * security_token -- the security token for the username
    * organizationId -- the ID of your organization
            NOTE: security_token an organizationId are mutually exclusive
    * sf_version -- the version of the Salesforce API to use, for example
                    "27.0"
    * proxies -- the optional map of scheme to proxy server
    * session -- Custom requests session, created in calling code. This
                 enables the use of requets Session features not otherwise
                 exposed by simple_salesforce.
    * client_id -- the ID of this client
    * domain -- The domain to using for connecting to Salesforce. Use
                common domains, such as 'login' or 'test', or
                Salesforce My domain. If not used, will default to
                'login'.
    * consumer_key -- the consumer key generated for the user/app
    * consumer_secret -- the consumer secret generated for the user/app
    * privatekey_file -- the path to the private key file used
                         for signing the JWT token.
    * privatekey -- the private key to use
                         for signing the JWT token.
    """

    if domain is None:
        domain = 'login'

    if sf_version.startswith("v"):
        error_msg = (
            f"Invalid sf_version specified ({sf_version}). Version should not "
            "contain a leading 'v'"
        )
        raise ValueError(error_msg)

    if client_id:
        client_id = f'{DEFAULT_CLIENT_ID_PREFIX}/{client_id}'
    else:
        client_id = DEFAULT_CLIENT_ID_PREFIX

    # pylint: disable=E0012,deprecated-method
    username = escape(username) if username else None
    password = escape(password) if password else None

    # Check if token authentication is used
    if security_token is not None:
        # Security Token Soap request body
        login_soap_request_body = f"""<?xml version="1.0" encoding="utf-8" ?>
<env:Envelope
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="urn:partner.soap.sforce.com">
    <env:Header>
        <urn:CallOptions>
            <urn:client>{client_id}</urn:client>
            <urn:defaultNamespace>sf</urn:defaultNamespace>
        </urn:CallOptions>
    </env:Header>
    <env:Body>
        <n1:login xmlns:n1="urn:partner.soap.sforce.com">
            <n1:username>{username}</n1:username>
            <n1:password>{password}{security_token}</n1:password>
        </n1:login>
    </env:Body>
</env:Envelope>"""

    elif username is not None and \
            password is not None and \
            consumer_key is not None and \
            consumer_secret is not None:
        token_data = {
            'grant_type': 'password',
            'client_id': consumer_key,
            'client_secret': consumer_secret,
            'username': unescape(username),
            'password': unescape(password) if password else None
            }
        return token_login(
            f'https://{domain}.salesforce.com/services/oauth2/token',
            token_data, domain, consumer_key,
            None, proxies, session)

    # Check if IP Filtering is used in conjunction with organizationId
    elif organizationId is not None:
        # IP Filtering Login Soap request body
        login_soap_request_body = f"""<?xml version="1.0" encoding="utf-8" ?>
<soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="urn:partner.soap.sforce.com">
    <soapenv:Header>
        <urn:CallOptions>
            <urn:client>{client_id}</urn:client>
            <urn:defaultNamespace>sf</urn:defaultNamespace>
        </urn:CallOptions>
        <urn:LoginScopeHeader>
            <urn:organizationId>{organizationId}</urn:organizationId>
        </urn:LoginScopeHeader>
    </soapenv:Header>
    <soapenv:Body>
        <urn:login>
            <urn:username>{username}</urn:username>
            <urn:password>{password}</urn:password>
        </urn:login>
    </soapenv:Body>
</soapenv:Envelope>"""
    elif username is not None and password is not None:
        # IP Filtering for non self-service users
        login_soap_request_body = f"""<?xml version="1.0" encoding="utf-8" ?>
<soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="urn:partner.soap.sforce.com">
    <soapenv:Header>
        <urn:CallOptions>
            <urn:client>{client_id}</urn:client>
            <urn:defaultNamespace>sf</urn:defaultNamespace>
        </urn:CallOptions>
    </soapenv:Header>
    <soapenv:Body>
        <urn:login>
            <urn:username>{username}</urn:username>
            <urn:password>{password}</urn:password>
        </urn:login>
    </soapenv:Body>
</soapenv:Envelope>"""
    elif username is not None and \
            consumer_key is not None and \
            (privatekey_file is not None or privatekey is not None):
        expiration = datetime.now(timezone.utc) + timedelta(minutes=3)
        payload = {
            'iss': consumer_key,
            'sub': unescape(username),
            'aud': f'https://{domain}.salesforce.com',
            'exp': f'{expiration.timestamp():.0f}'
            }
        if privatekey_file is not None:
            key = Path(privatekey_file).read_bytes()
        else:
            key = privatekey
        assertion = jwt.encode(payload, key, algorithm='RS256')

        token_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
            }

        return token_login(
            f'https://{domain}.salesforce.com/services/oauth2/token',
            token_data, domain, consumer_key,
            None, proxies, session)
    elif consumer_key is not None and consumer_secret is not None and \
            domain is not None and domain not in ('login', 'test'):
        token_data = {'grant_type': 'client_credentials'}
        authorization = f'{consumer_key}:{consumer_secret}'
        encoded = base64.b64encode(authorization.encode()).decode()
        headers = {
            'Authorization': f'Basic {encoded}'
        }
        return token_login(
            f'https://{domain}.salesforce.com/services/oauth2/token',
            token_data, domain, consumer_key,
            headers, proxies, session)
    else:
        except_code = 'INVALID AUTH'
        except_msg = (
            'You must submit either a security token or organizationId for '
            'authentication'
        )
        raise SalesforceAuthenticationFailed(except_code, except_msg)

    soap_url = f'https://{domain}.salesforce.com/services/Soap/u/{sf_version}'
    login_soap_request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
        }

    return soap_login(soap_url, login_soap_request_body,
                      login_soap_request_headers, proxies, session)


def soap_login(soap_url, request_body, headers, proxies, session=None):
    """Process SOAP specific login workflow."""
    response = (session or requests).post(
        soap_url, request_body, headers=headers, proxies=proxies)

    if response.status_code != 200:
        except_code = getUniqueElementValueFromXmlString(
            response.content, 'sf:exceptionCode')
        except_msg = getUniqueElementValueFromXmlString(
            response.content, 'sf:exceptionMessage')
        raise SalesforceAuthenticationFailed(except_code, except_msg)

    session_id = getUniqueElementValueFromXmlString(
        response.content, 'sessionId')
    server_url = getUniqueElementValueFromXmlString(
        response.content, 'serverUrl')

    sf_instance = (server_url
                   .replace('http://', '')
                   .replace('https://', '')
                   .split('/')[0]
                   .replace('-api', ''))

    return session_id, sf_instance


def token_login(token_url, token_data, domain, consumer_key,
                headers, proxies, session=None):
    """Process OAuth 2.0 JWT Bearer Token Flow."""
    response = (session or requests).post(
        token_url, token_data, headers=headers, proxies=proxies)

    try:
        json_response = response.json()
    except JSONDecodeError as exc:
        raise SalesforceAuthenticationFailed(
            response.status_code, response.text
            ) from exc

    if response.status_code != 200:
        except_code = json_response.get('error')
        except_msg = json_response.get('error_description')
        if except_msg == "user hasn't approved this consumer":
            auth_url = f'https://{domain}.salesforce.com/services/oauth2/' \
                       'authorize?response_type=code&client_id=' \
                       f'{consumer_key}&redirect_uri=<approved URI>'
            warnings.warn(f"""
    If your connected app policy is set to "All users may
    self-authorize", you may need to authorize this
    application first. Browse to
    {auth_url}
    in order to Allow Access. Check first to ensure you have a valid
    <approved URI>.""")
        raise SalesforceAuthenticationFailed(except_code, except_msg)

    access_token = json_response.get('access_token')
    instance_url = json_response.get('instance_url')

    sf_instance = instance_url.replace(
        'http://', '').replace(
        'https://', '')

    return access_token, sf_instance
