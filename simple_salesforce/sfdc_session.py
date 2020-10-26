import re

from requests import Session
from xml.etree import ElementTree as ET


class SfdcSession(Session):
    _DEFAULT_API_VERSION = "43.0"
    _LOGIN_URL = "https://{instance}.salesforce.com"
    _SOAP_API_BASE_URI = "/services/Soap/c/{version}"
    _XML_NAMESPACES = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'mt': 'http://soap.sforce.com/2006/04/metadata',
        'd': 'urn:enterprise.soap.sforce.com'
    }

    _LOGIN_TMPL = \
        """<env:Envelope xmlns:xsd='http://www.w3.org/2001/XMLSchema'
xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
xmlns:env='http://schemas.xmlsoap.org/soap/envelope/'>
    <env:Body>
        <sf:login xmlns:sf='urn:enterprise.soap.sforce.com'>
            <sf:username>{username}</sf:username>
            <sf:password>{password}</sf:password>
        </sf:login>
    </env:Body>
</env:Envelope>"""

    def __init__(
            self, username=None, password=None, token=None,
            is_sandbox=False, api_version=_DEFAULT_API_VERSION,
            **kwargs):
        super(SfdcSession, self).__init__()
        self._username = username
        self._password = password
        self._token = token
        self._is_sandbox = is_sandbox
        self._api_version = api_version
        self._session_id = kwargs.get("session_id", None)
        self._instance = kwargs.get("instance", None)

    def login(self):
        url = self.construct_url(self.get_soap_api_uri())
        headers = {'Content-Type': 'text/xml', 'SOAPAction': 'login'}
        password = self._password
        if self._token:
            password += self._token
        data = SfdcSession._LOGIN_TMPL.format(**{'username': self._username, 'password': password})
        r = self.post(url, headers=headers, data=data)
        root = ET.fromstring(r.text)
        if root.find('soapenv:Body/soapenv:Fault', SfdcSession._XML_NAMESPACES):
            raise Exception("Could not log in. Code: %s Message: %s" % (
                root.find('soapenv:Body/soapenv:Fault/faultcode', SfdcSession._XML_NAMESPACES).text,
                root.find('soapenv:Body/soapenv:Fault/faultstring', SfdcSession._XML_NAMESPACES).text))
        self._session_id = root.find('soapenv:Body/d:loginResponse/d:result/d:sessionId',
                                     SfdcSession._XML_NAMESPACES).text
        server_url = root.find('soapenv:Body/d:loginResponse/d:result/d:serverUrl', SfdcSession._XML_NAMESPACES).text
        self._instance = re.search("""https://(.*).salesforce.com/.*""", server_url).group(1)

    def get_server_url(self):
        if not self._instance:
            url = SfdcSession._LOGIN_URL.format(**{'instance': 'test' if self._is_sandbox else 'login'})
        url = SfdcSession._LOGIN_URL.format(**{'instance': self._instance})
        if re.search(r'cloudforce', url):
            url = re.sub(r'\.salesforce\.com$', '', url)
        return url

    def get_soap_api_uri(self):
        return SfdcSession._SOAP_API_BASE_URI.format(**{'version': self._api_version})

    def construct_url(self, uri):
        return "%s%s" % (self.get_server_url(), uri)

    def get_api_version(self):
        return self._api_version

    def get_session_id(self):
        return self._session_id

    def is_connected(self):
        return True if self._instance else False
