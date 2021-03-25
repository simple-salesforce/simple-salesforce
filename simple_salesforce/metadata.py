""" Class to work with Salesforce Metadata API """
from base64 import b64encode, b64decode
from xml.etree import ElementTree as ET

import simple_salesforce.messages as msg


class SfdcMetadataApi:
    """ Class to work with Salesforce Metadata API """
    _METADATA_API_BASE_URI = "/services/Soap/m/{version}"
    _XML_NAMESPACES = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'mt': 'http://soap.sforce.com/2006/04/metadata'
    }

    def __init__(self, session):
        if not session.is_connected():
            raise Exception("Session must be connected prior to instantiating this class")
        self._session = session
        self._deploy_zip = None

    def _get_api_url(self):
        return "%s%s" % (
            self._session.get_server_url(),
            self._METADATA_API_BASE_URI.format(**{'version': self._session.get_api_version()}))

    def deploy(self, zipfile, options):
        """ Kicks off async deployment, returns deployment id """
        check_only = ""
        if 'checkonly' in options:
            check_only = "<met:checkOnly>%s</met:checkOnly>" % options['checkonly']

        test_level = ""
        if 'testlevel' in options:
            test_level = "<met:testLevel>%s</met:testLevel>" % options['testlevel']

        tests_tag = ""
        if 'tests' in options:
            for test in options['tests']:
                tests_tag += "<met:runTests>%s</met:runTests>\n" % test

        attributes = {
            'client': 'Metahelper',
            'checkOnly': check_only,
            'sessionId': self._session.get_session_id(),
            'ZipFile': self._read_deploy_zip(zipfile),
            'testLevel': test_level,
            'tests': tests_tag
        }

        request = msg.DEPLOY_MSG.format(**attributes)

        headers = {'Content-type': 'text/xml', 'SOAPAction': 'deploy'}
        res = self._session.post(self._get_api_url(), headers=headers, data=request)
        if res.status_code != 200:
            raise Exception(
                "Request failed with %d code and error [%s]" %
                (res.status_code, res.text))

        async_process_id = ET.fromstring(res.text).find(
            'soapenv:Body/mt:deployResponse/mt:result/mt:id',
            self._XML_NAMESPACES).text
        state = ET.fromstring(res.text).find(
            'soapenv:Body/mt:deployResponse/mt:result/mt:state',
            self._XML_NAMESPACES).text

        return async_process_id, state

    @staticmethod
    def _read_deploy_zip(zipfile):
        if hasattr(zipfile, 'read'):
            file = zipfile
            file.seek(0)
            should_close = False
        else:
            file = open(zipfile, 'rb')
            should_close = True
        raw = file.read()
        if should_close:
            file.close()
        return b64encode(raw).decode("utf-8")

    def _retrieve_deploy_result(self, async_process_id):
        """ Retrieves status for specified deployment id """
        attributes = {
            'client': 'Metahelper',
            'sessionId': self._session.get_session_id(),
            'asyncProcessId': async_process_id,
            'includeDetails': 'true'
            }
        mt_request = msg.CHECK_DEPLOY_STATUS_MSG.format(**attributes)
        headers = {'Content-type': 'text/xml', 'SOAPAction': 'checkDeployStatus'}
        res = self._session.post(self._get_api_url(), headers=headers, data=mt_request)
        root = ET.fromstring(res.text)
        result = root.find(
            'soapenv:Body/mt:checkDeployStatusResponse/mt:result',
            self._XML_NAMESPACES)
        if result is None:
            raise Exception("Result node could not be found: %s" % res.text)

        return result

    @staticmethod
    def get_component_error_count(value):
        try:
            return int(value)
        except ValueError:
            return 0

    def check_deploy_status(self, async_process_id):
        """ Checks whether deployment succeeded """
        result = self._retrieve_deploy_result(async_process_id)
        state = result.find('mt:status', self._XML_NAMESPACES).text
        state_detail = result.find('mt:stateDetail', self._XML_NAMESPACES)
        if state_detail is not None:
            state_detail = state_detail.text

        unit_test_errors = []
        deployment_errors = []
        failed_count = self.get_component_error_count(result.find('mt:numberComponentErrors', self._XML_NAMESPACES).text)
        if state == 'Failed' or failed_count > 0:
            # Deployment failures
            failures = result.findall('mt:details/mt:componentFailures', self._XML_NAMESPACES)
            for failure in failures:
                deployment_errors.append({
                    'type': failure.find('mt:componentType', self._XML_NAMESPACES).text,
                    'file': failure.find('mt:fileName', self._XML_NAMESPACES).text,
                    'status': failure.find('mt:problemType', self._XML_NAMESPACES).text,
                    'message': failure.find('mt:problem', self._XML_NAMESPACES).text
                    })
            # Unit test failures
            failures = result.findall(
                'mt:details/mt:runTestResult/mt:failures',
                self._XML_NAMESPACES)
            for failure in failures:
                unit_test_errors.append({
                    'class': failure.find('mt:name', self._XML_NAMESPACES).text,
                    'method': failure.find('mt:methodName', self._XML_NAMESPACES).text,
                    'message': failure.find('mt:message', self._XML_NAMESPACES).text,
                    'stack_trace': failure.find('mt:stackTrace', self._XML_NAMESPACES).text
                    })

        deployment_detail = {
            'total_count': result.find('mt:numberComponentsTotal', self._XML_NAMESPACES).text,
            'failed_count': result.find('mt:numberComponentErrors', self._XML_NAMESPACES).text,
            'deployed_count': result.find('mt:numberComponentsDeployed', self._XML_NAMESPACES).text,
            'rollbackOnError': result.find('mt:rollbackOnError', self._XML_NAMESPACES).text,
            'checkOnly': result.find('mt:rollbackOnCheckOnly', self._XML_NAMESPACES).text,
            'errors': deployment_errors
        }
        unit_test_detail = {
            'total_count': result.find('mt:numberTestsTotal', self._XML_NAMESPACES).text,
            'failed_count': result.find('mt:numberTestErrors', self._XML_NAMESPACES).text,
            'completed_count': result.find('mt:numberTestsCompleted', self._XML_NAMESPACES).text,
            'errors': unit_test_errors
        }

        return state, state_detail, deployment_detail, unit_test_detail

    def download_unit_test_logs(self, async_process_id):
        """ Downloads Apex logs for unit tests executed during specified deployment """
        result = self._retrieve_deploy_result(async_process_id)
        print("Results: %s" % ET.tostring(result, encoding="us-ascii", method="xml"))

    def retrieve(self, options):
        """ Submits retrieve request """
        # Compose unpackaged XML
        unpackaged = ''
        for metadata_type in options['unpackaged']:
            members = options['unpackaged'][metadata_type]
            unpackaged += '<types>'
            for member in members:
                unpackaged += '<members>{member}</members>'.format(member=member)
            unpackaged += '<name>{metadata_type}</name></types>'.format(metadata_type=metadata_type)
        # Compose retrieve request XML
        attributes = {
            'client': 'Metahelper',
            'sessionId': self._session.get_session_id(),
            'apiVersion': self._session.get_api_version(),
            'singlePackage': options['single_package'],
            'unpackaged': unpackaged
        }
        request = msg.RETRIEVE_MSG.format(**attributes)
        # Submit request
        headers = {'Content-type': 'text/xml', 'SOAPAction': 'retrieve'}
        res = self._session.post(self._get_api_url(), headers=headers, data=request)
        if res.status_code != 200:
            raise Exception(
                "Request failed with %d code and error [%s]" %
                (res.status_code, res.text))
        # Parse results to get async Id and status
        async_process_id = ET.fromstring(res.text).find(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:id',
            self._XML_NAMESPACES).text
        state = ET.fromstring(res.text).find(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:state',
            self._XML_NAMESPACES).text

        return async_process_id, state

    def retrieve_retrieve_result(self, async_process_id, include_zip):
        """ Retrieves status for specified retrieval id """
        attributes = {
            'client': 'Metahelper',
            'sessionId': self._session.get_session_id(),
            'asyncProcessId': async_process_id,
            'includeZip': include_zip
        }
        mt_request = msg.CHECK_RETRIEVE_STATUS_MSG.format(**attributes)
        headers = {'Content-type': 'text/xml', 'SOAPAction': 'checkRetrieveStatus'}
        res = self._session.post(self._get_api_url(), headers=headers, data=mt_request)
        root = ET.fromstring(res.text)
        result = root.find(
            'soapenv:Body/mt:checkRetrieveStatusResponse/mt:result',
            self._XML_NAMESPACES)
        if result is None:
            raise Exception("Result node could not be found: %s" % res.text)

        return result

    def retrieve_zip(self, async_process_id):
        """ Retrieves ZIP file """
        result = self._retrieve_retrieve_result(async_process_id, 'true')
        state = result.find('mt:status', self._XML_NAMESPACES).text
        error_message = result.find('mt:errorMessage', self._XML_NAMESPACES)
        if error_message is not None:
            error_message = error_message.text

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages', self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.find('mt:fileName', self._XML_NAMESPACES).text,
                'message': message.find('mt:problem', self._XML_NAMESPACES).text
            })

        # Retrieve base64 encoded ZIP file
        zipfile_base64 = result.find('mt:zipFile', self._XML_NAMESPACES).text
        zipfile = b64decode(zipfile_base64)

        return state, error_message, messages, zipfile

    def check_retrieve_status(self, async_process_id):
        """ Checks whether retrieval succeeded """
        result = self._retrieve_retrieve_result(async_process_id, 'false')
        state = result.find('mt:status', self._XML_NAMESPACES).text
        error_message = result.find('mt:errorMessage', self._XML_NAMESPACES)
        if error_message is not None:
            error_message = error_message.text

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages', self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.find('mt:fileName', self._XML_NAMESPACES).text,
                'message': message.find('mt:problem', self._XML_NAMESPACES).text
            })

        return state, error_message, messages
