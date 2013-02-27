'''
Heavily Modified from RestForce 1.0.0
'''

from util import getUniqueElementValueFromXmlString
import requests


def login(username, password, securityToken, sandbox=False,
          sf_version='23.0'):
    soapUrl = 'https://{domain}.salesforce.com/services/Soap/u/{sf_version}'
    domain = 'test'
    if not sandbox:
        domain = 'login'
    soapUrl = soapUrl.format(domain=domain, sf_version=sf_version)

    loginSoapRequestBody = """<?xml version="1.0" encoding="utf-8" ?>
        <env:Envelope
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
            <env:Body>
                <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                    <n1:username>%s</n1:username>
                    <n1:password>%s%s</n1:password>
                </n1:login>
            </env:Body>
        </env:Envelope>""" % (username, password, securityToken)

    loginSoapRequestHeaders = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
    }
    response = requests.post(soapUrl, loginSoapRequestBody,
                             headers=loginSoapRequestHeaders)

    if response.status_code != 200:
        except_code = getUniqueElementValueFromXmlString(response.content,
                                                         'sf:exceptionCode')
        except_msg = getUniqueElementValueFromXmlString(response.content,
                                                        'sf:exceptionMessage')
        raise SalesforceAuthenticationFailed('%s: %s' % (except_code,
                                                         except_msg))

    sessionId = getUniqueElementValueFromXmlString(response.content,
                                                   'sessionId')
    serverUrl = getUniqueElementValueFromXmlString(response.content,
                                                   'serverUrl')
    sfInstance = (serverUrl
                  .replace('http://', '')
                  .replace('https://', '')
                  .split('/')[0]
                  .replace('-api', ''))

    return (sessionId, sfInstance)


class SalesforceAuthenticationFailed(Exception):
    '''
    Thrown to indicate that authentication with Salesforce failed.
    '''
    pass
