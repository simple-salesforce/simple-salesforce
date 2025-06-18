""" Class to work with Salesforce Metadata API """

from base64 import b64encode, b64decode
from pathlib import Path
from typing import Any, Dict, IO, List, Mapping, Optional, Tuple, Union
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

import requests
from zeep.proxy import ServiceProxy
from zeep.xsd import AnySimpleType, ComplexType, CompoundValue

from .util import Headers, call_salesforce
from .messages import DEPLOY_MSG, CHECK_DEPLOY_STATUS_MSG, \
    CHECK_RETRIEVE_STATUS_MSG, RETRIEVE_MSG
from zeep import Client, Settings


class MetadataType:
    """
    Salesforce Metadata Type
    """
    def __init__(
            self,
            name: str,
            service: ServiceProxy,
            zeep_type: Union[ComplexType, AnySimpleType],
            session_header: CompoundValue):
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
    # pylint: disable=broad-exception-raised
    def _handle_api_response(response: List[Any]) -> None:
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
                err_string += f'\n{result.fullName}: '
                for error in result.errors:
                    err_string += f'({error.statusCode}, {error.message}), '
        if err_string:
            raise Exception(err_string)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Creates a new object of this metadata type

        :param args: Parameters to pass to zeep.xsd.AnySimpleType
        :param kwargs: Parameters to pass to zeep.xsd.ComplexType
        :returns: An object of type self._name
        """
        return self._zeep_type(*args, **kwargs)

    def create(self, metadata: List[Any]) -> None:
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

    def read(self, full_names: List[str]) -> Union[List[Any], Any]:
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

    def update(self, metadata: List[Any]) -> None:
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

    def upsert(self, metadata: List[Any]) -> None:
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
        response = self._service.upsertMetadata(metadata, _soapheaders=[
            self._session_header])
        self._handle_api_response(response)

    def delete(self, full_names: List[Dict[str, Any]]) -> None:
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

    def rename(self, old_full_name: str, new_full_name: str) -> None:
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

    def describe(self) -> Any:
        """
        Performs a describeValueType call

        :returns: DescribeValueTypeResult
        """
        return self._service.describeValueType(
            f'{{http://soap.sforce.com/2006/04/metadata}}{self._name}',
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
    def __init__(
            self,
            session: requests.Session,
            session_id: str,
            instance: str,
            metadata_url: str,
            headers: Headers,
            api_version: Optional[str]):
        """ Initialize and check session """
        self.session = session
        self._session_id = session_id
        self._instance = instance
        self.metadata_url = metadata_url
        self.headers = headers
        self._api_version = api_version
        self._deploy_zip = None
        wsdl_path = Path(__file__).parent / 'metadata.wsdl'
        self._client = Client(
            wsdl_path.absolute().as_uri(),
            settings=Settings(
                strict=False,
                xsd_ignore_sequence_order=True
            ))  # type: ignore[no-untyped-call]
        self._service = self._client.create_service(
            "{http://soap.sforce.com/2006/04/metadata}MetadataBinding",
            self.metadata_url)  # type: ignore[no-untyped-call]
        self._session_header = self._client.get_element(
            'ns0:SessionHeader'  # type: ignore[no-untyped-call]
        )(sessionId=self._session_id)

    def __getattr__(self, item: str) -> MetadataType:
        return MetadataType(
            item,
            self._service,
            self._client.get_type(
                'ns0:' + item),  # type: ignore[no-untyped-call]
            self._session_header)

    def describe_metadata(self) -> Any:
        """
        Performs a describeMetadata call

        :returns: An object of zeep.objects.DescribeMetadataResult
        """
        return self._service.describeMetadata(self._api_version, _soapheaders=[
            self._session_header])

    def list_metadata(self, queries: List[Any]) -> List[Any]:
        """
        Performs a listMetadata call

        :param queries: A list of zeep.objects.ListMetadataQuery that specify
        which components you are interested in.
                        Limit: 3
        :type queries: list
        :returns: List of zeep.objects.FileProperties objects
        :rtype: list
        """
        return self._service.listMetadata(  # type: ignore[no-any-return]
            queries,
            self._api_version,
            _soapheaders=[self._session_header])

    # pylint: disable=R0914
    # pylint: disable-msg=C0103
    def deploy(
            self,
            zipfile: Union[str, IO[bytes]],
            sandbox: bool,
            **kwargs: Any) -> Tuple[Optional[str], Optional[str]]:
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
            test_level = f'<met:testLevel>{testLevel}</met:testLevel>'
            attributes['testLevel'] = test_level

        tests_tag = ''
        if tests and \
                str(testLevel).lower() == 'runspecifiedtests':
            for test in tests:
                tests_tag += f'<met:runTests>{test}</met:runTests>\n'
            attributes['tests'] = tests_tag

        request = DEPLOY_MSG.format(**attributes)

        headers = {'Content-Type': 'text/xml', 'SOAPAction': 'deploy'}
        result = call_salesforce(url=self.metadata_url + 'deployRequest',
                                 method='POST',
                                 session=self.session,
                                 headers=self.headers,
                                 additional_headers=headers,
                                 data=request)

        async_process_id = ET.fromstring(result.text).findtext(
            'soapenv:Body/mt:deployResponse/mt:result/mt:id',
            None,
            self._XML_NAMESPACES) or None
        state = ET.fromstring(result.text).findtext(
            'soapenv:Body/mt:deployResponse/mt:result/mt:state',
            None,
            self._XML_NAMESPACES) or None

        return async_process_id, state

    @staticmethod
    # pylint: disable=R1732
    def _read_deploy_zip(zipfile: Union[str, IO[bytes]]) -> str:
        """
        :param zipfile:
        :type zipfile:
        :return:
        :rtype:
        """
        if hasattr(zipfile, 'read') and hasattr(zipfile, 'seek'):
            zipfile.seek(0)
            raw = zipfile.read()
        else:
            raw = Path(zipfile).read_bytes()
        return b64encode(raw).decode()

    # pylint: disable=broad-exception-raised
    def _retrieve_deploy_result(
            self,
            async_process_id: str,
            **kwargs: Any) -> Element:
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
            'Content-Type': 'text/xml', 'SOAPAction': 'checkDeployStatus'
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
            raise Exception(f"Result node could not be found: {res.text}")

        return result

    @staticmethod
    def get_component_error_count(value: str) -> int:
        """Get component error counts"""
        try:
            return int(value)
        except ValueError:
            return 0

    def check_deploy_status(
            self,
            async_process_id: str,
            **kwargs: Any
    ) -> Tuple[Optional[str],
                Optional[str],
                Optional[Mapping[str, Any]],
                Optional[Mapping[str, Any]]]:
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

        state = result.findtext(
            'mt:status', None, self._XML_NAMESPACES) or None
        state_detail = result.findtext(
            'mt:stateDetail', None, self._XML_NAMESPACES) or None

        unit_test_errors = []
        deployment_errors = []
        failed_count = self.get_component_error_count(
            result.findtext(
                'mt:numberComponentErrors', '', self._XML_NAMESPACES))
        if state == 'Failed' or failed_count > 0:
            # Deployment failures
            failures = result.findall('mt:details/mt:componentFailures',
                                      self._XML_NAMESPACES)
            for failure in failures:
                deployment_errors.append({
                    'type': failure.findtext(
                        'mt:componentType', None, self._XML_NAMESPACES) or None,
                    'file': failure.findtext(
                        'mt:fileName', None, self._XML_NAMESPACES) or None,
                    'status': failure.findtext(
                        'mt:problemType', None, self._XML_NAMESPACES) or None,
                    'message': failure.findtext(
                        'mt:problem', None, self._XML_NAMESPACES) or None
                    })
            # Unit test failures
            failures = result.findall(
                'mt:details/mt:runTestResult/mt:failures',
                self._XML_NAMESPACES)
            for failure in failures:
                unit_test_errors.append({
                    'class': failure.findtext(
                        'mt:name', None, self._XML_NAMESPACES) or None,
                    'method': failure.findtext(
                        'mt:methodName', None, self._XML_NAMESPACES) or None,
                    'message': failure.findtext(
                        'mt:message', None, self._XML_NAMESPACES) or None,
                    'stack_trace': failure.findtext(
                        'mt:stackTrace', None, self._XML_NAMESPACES) or None
                    })

        deployment_detail = {
            'total_count': result.findtext('mt:numberComponentsTotal',
                                           None,
                                           self._XML_NAMESPACES) or None,
            'failed_count': result.findtext('mt:numberComponentErrors',
                                            None,
                                            self._XML_NAMESPACES) or None,
            'deployed_count': result.findtext('mt:numberComponentsDeployed',
                                              None,
                                              self._XML_NAMESPACES) or None,
            'errors': deployment_errors
            }
        unit_test_detail = {
            'total_count': result.findtext('mt:numberTestsTotal',
                                           None,
                                           self._XML_NAMESPACES) or None,
            'failed_count': result.findtext('mt:numberTestErrors',
                                            None,
                                            self._XML_NAMESPACES) or None,
            'completed_count': result.findtext('mt:numberTestsCompleted',
                                               None,
                                               self._XML_NAMESPACES) or None,
            'errors': unit_test_errors
            }

        return state, state_detail, deployment_detail, unit_test_detail

    def download_unit_test_logs(self, async_process_id: str) -> None:
        """ Downloads Apex logs for unit tests executed during specified
        deployment """
        result = self._retrieve_deploy_result(async_process_id)
        print("response:", ET.tostring(result, encoding="us-ascii",
                                       method="xml"))

    def retrieve(
            self,
            async_process_id: str,
            **kwargs: Any) -> Tuple[Optional[str], Optional[str]]:
        """ Submits retrieve request """
        # Compose unpackaged XML
        client = kwargs.get('client', 'simple_salesforce_metahelper')
        single_package = kwargs.get('single_package', True)

        if not isinstance(single_package, bool):
            raise TypeError('single_package must be bool')

        unpackaged = ''
        if kwargs.get('unpackaged'):
            for metadata_type in kwargs.get('unpackaged', {}):
                if isinstance(kwargs.get('unpackaged'), dict):
                    members = kwargs.get('unpackaged', {})[metadata_type]
                    unpackaged += '<types>'
                    for member in members:
                        unpackaged += f'<members>{member}</members>'
                    unpackaged += f'<name>{metadata_type}</name></types>'
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
        headers = {'Content-Type': 'text/xml', 'SOAPAction': 'retrieve'}

        res = call_salesforce(
            url=self.metadata_url + 'deployRequest/' + async_process_id,
            method='POST',
            session=self.session,
            headers=self.headers,
            additional_headers=headers,
            data=request)

        # Parse response to get async Id and status
        async_process_id_ = ET.fromstring(res.text).findtext(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:id',
            None,
            self._XML_NAMESPACES) or None
        state = ET.fromstring(res.text).findtext(
            'soapenv:Body/mt:retrieveResponse/mt:result/mt:state',
            None,
            self._XML_NAMESPACES) or None

        return async_process_id_, state

    # pylint: disable=broad-exception-raised
    def retrieve_retrieve_result(
            self,
            async_process_id: str,
            include_zip: str,
            **kwargs: Any) -> Element:
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
            'Content-Type': 'text/xml', 'SOAPAction': 'checkRetrieveStatus'
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
            raise Exception(f"Result node could not be found: {res.text}")

        return result

    def retrieve_zip(
            self,
            async_process_id: str,
            **kwargs: Any
    ) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]], bytes]:
        """ Retrieves ZIP file """
        result = self.retrieve_retrieve_result(async_process_id, 'true',
                                               **kwargs)
        state = result.findtext('mt:status', None, self._XML_NAMESPACES) or None
        error_message = result.findtext(
            'mt:errorMessage', None, self._XML_NAMESPACES)

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages',
                                      self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.findtext(
                    'mt:fileName', None, self._XML_NAMESPACES) or None,
                'message': message.findtext(
                    'mt:problem', None, self._XML_NAMESPACES) or None
                })

        # Retrieve base64 encoded ZIP file
        zipfile_base64 = result.findtext(
            'mt:zipFile', None, self._XML_NAMESPACES
        ) or None
        zipfile = b64decode(zipfile_base64)  # type: ignore[arg-type]

        return state, error_message, messages, zipfile

    def check_retrieve_status(
            self,
            async_process_id: str,
            **kwargs: Any
    ) -> Tuple[Optional[str], Optional[str], List[Dict[str, Optional[str]]]]:
        """ Checks whether retrieval succeeded """
        result = self.retrieve_retrieve_result(async_process_id, 'false',
                                               **kwargs)
        state = result.findtext('mt:status', None, self._XML_NAMESPACES) or None
        error_message = result.findtext(
            'mt:errorMessage', None, self._XML_NAMESPACES)

        # Check if there are any messages
        messages = []
        message_list = result.findall('mt:details/mt:messages',
                                      self._XML_NAMESPACES)
        for message in message_list:
            messages.append({
                'file': message.findtext(
                    'mt:fileName', None, self._XML_NAMESPACES) or None,
                'message': message.findtext(
                    'mt:problem', None, self._XML_NAMESPACES) or None
                })

        return state, error_message, messages
