""" Class to work with Salesforce Metadata API """
import os
from base64 import b64encode, b64decode
from xml.etree import ElementTree as ET
from .util import call_salesforce
from .messages import DEPLOY_MSG, CHECK_DEPLOY_STATUS_MSG, \
    CHECK_RETRIEVE_STATUS_MSG, RETRIEVE_MSG
from zeep import Client, Settings


class MetadataType:
    """
    Salesforce Metadata Type
    """
    def __init__(self, name, service, zeep_type, session_header):
        """
        Initialize metadata type

        :param name: Name of metadata type
        :type name: str
        :param service: Zeep service
        :type service: zeep.proxy.ServiceProxy
        :param zeep_type: Zeep type object
        :type zeep_type: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType
        :param session_header: Session Id header for Metadata API calls
        """
        self._name = name
        self._service = service
        self._zeep_type = zeep_type
        self._session_header = session_header

    @staticmethod
    def _handle_api_response(response):
        """
        Parses SaveResult and DeleteResult objects to identify if there was
        an error, and raises exception accordingly

        :param response: List of zeep.objects.SaveResult or
        zeep.objects.DeleteResult objects
        :type response: list
        :raises Exception: If any Result object contains one or more error
        messages
        """
        err_string = ""
        for result in response:
            if not result.success:
                err_string += "\n{}: ".format(result.fullName)
                for error in result.errors:
                    err_string += "({}, {}), ".format(error.statusCode,
                                                      error.message)
        if err_string:
            raise Exception(err_string)

    def __call__(self, *args, **kwargs):
        """
        Creates a new object of this metadata type

        :param args: Parameters to pass to zeep.xsd.AnySimpleType
        :param kwargs: Parameters to pass to zeep.xsd.ComplexType
        :returns: An object of type self._name
        """
        return self._zeep_type(*args, **kwargs)

    def create(self, metadata):
        """
        Performs a createMetadata call

        :param metadata: Array of one or more metadata components.
                         Limit: 10. (For CustomMetadata and CustomApplication
                         only, the limit is 200.)
                         You must submit arrays of only one type of
                         component. For example, you can submit an
                         array of 10 custom objects or 10 profiles, but not a
                         mix of both types.
        :type metadata: list
        """
        response = self._service.createMetadata(metadata, _soapheaders=[
            self._session_header])
        self._handle_api_response(response)

    def read(self, full_names):
        """
        Performs a readMetadata call

        :param full_names: Array of full names of the components to read.
                           Limit: 10. (For CustomMetadata and
                           CustomApplication only, the limit is 200.)
                           You must submit arrays of only one type of
                           component. For example, you can submit an array
                           of 10 custom objects or 10 profiles, but not a mix
                           of both types.
        :type full_names: list
        :returns: A list of metadata components
        :rtype: list
        """
        response = self._service.readMetadata(self._name, full_names,
                                              _soapheaders=[
                                                  self._session_header])
        if len(response) == 1:
            return response[0]
        return response

    def update(self, metadata):
        """
        Performs an updateMetadata call. All required fields must be passed
        for each component

        :param metadata: Array of one or more metadata components.
                         Limit: 10. (For CustomMetadata and CustomApplication
                         only, the limit is 200.)
                         You must submit arrays of only one type of
                         component. For example, you can submit an
                         array of 10 custom objects or 10 profiles, but not a
                         mix of both types.
        :type metadata: list
        """
        response = self._service.updateMetadata(metadata, _soapheaders=[
            self._session_header])
        self._handle_api_response(response)

    def upsert(self, metadata):
        """
        Performs an upsertMetadata call. All required fields must be passed
        for each component

        :param metadata: Array of one or more metadata components.
                         Limit: 10. (For CustomMetadata and CustomApplication
                         only, the limit is 200.)
                         You must submit arrays of only one type of
                         component. For example, you can submit an
                         array of 10 custom objects or 10 profiles, but not a
                         mix of both types.
        :type metadata: list
        """
        response = self._service.updateMetadata(metadata, _soapheaders=[
            self._session_header])
        self._handle_api_response(response)

    def delete(self, full_names):
        """
        Performs a deleteMetadata call

        :param full_names: Array of full names of the components to delete.
                           Limit: 10. (For CustomMetadata and
                           CustomApplication only, the limit is 200.)
                           You must submit arrays of only one type of
                           component. For example, you can submit an array
                           of 10 custom objects or 10 profiles, but not a mix
                           of both types.
        :type full_names: list
        """
        response = self._service.deleteMetadata(self._name, full_names,
                                                _soapheaders=[
                                                    self._session_header])
        self._handle_api_response(response)

    def rename(self, old_full_name, new_full_name):
        """
        Performs a renameMetadata call

        :param old_full_name: The current component full name.
        :type old_full_name: str
        :param new_full_name: The new component full name.
        :type new_full_name: str
        """
        result = self._service.renameMetadata(self._name, old_full_name,
                                              new_full_name,
                                              _soapheaders=[
                                                  self._session_header])
        self._handle_api_response([result])

    def describe(self):
        """
        Performs a describeValueType call

        :returns: DescribeValueTypeResult
        """
        return self._service.describeValueType(
            "{{http://soap.sforce.com/2006/04/metadata}}{}".format(self._name),
            _soapheaders=[self._session_header])


