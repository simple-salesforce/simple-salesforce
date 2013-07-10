'''
Heavily Modified from RestForce 1.0.0
'''

from simple_salesforce.util import getUniqueElementValueFromXmlString
import cgi
import requests


def SalesforceLogin(username, password, security_token, sandbox=False,
                    sf_version='23.0'):
    '''Return a tuple of `(session_id, sf_instance)` where `session_id` is the
    session ID to use for authentication to Salesforce and `sf_instance` is
    the domain of the instance of Salesforce to use for the session.

    Arguments:

    * username -- the Salesforce username to use for authentication
    * password -- the password for the username
    * security_token -- the security token for the username
    * sandbox -- True if you want to login to `test.salesforce.com`, False if
                 you want to login to `login.salesforce.com`.
    * sf_version -- the version of the Salesforce API to use, for example
                    "27.0"
    '''
    soap_url = 'https://{domain}.salesforce.com/services/Soap/u/{sf_version}'
    domain = 'test'
    if not sandbox:
        domain = 'login'
    soap_url = soap_url.format(domain=domain, sf_version=sf_version)

    username = cgi.escape(username)
    password = cgi.escape(password)
    login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
        <env:Envelope
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
            <env:Body>
                <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                    <n1:username>{username}</n1:username>
                    <n1:password>{password}{token}</n1:password>
                </n1:login>
            </env:Body>
        </env:Envelope>""".format(username=username, password=password, token=security_token)

    login_soap_request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
    }
    response = requests.post(soap_url, login_soap_request_body,
                             headers=login_soap_request_headers)

    if response.status_code != 200:
        except_code = getUniqueElementValueFromXmlString(response.content,
                                                         'sf:exceptionCode')
        except_msg = getUniqueElementValueFromXmlString(response.content,
                                                        'sf:exceptionMessage')
        raise SalesforceAuthenticationFailed('%s: %s' % (except_code,
                                                         except_msg))

    session_id = getUniqueElementValueFromXmlString(response.content,
                                                    'sessionId')
    server_url = getUniqueElementValueFromXmlString(response.content,
                                                    'serverUrl')
    sf_instance = (server_url
                   .replace('http://', '')
                   .replace('https://', '')
                   .split('/')[0]
                   .replace('-api', ''))

    return (session_id, sf_instance)


class SalesforceAuthenticationFailed(Exception):
    '''
    Thrown to indicate that authentication with Salesforce failed.
    '''
    pass
