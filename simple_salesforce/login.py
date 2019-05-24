"""Login classes and functions for Simple-Salesforce

Heavily Modified from RestForce 1.0.0
"""

DEFAULT_CLIENT_ID_PREFIX = 'RestForce'


from simple_salesforce.api import DEFAULT_API_VERSION
from simple_salesforce.util import getUniqueElementValueFromXmlString
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

try:
    # Python 3+
    from html import escape
    from json.decoder import JSONDecodeError
except ImportError:
    from cgi import escape
    JSONDecodeError = ValueError
import requests
import warnings
import time
from datetime import datetime, timedelta
from authlib.jose import jwt


# pylint: disable=invalid-name,too-many-arguments,too-many-locals
def SalesforceLogin(
        username=None, password=None, security_token=None,
        organizationId=None, sandbox=None, sf_version=DEFAULT_API_VERSION,
        proxies=None, session=None, client_id=None, domain=None,
        consumer_key=None, privatekey_file=None):
    """Return a tuple of `(session_id, sf_instance)` where `session_id` is the
    session ID to use for authentication to Salesforce and `sf_instance` is
    the domain of the instance of Salesforce to use for the session.

    Arguments:

    * username -- the Salesforce username to use for authentication
    * password -- the password for the username
    * security_token -- the security token for the username
    * organizationId -- the ID of your organization
            NOTE: security_token an organizationId are mutually exclusive
    * sandbox -- DEPRECATED: Use domain instead.
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
    * consumer_key -- the consumer key generated for the user
    * privatekey_file -- the path to the private key file used
                         for signing the JWT token
    """
    if (sandbox is not None) and (domain is not None):
        raise ValueError("Both 'sandbox' and 'domain' arguments were "
                         "supplied. Either may be supplied, but not "
                         "both.")

    if sandbox is not None:
        warnings.warn("'sandbox' argument is deprecated. Use "
                      "'domain' instead. Overriding 'domain' "
                      "with 'sandbox' value.",
                      DeprecationWarning)

        domain = 'test' if sandbox else 'login'

    if domain is None:
        domain = 'login'

    soap_url = 'https://{domain}.salesforce.com/services/Soap/u/{sf_version}'

    if client_id:
        client_id = "{prefix}/{app_name}".format(
            prefix=DEFAULT_CLIENT_ID_PREFIX,
            app_name=client_id)
    else:
        client_id = DEFAULT_CLIENT_ID_PREFIX

    soap_url = soap_url.format(domain=domain,
                               sf_version=sf_version)

    # pylint: disable=E0012,deprecated-method
    username = escape(username) if username else None
    password = escape(password) if password else None

    # Check if token authentication is used
    if security_token is not None:
        # Security Token Soap request body
        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
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
                    <n1:password>{password}{token}</n1:password>
                </n1:login>
            </env:Body>
        </env:Envelope>""".format(
            username=username, password=password, token=security_token,
            client_id=client_id)

    # Check if IP Filtering is used in conjunction with organizationId
    elif organizationId is not None:
        # IP Filtering Login Soap request body
        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
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
        </soapenv:Envelope>""".format(
            username=username, password=password, organizationId=organizationId,
            client_id=client_id)
    elif username is not None and password is not None:
        # IP Filtering for non self-service users
        login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
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
        </soapenv:Envelope>""".format(
            username=username, password=password, client_id=client_id)
    elif username is not None and \
            consumer_key is not None and \
            privatekey_file is not None:
        header = {'alg': 'RS256'}
        expiration = datetime.utcnow() + timedelta(minutes=3)
        payload = {
            'iss': consumer_key,
            'sub': username,
            'aud': 'https://{domain}.salesforce.com'.format(domain=domain),
            'exp': '{exp:.0f}'.format(
                exp=time.mktime(expiration.timetuple()) +
                    expiration.microsecond / 1e6
            )
        }
        with open(privatekey_file, 'rb') as key:
            assertion = jwt.encode(header, payload, key.read())

        login_token_request_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }

        return token_login(
            'https://{domain}.salesforce.com/services/oauth2/token'.format(
                domain=domain),
            login_token_request_data, domain, consumer_key,
            None, proxies, session)
    else:
        except_code = 'INVALID AUTH'
        except_msg = (
            'You must submit either a security token or organizationId for '
            'authentication'
        )
        raise SalesforceAuthenticationFailed(except_code, except_msg)

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
    except JSONDecodeError:
        raise SalesforceAuthenticationFailed(
            response.status_code, response.text
        )

    if response.status_code != 200:
        except_code = json_response.get('error')
        except_msg = json_response.get('error_description')
        if except_msg == "user hasn't approved this consumer":
            auth_url = 'https://{domain}.salesforce.com/services/oauth2/' \
                       'authorize?response_type=code&client_id=' \
                       '{consumer_key}&redirect_uri=<approved URI>'.format(
                            domain=domain,
                            consumer_key=consumer_key
                        )
            warnings.warn("""
    If your connected app policy is set to "All users may 
    self-authorize", you may need to authorize this 
    application first. Browse to 
    %s 
    in order to Allow Access. Check first to ensure you have a valid 
    <approved URI>.""" % auth_url)
        raise SalesforceAuthenticationFailed(except_code, except_msg)

    access_token = json_response.get('access_token')
    instance_url = json_response.get('instance_url')

    sf_instance = instance_url.replace(
        'http://', '').replace(
        'https://', '')

    return access_token, sf_instance