class SfdcMetadataApi:
    # pylint: disable=too-many-instance-attributes
    """ Class to work with Salesforce Metadata API """
    _METADATA_API_BASE_URI = "/services/Soap/m/{version}"
    _XML_NAMESPACES = {
        'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
        'mt': 'http://soap.sforce.com/2006/04/metadata'
        }

    # pylint: disable=R0913
    def __init__(self, session, session_id, instance, metadata_url, headers,
                 api_version):
        """ Initialize and check session """
        self.session = session
        self._session_id = session_id
        self._instance = instance
        self.metadata_url = metadata_url
        self.headers = headers
        self._api_version = api_version
        self._deploy_zip = None
        wsdl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'metadata.wsdl')
        self._client = Client(os.path.join('simple_salesforce', wsdl_path),
                              settings=Settings(strict=False,
                                                xsd_ignore_sequence_order=True))
        self._service = self._client.create_service(
            "{http://soap.sforce.com/2006/04/metadata}MetadataBinding",
            self.metadata_url)
        self._session_header = self._client.get_element('ns0:SessionHeader')(
            sessionId=self._session_id)

    def __getattr__(self, item):
        return MetadataType(item, self._service,
                            self._client.get_type('ns0:' + item),
                            self._session_header)

    def describe_metadata(self):
        """
        Performs a describeMetadata call

        :returns: An object of zeep.objects.DescribeMetadataResult
        """
        return self._service.describeMetadata(self._api_version, _soapheaders=[
            self._session_header])

    def list_metadata(self, queries):
        """
        Performs a listMetadata call

        :param queries: A list of zeep.objects.ListMetadataQuery that specify
        which components you are interested in.
                        Limit: 3
        :type queries: list
        :returns: List of zeep.objects.FileProperties objects
        :rtype: list
        """
        return self._service.listMetadata(queries, self._api_version,
                                          _soapheaders=[self._session_header])

    # pylint: disable=R0914
    # pylint: disable-msg=C0103
    def deploy(self, zipfile, sandbox, **kwargs):
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

        if not sandbox:
            attributes['allowMissingFiles'] = False
            attributes['rollbackOnError'] = True

        if testLevel:
            test_level = "<met:testLevel>%s</met:testLevel>" % testLevel
            attributes['testLevel'] = test_level

        tests_tag = ''
        if tests and \
                str(testLevel).lower() == 'runspecifiedtests':
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
    # pylint: disable=R1732
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
        print("response: %s" % ET.tostring(result, encoding="us-ascii",
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
                if isinstance(kwargs.get('unpackaged'), dict):
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

        # Parse response to get async Id and status
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
        result = self.retrieve_retrieve_result(async_process_id, 'true',
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
        result = self.retrieve_retrieve_result(async_process_id, 'false',
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
