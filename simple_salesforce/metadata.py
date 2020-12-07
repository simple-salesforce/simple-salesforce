""" Class to work with Salesforce Metadata API """
from base64 import b64encode, b64decode
from xml.etree import ElementTree as ET
from .util import call_salesforce
from .messages import DEPLOY_MSG,CHECK_DEPLOY_STATUS_MSG,\
    CHECK_RETRIEVE_STATUS_MSG,RETRIEVE_MSG


class SfdcMetadataApi:
    # pylint: disable=too-many-instance-attributes
    """ Class to work with Salesforce Metadata API """
    _METADATA_API_BASE_URI = "/services/Soap/m/{version}"
    _XML_NAMESPACES = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'mt': 'http://soap.sforce.com/2006/04/metadata'
        }

    # pylint: disable=R0913
    def __init__(self, session, session_id, instance, sandbox, metadata_url,
                 headers, api_version):
        """ Initialize and check session """
        self.session = session
        self._session_id = session_id
        self._instance = instance
        self._sandbox = sandbox
        self.metadata_url = metadata_url
        self.headers = headers
        self._api_version = api_version
        self._deploy_zip = None

    # pylint: disable=R0914
    # pylint: disable-msg=C0103
    def deploy(self, zipfile, **kwargs):
        """ Kicks off async deployment, returns deployment id
        :param zipfile:
        :type zipfile:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        client = kwargs.get('client', 'simple_salesforce_metahelper')
        checkOnly = kwargs.get('checkOnly', False)
        testLevel = kwargs.get('testLevel')
        tests = kwargs.get('tests')
        ignoreWarnings = kwargs.get('ignoreWarnings', False)
        allowMissingFiles = kwargs.get('allowMissingFiles', False)
        autoUpdatePackage = kwargs.get('autoUpdatePackage', False)
        performRetrieve = kwargs.get('performRetrieve', False)
        purgeOnDelete = kwargs.get('purgeOnDelete', False)
        rollbackOnError = kwargs.get('rollbackOnError', False)
        singlePackage = True

        attributes = {
            'client': client,
            'checkOnly': checkOnly,
            'sessionId': self._session_id,
            'ZipFile': self._read_deploy_zip(zipfile),
            'testLevel': testLevel,
            'tests': tests,
            'ignoreWarnings': ignoreWarnings,
            'allowMissingFiles': allowMissingFiles,
            'autoUpdatePackage': autoUpdatePackage,
            'performRetrieve': performRetrieve,
            'purgeOnDelete': purgeOnDelete,
            'rollbackOnError': rollbackOnError,
            'singlePackage': singlePackage,
            }

        if not self._sandbox:
            attributes['allowMissingFiles'] = False
            attributes['rollbackOnError'] = True

        if testLevel:
            test_level = "<met:testLevel>%s</met:testLevel>" % testLevel
            attributes['testLevel'] = test_level

        tests_tag = ''
        if tests and \
                str(tests).lower() == 'runspecifiedtests':
            for test in tests:
                tests_tag += '<met:runTests>%s</met:runTests>\n' % test
            attributes['tests'] = tests_tag

        request = DEPLOY_MSG.format(**attributes)

        headers = {'Content-Type': 'text/xml', 'SOAPAction': 'deploy'}
        result = call_salesforce(url=self.metadata_url + 'deployRequest',
                                 method='POST',
                                 session=self.session,
                                 headers=self.headers,
                                 additional_headers=headers,
                                 data=request)

        async_process_id = ET.fromstring(result.text).find(
            'soapenv:Body/mt:deployResponse/mt:result/mt:id',
            self._XML_NAMESPACES).text
        state = ET.fromstring(result.text).find(
            'soapenv:Body/mt:deployResponse/mt:result/mt:state',
            self._XML_NAMESPACES).text

        return async_process_id, state

    @staticmethod
    def _read_deploy_zip(zipfile):
        """
        :param zipfile:
        :type zipfile:
        :return:
        :rtype:
        """
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

    def _retrieve_deploy_result(self, async_process_id, **kwargs):
        """ Retrieves status for specified deployment id
        :param async_process_id:
        :type async_process_id:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        client = kwargs.get('client', 'simple_salesforce_metahelper')

        attributes = {
            'client': client,
            'sessionId': self._session_id,
            'asyncProcessId': async_process_id,
            'includeDetails': 'true'
            }
        mt_request = CHECK_DEPLOY_STATUS_MSG.format(**attributes)
        headers = {
            'Content-type': 'text/xml', 'SOAPAction': 'checkDeployStatus'
            }

        res = call_salesforce(
            url=self.metadata_url + 'deployRequest/' + async_process_id,
            method='POST',
            session=self.session,
            headers=self.headers,
            additional_headers=headers,
            data=mt_request)

        root = ET.fromstring(res.text)
        result = root.find(
            'soapenv:Body/mt:checkDeployStatusResponse/mt:result',
            self._XML_NAMESPACES)
        if result is None:
            raise Exception("Result node could not be found: %s" % res.text)

        return result

    @staticmethod
    def get_component_error_count(value):
        """Get component error counts"""
        try:
            return int(value)
        except ValueError:
            return 0

    def check_deploy_status(self, async_process_id, **kwargs):
        """
        Checks whether deployment succeeded
        :param async_process_id:
        :type async_process_id:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        result = self._retrieve_deploy_result(async_process_id, **kwargs)

        state = result.find('mt:status', self._XML_NAMESPACES).text
        state_detail = result.find('mt:stateDetail', self._XML_NAMESPACES)
        if state_detail is not None:
            state_detail = state_detail.text

        unit_test_errors = []
        deployment_errors = []
        failed_count = self.get_component_error_count(
            result.find('mt:numberComponentErrors', self._XML_NAMESPACES).text)
        if state == 'Failed' or failed_count > 0:
            # Deployment failures
            failures = result.findall('mt:details/mt:componentFailures',
                                      self._XML_NAMESPACES)
            for failure in failures:
                deployment_errors.append({
                    'type': failure.find('mt:componentType',
                                         self._XML_NAMESPACES).text,
                    'file': failure.find('mt:fileName',
                                         self._XML_NAMESPACES).text,
                    'status': failure.find('mt:problemType',
                                           self._XML_NAMESPACES).text,
                    'message': failure.find('mt:problem',
                                            self._XML_NAMESPACES).text
                    })
            # Unit test failures
            failures = result.findall(
                'mt:details/mt:runTestResult/mt:failures',
                self._XML_NAMESPACES)
            for failure in failures:
                unit_test_errors.append({
                    'class': failure.find('mt:name', self._XML_NAMESPACES).text,
                    'method': failure.find('mt:methodName',
                                           self._XML_NAMESPACES).text,
                    'message': failure.find('mt:message',
                                            self._XML_NAMESPACES).text,
                    'stack_trace': failure.find('mt:stackTrace',
                                                self._XML_NAMESPACES).text
                    })

        deployment_detail = {
            'total_count': result.find('mt:numberComponentsTotal',
                                       self._XML_NAMESPACES).text,
            'failed_count': result.find('mt:numberComponentErrors',
                                        self._XML_NAMESPACES).text,
            'deployed_count': result.find('mt:numberComponentsDeployed',
                                          self._XML_NAMESPACES).text,
            'errors': deployment_errors
            }
        unit_test_detail = {
            'total_count': result.find('mt:numberTestsTotal',
                                       self._XML_NAMESPACES).text,
            'failed_count': result.find('mt:numberTestErrors',
                                        self._XML_NAMESPACES).text,
            'completed_count': result.find('mt:numberTestsCompleted',
                                           self._XML_NAMESPACES).text,
            'errors': unit_test_errors
            }

        return state, state_detail, deployment_detail, unit_test_detail

    def download_unit_test_logs(self, async_process_id):
        """ Downloads Apex logs for unit tests executed during specified
        deployment """
        result = self._retrieve_deploy_result(async_process_id)
        print("Results: %s" % ET.tostring(result, encoding="us-ascii",
                                          method="xml"))

    def retrieve(self, async_process_id, **kwargs):
        """ Submits retrieve request """
        # Compose unpackaged XML
        client = kwargs.get('client', 'simple_salesforce_metahelper')
        single_package = kwargs.get('single_package', True)

        if not isinstance(single_package, bool):
            raise TypeError('single_package must be bool')

        unpackaged = ''
        if kwargs.get('unpackaged'):
            for metadata_type in kwargs.get('unpackaged'):
                if isinstance(metadata_type, dict):
                    members = kwargs.get('unpackaged')[metadata_type]
                    unpackaged += '<types>'
                    for member in members:
                        unpackaged += '<members>{member}</members>'.format(
                            member=member)
                    unpackaged += '<name>{metadata_type}</name></types>'.format(
                        metadata_type=metadata_type)
                else:
                    raise TypeError('unpackaged metadata types must be a dict')

        # Compose retrieve request XML
        attributes = {
            'client': client,
            'sessionId': self._session_id,
            'apiVersion': self._api_version,
            'singlePackage': single_package,
            'unpackaged': unpackaged
            }
        request = RETRIEVE_MSG.format(**attributes)
        # Submit request
        headers = {'Content-type': 'text/xml', 'SOAPAction': 'retrieve'}

        res = call_salesforce(
            url=self.metadata_url + 'deployRequest/' + async_process_id,
            method='POST',
            session=self.session,
            headers=self.headers,
            additional_headers=headers,
            data=request)

        # Parse results to get async Id and status
        async_process_id = ET.fromstring(res.text).find(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:id',
            self._XML_NAMESPACES).text
        state = ET.fromstring(res.text).find(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:state',
            self._XML_NAMESPACES).text

        return async_process_id, state

    def retrieve_retrieve_result(self, async_process_id, include_zip, **kwargs):
        """ Retrieves status for specified retrieval id """
        client = kwargs.get('client', 'simple_salesforce_metahelper')
        attributes = {
            'client': client,
            'sessionId': self._session_id,
            'asyncProcessId': async_process_id,
            'includeZip': include_zip
            }
        mt_request = CHECK_RETRIEVE_STATUS_MSG.format(**attributes)
        headers = {
            'Content-type': 'text/xml', 'SOAPAction': 'checkRetrieveStatus'
            }
        res = call_salesforce(
            url=self.metadata_url + 'deployRequest/' + async_process_id,
            method='POST',
            session=self.session,
            headers=self.headers,
            additional_headers=headers,
            data=mt_request)

        root = ET.fromstring(res.text)
        result = root.find(
            'soapenv:Body/mt:checkRetrieveStatusResponse/mt:result',
            self._XML_NAMESPACES)
        if result is None:
            raise Exception("Result node could not be found: %s" % res.text)

        return result

    def retrieve_zip(self, async_process_id, **kwargs):
        """ Retrieves ZIP file """
        result = self._retrieve_retrieve_result(async_process_id, 'true',
                                                **kwargs)
        state = result.find('mt:status', self._XML_NAMESPACES).text
        error_message = result.find('mt:errorMessage', self._XML_NAMESPACES)
        if error_message is not None:
            error_message = error_message.text

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages',
                                      self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.find('mt:fileName', self._XML_NAMESPACES).text,
                'message': message.find('mt:problem', self._XML_NAMESPACES).text
                })

        # Retrieve base64 encoded ZIP file
        zipfile_base64 = result.find('mt:zipFile', self._XML_NAMESPACES).text
        zipfile = b64decode(zipfile_base64)

        return state, error_message, messages, zipfile

    def check_retrieve_status(self, async_process_id, **kwargs):
        """ Checks whether retrieval succeeded """
        result = self._retrieve_retrieve_result(async_process_id, 'false',
                                                **kwargs)
        state = result.find('mt:status', self._XML_NAMESPACES).text
        error_message = result.find('mt:errorMessage', self._XML_NAMESPACES)
        if error_message is not None:
            error_message = error_message.text

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages',
                                      self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.find('mt:fileName', self._XML_NAMESPACES).text,
                'message': message.find('mt:problem', self._XML_NAMESPACES).text
                })

        return state, error_message, messages
