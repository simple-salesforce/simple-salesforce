"""Core classes and exceptions for Simple-Salesforce"""

from datetime import datetime

# has to be defined prior to login import
DEFAULT_API_VERSION = '59.0'
import base64
import json
import logging
import re
from typing import Any, Callable, Dict, IO, Iterator, List, Mapping, \
    MutableMapping, \
    Optional, Tuple, Union, cast
from collections import OrderedDict
from functools import partial
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote_plus
import requests
from .bulk import SFBulkHandler
from .bulk2 import SFBulk2Handler
from .exceptions import SalesforceGeneralError
from .login import SalesforceLogin
from .metadata import SfdcMetadataApi
from .util import Headers, PerAppUsage, Proxies, Usage, date_to_iso8601, \
    exception_handler

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Salesforce:
    """Salesforce Instance
    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    _parse_float = None
    _object_pairs_hook = OrderedDict

    # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements,line-too-long
    def __init__(
            self,
            username: Optional[str] = None,
            password: Optional[str] = None,
            security_token: Optional[str] = None,
            session_id: Optional[str] = None,
            instance: Optional[str] = None,
            instance_url: Optional[str] = None,
            organizationId: Optional[str] = None,
            version: Optional[str] = DEFAULT_API_VERSION,
            proxies: Optional[Proxies] = None,
            session: Optional[requests.Session] = None,
            client_id: Optional[str] = None,
            domain: Optional[str] = None,
            consumer_key: Optional[str] = None,
            consumer_secret: Optional[str] = None,
            privatekey_file: Optional[str] = None,
            privatekey: Optional[str] = None,
            parse_float: Optional[Callable[[str], Any]] = None,
            object_pairs_hook: Optional[Callable[[List[Tuple[Any, Any]]], Any]]
            = OrderedDict,
            ):

        """Initialize the instance with the given parameters.
        Available kwargs
        Password Authentication:
        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * domain -- The domain to using for connecting to Salesforce. Use
                    common domains, such as 'login' or 'test', or
                    Salesforce My domain. If not used, will default to
                    'login'.

        OAuth 2.0 Connected App Token Authentication:
        * consumer_key -- the consumer key generated for the user
        * consumer_secret -- the consumer secret generated for the user

        OAuth 2.0 JWT Bearer Token Authentication:
        * consumer_key -- the consumer key generated for the user

        Then either
        * privatekey_file -- the path to the private key file used
                             for signing the JWT token
        OR
        * privatekey -- the private key to use
                         for signing the JWT token

        Direct Session and Instance Access:

        * session_id -- Access token for this session

        Then either
        * instance -- Domain of your Salesforce instance, i.e.
          `na1.salesforce.com`
        OR
        * instance_url -- Full URL of your instance i.e.
          `https://na1.salesforce.com

        Universal Kwargs:
        * version -- the version of the Salesforce API to use, for example
                     `29.0`
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        * parse_float -- Function to parse float values with. Is passed along to
                         https://docs.python.org/3/library/json.html#json.load
        * object_pairs_hook -- Function to parse ordered list of pairs in json.
                               To use python 'dict' change it to None or dict.
        """

        if domain is None:
            domain = 'login'

        # Determine if the user passed in the optional version and/or
        # domain kwargs
        self.sf_version = version
        self.domain = domain
        self.session = session or requests.Session()
        self.proxies = self.session.proxies
        self._salesforce_login_partial = None
        # override custom session proxies dance
        if proxies is not None:
            if not session:
                self.session.proxies = self.proxies = proxies
            else:
                logger.warning(
                    'Proxies must be defined on custom session object, '
                    'ignoring proxies: %s',
                    proxies
                    )

        # Determine if the user wants to use our username/password auth or pass
        # in their own information
        if all(arg is not None for arg in (
                username, password, security_token)
               ):
            self.auth_type = "password"

            # Pass along the username/password to our login helper
            self._salesforce_login_partial = partial(
                SalesforceLogin,
                session=self.session,
                username=username,
                password=password,
                security_token=security_token,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id,
                domain=self.domain
                )
            self._refresh_session()

        elif all(arg is not None for arg in (
                session_id, instance or instance_url)
                 ):
            self.auth_type = "direct"
            self.session_id: str = cast(str,
                                        session_id
                                        )

            # If the user provides the full url (as returned by the OAuth
            # interface for example) extract the hostname (which we rely on)
            if instance_url is not None:
                self.sf_instance: str = urlparse(
                    instance_url
                    ).hostname  # type: ignore[assignment]
                port = urlparse(instance_url).port
                if port not in (None, 443):
                    self.sf_instance += f':{port}'
            else:
                self.sf_instance = cast(str,
                                        instance
                                        )

            # Only generate the headers wihtout logging in first
            self._generate_headers()

        elif all(arg is not None for arg in (
                username, password, organizationId)
                 ):
            self.auth_type = 'ipfilter'

            # Pass along the username/password to our login helper
            self._salesforce_login_partial = partial(
                SalesforceLogin,
                session=self.session,
                username=username,
                password=password,
                organizationId=organizationId,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id,
                domain=self.domain
                )
            self._refresh_session()

        elif all(arg is not None for arg in (
                username, password, consumer_key, consumer_secret)
                 ):
            self.auth_type = "password"

            # Pass along the username/password to our login helper
            self._salesforce_login_partial = partial(
                SalesforceLogin,
                session=self.session,
                username=username,
                password=password,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                proxies=self.proxies,
                domain=self.domain
                )
            self._refresh_session()

        elif all(arg is not None for arg in (
                username, consumer_key, privatekey_file or privatekey)
                 ):
            self.auth_type = "jwt-bearer"

            # Pass along the username/password to our login helper
            self._salesforce_login_partial = partial(
                SalesforceLogin,
                session=self.session,
                username=username,
                instance_url=instance_url,
                consumer_key=consumer_key,
                privatekey_file=privatekey_file,
                privatekey=privatekey,
                proxies=self.proxies,
                domain=self.domain
                )
            self._refresh_session()
        elif all(arg is not None for arg in (
                consumer_key, consumer_secret, domain
                )
                 ):
            self.auth_type = "client-credentials"
            self._salesforce_login_partial = partial(
                SalesforceLogin,
                session=self.session,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                proxies=self.proxies,
                domain=self.domain
                )
            self._refresh_session()
        else:
            raise TypeError(
                'You must provide login information or an instance and token'
                )

        self.auth_site = f'https://{self.domain}.salesforce.com'

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
            }

        self.base_url = (
            f'https://{self.sf_instance}/services/data/v{self.sf_version}/')
        self.apex_url = f'https://{self.sf_instance}/services/apexrest/'
        self.bulk_url = (
            f'https://{self.sf_instance}/services/async/{self.sf_version}/')
        self.bulk2_url = (
            f'https://{self.sf_instance}/services/data/v{self.sf_version}/jobs/'
        )
        self.metadata_url = (
            f'https://{self.sf_instance}/services/Soap/m/{self.sf_version}/')
        self.tooling_url = f'{self.base_url}tooling/'
        self.oauth2_url = f'https://{self.sf_instance}/services/oauth2/'
        self.api_usage: MutableMapping[str, Union[Usage, PerAppUsage]] = {}
        self._parse_float = parse_float
        self._object_pairs_hook = object_pairs_hook  # type: ignore[assignment]
        self._mdapi: Optional[SfdcMetadataApi] = None

    @property
    def mdapi(self) -> SfdcMetadataApi:
        """Utility to interact with metadata api functionality"""
        if not self._mdapi:
            self._mdapi = SfdcMetadataApi(session=self.session,
                                          session_id=self.session_id,
                                          instance=self.sf_instance,
                                          metadata_url=self.metadata_url,
                                          api_version=self.sf_version,
                                          headers=self.headers
                                          )
        return self._mdapi

    def _generate_headers(self) -> None:
        """Utility to generate headers when refreshing the session"""
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
            }

    def _refresh_session(self) -> None:
        """Utility to refresh the session when expired"""
        if self._salesforce_login_partial is None:
            raise RuntimeError(
                'The simple_salesforce session can not refreshed if a '
                'session id has been provided.'
                )
        self.session_id, self.sf_instance = self._salesforce_login_partial()
        self._generate_headers()

    def describe(self,
                 **kwargs: Any
                 ) -> Optional[Any]:
        """Describes all available objects
        Arguments:
        * keyword arguments supported by requests.request (e.g. json, timeout)
        """
        url = self.base_url + "sobjects"
        result = self._call_salesforce('GET',
                                       url,
                                       name='describe',
                                       **kwargs
                                       )

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    def is_sandbox(self) -> Optional[bool]:
        """After connection returns is the organization in a sandbox"""
        is_sandbox = None
        if self.session_id:
            is_sandbox = self.query_all("SELECT IsSandbox "
                                        "FROM Organization LIMIT 1"
                                        ).get(
                'records',
                [{
                    'IsSandbox': None
                    }]
                )[0].get('IsSandbox')
        return is_sandbox

    # SObject Handler
    def __getattr__(
            self,
            name: str
            ) -> Union[SFBulkHandler, SFBulk2Handler, "SFType"]:
        """Returns an `SFType` instance for the given Salesforce object type
        (given in `name`).
        The magic part of the SalesforceAPI, this function translates
        calls such as `salesforce_api_instance.Lead.metadata()` into fully
        constituted `SFType` instances to make a nice Python API wrapper
        for the REST API.
        Arguments:
        * name -- the name of a Salesforce object type, e.g. Lead or Contact
        """

        # fix to enable serialization
        # (https://github.com/heroku/simple-salesforce/issues/60)
        if name.startswith('__'):
            return super().__getattr__(name)  # type: ignore[misc,no-any-return]

        if name == 'bulk':
            # Deal with bulk API functions
            return SFBulkHandler(self.session_id,
                                 self.bulk_url,
                                 self.proxies,
                                 self.session
                                 )
        if name == 'bulk2':
            return SFBulk2Handler(self.session_id,
                                  self.bulk2_url,
                                  self.proxies,
                                  self.session
                                  )

        return SFType(
            name,
            self.session_id,
            self.sf_instance,
            sf_version=self.sf_version,
            proxies=self.proxies,
            session=self.session,
            salesforce=self,
            object_pairs_hook=self._object_pairs_hook
            )

    # User utility methods
    def set_password(self,
                     user: str,
                     password: str
                     ) -> Optional[Any]:
        """Sets the password of a user
        salesforce dev documentation link:
        https://www.salesforce.com/us/developer/docs/api_rest/Content
        /dome_sobject_user_password.htm
        Arguments:
        * user: the userID of the user to set
        * password: the new password
        """

        url = f'{self.base_url}sobjects/User/{user}/password'
        params = {
            'NewPassword': password
            }

        result = self._call_salesforce('POST',
                                       url,
                                       data=json.dumps(params)
                                       )

        if result.status_code == 204:
            return None

        # salesforce return 204 No Content when the request is successful
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         result.status_code,
                                         'User',
                                         result.content
                                         )
        return self.parse_result_to_json(result)

    # Generic Rest Function
    def restful(
            self,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            method: str = 'GET',
            **kwargs: Any
            ) -> Optional[Any]:
        """Allows you to make a direct REST call if you know the path

        Arguments:
        * path: The path of the request
            Example: sobjects/User/ABC123/password'
        * params: dict of parameters to pass to the path
        * method: HTTP request method, default GET
        * other arguments supported by requests.request (e.g. json, timeout)
        """

        url = self.base_url + path
        result = self._call_salesforce(method,
                                       url,
                                       name=path,
                                       params=params,
                                       **kwargs
                                       )
        # Some restful calls return 204 No Content, which is not JSON
        if result.status_code == 204:
            return None

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    # OAuth Endpoints Function
    def oauth2(
            self,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            method: str = 'GET'
            ) -> Optional[Any]:
        """Allows you to make a request to OAuth endpoints if you know the path

        Arguments:

        * path: The path of the request
            Example: /services/oauth2/token'
        * params: dict of parameters to pass to the path
        * method: HTTP request method, default GET
        * other arguments supported by requests.request (e.g. json, timeout)
        """
        url = self.oauth2_url + path
        result = self._call_salesforce(method,
                                       url,
                                       name=path,
                                       params=params
                                       )

        content_type = result.headers.get('Content-Type')
        json_result = self.parse_result_to_json(result) \
            if content_type is not None \
               and 'json' in content_type else None

        return None if json_result and len(json_result) == 0 else json_result

    # Search Functions
    def search(self,
               search: str
               ) -> Any:
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.
        Arguments:
        * search -- the fully formatted SOSL search string, e.g.
                    `FIND {Waldo}`
        """
        url = self.base_url + 'search/'

        # `requests` will correctly encode the query string passed as `params`
        params = {
            'q': search
            }
        result = self._call_salesforce('GET',
                                       url,
                                       name='search',
                                       params=params
                                       )

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    def quick_search(self,
                     search: str
                     ) -> Any:
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.
        Arguments:
        * search -- the non-SOSL search string, e.g. `Waldo`. This search
                    string will be wrapped to read `FIND {Waldo}` before being
                    sent to Salesforce
        """
        search_string = f'FIND {{{search}}}'
        return self.search(search_string)

    def limits(self,
               **kwargs: Any
               ) -> Any:
        """Return the result of a Salesforce request to list Organization
        limits.
        """
        url = self.base_url + 'limits/'
        result = self._call_salesforce('GET',
                                       url,
                                       **kwargs
                                       )

        if result.status_code != 200:
            exception_handler(result)

        return self.parse_result_to_json(result)

    # Query Handler
    def query(
            self,
            query: str,
            include_deleted: bool = False,
            **kwargs: Any
            ) -> Any:
        """Return the result of a Salesforce SOQL query as a dict decoded from
        the Salesforce response JSON payload.
        Arguments:
        * query -- the SOQL query to send to Salesforce, e.g.
                   SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
        * include_deleted -- True if deleted records should be included
        """
        url = self.base_url + ('queryAll/' if include_deleted else 'query/')
        params = {
            'q': query
            }
        # `requests` will correctly encode the query string passed as `params`
        result = self._call_salesforce('GET',
                                       url,
                                       name='query',
                                       params=params,
                                       **kwargs
                                       )

        return self.parse_result_to_json(result)

    def query_more(
            self,
            next_records_identifier: str,
            identifier_is_url: bool = False,
            include_deleted: bool = False,
            **kwargs: Any
            ) -> Any:
        """Retrieves more results from a query that returned more results
        than the batch maximum. Returns a dict decoded from the Salesforce
        response JSON payload.
        Arguments:
        * next_records_identifier -- either the Id of the next Salesforce
                                     object in the result, or a URL to the
                                     next record in the result.
        * identifier_is_url -- True if `next_records_identifier` should be
                               treated as a URL, False if
                               `next_records_identifier` should be treated as
                               an Id.
        * include_deleted -- True if the `next_records_identifier` refers to a
                             query that includes deleted records. Only used if
                             `identifier_is_url` is False
        """
        if identifier_is_url:
            # Don't use `self.base_url` here because the full URI is provided
            url = f'https://{self.sf_instance}{next_records_identifier}'
        else:
            endpoint = 'queryAll' if include_deleted else 'query'
            url = f'{self.base_url}{endpoint}/{next_records_identifier}'
        result = self._call_salesforce('GET',
                                       url,
                                       name='query_more',
                                       **kwargs
                                       )

        return self.parse_result_to_json(result)

    def query_all_iter(
            self,
            query: str,
            include_deleted: bool = False,
            **kwargs: Any
            ) -> Iterator[Any]:
        """This is a lazy alternative to `query_all` - it does not construct
        the whole result set into one container, but returns objects from each
        page it retrieves from the API.
        Since `query_all` has always been eagerly executed, we reimplemented it
        using `query_all_iter`, only materializing the returned iterator to
        maintain backwards compatibility.
        The one big difference from `query_all` (apart from being lazy) is that
        we don't return a dictionary with `totalSize` and `done` here,
        we only return the records in an iterator.
        Arguments
        * query -- the SOQL query to send to Salesforce, e.g.
                   SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
        * include_deleted -- True if the query should include deleted records.
        """

        result = self.query(query,
                            include_deleted=include_deleted,
                            **kwargs
                            )
        while True:
            yield from result['records']
            # fetch next batch if we're not done else break out of loop
            if not result['done']:
                result = self.query_more(result['nextRecordsUrl'],
                                         identifier_is_url=True,
                                         **kwargs
                                         )
            else:
                return

    def query_all(
            self,
            query: str,
            include_deleted: bool = False,
            **kwargs: Any
            ) -> Dict[str, Any]:
        """Returns the full set of results for the `query`. This is a
        convenience
        wrapper around `query(...)` and `query_more(...)`.
        The returned dict is the decoded JSON payload from the final call to
        Salesforce, but with the `totalSize` field representing the full
        number of results retrieved and the `records` list representing the
        full list of records retrieved.
        Arguments
        * query -- the SOQL query to send to Salesforce, e.g.
                   SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
        * include_deleted -- True if the query should include deleted records.
        """

        records = self.query_all_iter(query,
                                      include_deleted=include_deleted,
                                      **kwargs
                                      )
        all_records = list(records)
        return {
            'records': all_records,
            'totalSize': len(all_records),
            'done': True,
            }

    def toolingexecute(
            self,
            action: str,
            method: str = 'GET',
            data: Optional[Dict[str, Any]] = None,
            **kwargs: Any
            ) -> Any:
        """Makes an HTTP request to an TOOLING REST endpoint
        Arguments:
        * action -- The REST endpoint for the request.
        * method -- HTTP method for the request (default GET)
        * data -- A dict of parameters to send in a POST / PUT request
        * kwargs -- Additional kwargs to pass to `requests.request`
        """
        # If data is None, we should send an empty body, not "null", which is
        # None in json.
        json_data = json.dumps(data) if data is not None else None
        result = self._call_salesforce(
            method,
            self.tooling_url + action,
            name="toolingexecute",
            data=json_data,
            **kwargs
            )
        try:
            response_content = result.json()
        # pylint: disable=broad-except
        except Exception:
            response_content = result.text

        return response_content

    def apexecute(
            self,
            action: str,
            method: str = 'GET',
            data: Optional[Dict[str, Any]] = None,
            **kwargs: Any
            ) -> Any:
        """Makes an HTTP request to an APEX REST endpoint
        Arguments:
        * action -- The REST endpoint for the request.
        * method -- HTTP method for the request (default GET)
        * data -- A dict of parameters to send in a POST / PUT request
        * kwargs -- Additional kwargs to pass to `requests.request`
        """
        # If data is None, we should send an empty body, not "null", which is
        # None in json.
        json_data = json.dumps(data) if data is not None else None
        result = self._call_salesforce(
            method,
            self.apex_url + action,
            name="apexecute",
            data=json_data,
            **kwargs
            )
        try:
            response_content = result.json()
        # pylint: disable=broad-except
        except Exception:
            response_content = result.text

        return response_content

    def _call_salesforce(
            self,
            method: str,
            url: str,
            name: str = "",
            retries: int = 0,
            max_retries: int = 3,
            **kwargs: Any
            ) -> requests.Response:
        """Utility method for performing HTTP call to Salesforce.
        Returns a `requests.result` object.
        """
        headers = self.headers.copy()
        additional_headers = kwargs.pop('headers',
                                        {}
                                        )
        headers.update(additional_headers)

        result = self.session.request(
            method,
            url,
            headers=headers,
            **kwargs
            )

        if self._salesforce_login_partial is not None \
                and result.status_code == 401:
            error_details = result.json()[0]
            if error_details['errorCode'] == 'INVALID_SESSION_ID':
                self._refresh_session()
                retries += 1
                if retries > max_retries:
                    exception_handler(result,
                                      name=name
                                      )
                return self._call_salesforce(
                    method,
                    url,
                    name,
                    retries=retries,
                    **kwargs
                    )

        if result.status_code >= 300:
            exception_handler(result,
                              name=name
                              )

        sforce_limit_info = result.headers.get('Sforce-Limit-Info')
        if sforce_limit_info:
            self.api_usage = self.parse_api_usage(sforce_limit_info)

        return result

    @staticmethod
    def parse_api_usage(
            sforce_limit_info: str
            ) -> MutableMapping[str, Union[Usage, PerAppUsage]]:
        """parse API usage and limits out of the Sforce-Limit-Info header
        Arguments:
        * sforce_limit_info: The value of response header 'Sforce-Limit-Info'
            Example 1: 'api-usage=18/5000'
            Example 2: 'api-usage=25/5000;
                per-app-api-usage=17/250(appName=sample-connected-app)'
        """
        result: MutableMapping[str, Union[Usage, PerAppUsage]] = {}

        api_usage = re.match(
            r'[^-]?api-usage=(?P<used>\d+)/(?P<tot>\d+)',
            sforce_limit_info
            )

        pau = r'.+per-app-api-usage=(?P<u>\d+)/(?P<t>\d+)\(appName=(?P<n>.+)\)'
        per_app_api_usage = re.match(pau,
                                     sforce_limit_info
                                     )

        if api_usage and api_usage.groups():
            groups = api_usage.groups()
            result['api-usage'] = Usage(used=int(groups[0]),
                                        total=int(groups[1])
                                        )
        if per_app_api_usage and per_app_api_usage.groups():
            groups = per_app_api_usage.groups()
            result['per-app-api-usage'] = PerAppUsage(used=int(groups[0]),
                                                      total=int(groups[1]),
                                                      name=groups[2]
                                                      )

        return result

    # file-based deployment function
    def deploy(
            self,
            zipfile: Union[str, IO[bytes]],
            sandbox: bool,
            **kwargs: Any
            ) -> Dict[str, Optional[str]]:
        """Deploy using the Salesforce Metadata API. Wrapper for
        SfdcMetaDataApi.deploy(...).
        Arguments:
        * zipfile: a .zip archive to deploy to an org, given as (
        "path/to/zipfile.zip")
        * options: salesforce DeployOptions in .json format.
            (https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta
            /api_meta/meta_deploy.htm)

        Returns a process id and state for this deployment.
        """
        asyncId, state = self.mdapi.deploy(zipfile,
                                           sandbox,
                                           **kwargs
                                           )
        result = {
            'asyncId': asyncId,
            'state': state
            }
        return result

    # check on a file-based deployment
    def checkDeployStatus(
            self,
            asyncId: str,
            **kwargs: Any
            ) -> Dict[str, Optional[Union[str, Mapping[str, str]]]]:
        """Check on the progress of a file-based deployment via Salesforce
        Metadata API.
        Wrapper for SfdcMetaDataApi.check_deploy_status(...).
        Arguments:
        * asyncId: deployment async process ID, returned by Salesforce.deploy()
        Returns status of the deployment the asyncId given.
        """
        state, state_detail, deployment_detail, unit_test_detail = \
            self.mdapi.check_deploy_status(asyncId,
                                           **kwargs
                                           )
        results = {
            'state': state,
            'state_detail': state_detail,
            'deployment_detail': deployment_detail,
            'unit_test_detail': unit_test_detail
            }
        return results

    def parse_result_to_json(self,
                             result: requests.Response
                             ) -> Any:
        """"Parse json from a Response object"""
        return result.json(object_pairs_hook=self._object_pairs_hook,
                           parse_float=self._parse_float
                           )


class SFType:
    """An interface to a specific type of SObject"""
    _parse_float = None
    _object_pairs_hook = OrderedDict

    # pylint: disable=too-many-arguments
    def __init__(
            self,
            object_name: str,
            session_id: str,
            sf_instance: str,
            sf_version: Optional[str] = DEFAULT_API_VERSION,
            proxies: Optional[Proxies] = None,
            session: Optional[requests.Session] = None,
            salesforce: Optional[Salesforce] = None,
            parse_float: Optional[Callable[[str], Any]] = None,
            object_pairs_hook: Callable[[List[Tuple[Any, Any]]], Any]
            = OrderedDict,
            ):
        """Initialize the instance with the given parameters.
        Arguments:
        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * session_id -- the session ID for authenticating to Salesforce
        * sf_instance -- the domain of the instance of Salesforce to use
        * sf_version -- the version of the Salesforce API to use
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        * parse_float -- Function to parse float values with. Is passed along to
                         https://docs.python.org/3/library/json.html#json.load
        * object_pairs_hook -- Function to parse ordered list of pairs in json.
                               To use python 'dict' change it to None or dict.
        """

        # Make this backwards compatible with any tests that
        # explicitly set the session_id and any other projects that
        # might be creating this object manually?

        if salesforce is None and session_id is None:
            raise RuntimeError(
                'The argument session_id or salesforce must be specified to '
                'instanciate SFType.'
                )

        self._session_id = session_id
        self.salesforce = salesforce
        self.name = object_name
        self.session = session or requests.Session()
        self._parse_float = parse_float
        self._object_pairs_hook = object_pairs_hook  # type: ignore[assignment]

        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies
        self.api_usage: MutableMapping[str, Union[Usage, PerAppUsage]] = {}

        self.base_url = (
            f'https://{sf_instance}/services/data/v{sf_version}/sobjects'
            f'/{object_name}/')

    @property
    def session_id(self) -> str:
        """Helper to return the session id"""
        if self.salesforce is not None:
            return self.salesforce.session_id
        return self._session_id

    def metadata(self,
                 headers: Optional[Headers] = None
                 ) -> Any:
        """Returns the result of a GET to `.../{object_name}/` as a dict
        decoded from the JSON payload returned by Salesforce.
        Arguments:
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce('GET',
                                       self.base_url,
                                       headers=headers
                                       )
        return self.parse_result_to_json(result)

    def describe(self,
                 headers: Optional[Headers] = None
                 ) -> Any:
        """Returns the result of a GET to `.../{object_name}/describe` as a
        dict decoded from the JSON payload returned by Salesforce.
        Arguments:
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='GET',
            url=urljoin(self.base_url,
                        'describe'
                        ),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def describe_layout(
            self,
            record_id: str,
            headers: Optional[Headers] = None
            ) -> Any:
        """Returns the layout of the object
        Returns the result of a GET to
        `.../{object_name}/describe/layouts/<recordid>` as a dict decoded from
        the JSON payload returned by Salesforce.
        Arguments:
        * record_id -- the Id of the SObject to get
        * headers -- a dict with additional request headers.
        """
        custom_url_part = f'describe/layouts/{record_id}'
        result = self._call_salesforce(
            method='GET',
            url=urljoin(self.base_url,
                        custom_url_part
                        ),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def get(
            self,
            record_id: str,
            headers: Optional[Headers] = None,
            **kwargs: Any
            ) -> Any:
        """Returns the result of a GET to `.../{object_name}/{record_id}` as a
        dict decoded from the JSON payload returned by Salesforce.
        Arguments:
        * record_id -- the Id of the SObject to get
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='GET',
            url=urljoin(self.base_url, record_id),
            headers=headers,
            **kwargs
            )
        return self.parse_result_to_json(result)

    def get_by_custom_id(
            self,
            custom_id_field: str,
            custom_id: str,
            headers: Optional[Headers] = None,
            **kwargs: Any
            ) -> Any:
        """Return an ``SFType`` by custom ID
        Returns the result of a GET to
        `.../{object_name}/{custom_id_field}/{custom_id}` as a dict decoded
        from the JSON payload returned by Salesforce.
        Arguments:
        * custom_id_field -- the API name of a custom field that was defined
                             as an External ID
        * custom_id - the External ID value of the SObject to get
        * headers -- a dict with additional request headers.
        """
        custom_url = urljoin(self.base_url,
                             f'{custom_id_field}/{quote_plus(custom_id)}'
                             )
        result = self._call_salesforce(
            method='GET',
            url=custom_url,
            headers=headers,
            **kwargs
            )
        return self.parse_result_to_json(result)

    def create(
            self,
            data: Dict[str, Any],
            headers: Optional[Headers] = None
            ) -> Any:
        """Creates a new SObject using a POST to `.../{object_name}/`.
        Returns a dict decoded from the JSON payload returned by Salesforce.
        Arguments:
        * data -- a dict of the data to create the SObject from. It will be
                  JSON-encoded before being transmitted.
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='POST',
            url=self.base_url,
            data=json.dumps(data),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def upsert(
            self,
            record_id: str,
            data: Dict[str, Any],
            raw_response: bool = False,
            headers: Optional[Headers] = None
            ) -> Any:
        """Creates or updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.
        If `raw_response` is false (the default), returns the status code
        returned by Salesforce. Otherwise, return the `requests.Response`
        object.
        Arguments:
        * record_id -- an identifier for the SObject as described in the
                       Salesforce documentation
        * data -- a dict of the data to create or update the SObject from. It
                  will be JSON-encoded before being transmitted.
        * raw_response -- a boolean indicating whether to return the response
                          directly, instead of the status code.
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='PATCH',
            url=urljoin(self.base_url,
                        record_id
                        ),
            data=json.dumps(data),
            headers=headers
            )
        return self._raw_response(result,
                                  raw_response
                                  )

    def update(
            self,
            record_id: str,
            data: Dict[str, Any],
            raw_response: bool = False,
            headers: Optional[Headers] = None
            ) -> Any:
        """Updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.
        If `raw_response` is false (the default), returns the status code
        returned by Salesforce. Otherwise, return the `requests.Response`
        object.
        Arguments:
        * record_id -- the Id of the SObject to update
        * data -- a dict of the data to update the SObject from. It will be
                  JSON-encoded before being transmitted.
        * raw_response -- a boolean indicating whether to return the response
                          directly, instead of the status code.
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='PATCH',
            url=urljoin(self.base_url,
                        record_id
                        ),
            data=json.dumps(data),
            headers=headers
            )
        return self._raw_response(result,
                                  raw_response
                                  )

    def delete(
            self,
            record_id: str,
            raw_response: bool = False,
            headers: Optional[Headers] = None
            ) -> Union[int, requests.Response]:
        """Deletes an SObject using a DELETE to
        `.../{object_name}/{record_id}`.
        If `raw_response` is false (the default), returns the status code
        returned by Salesforce. Otherwise, return the `requests.Response`
        object.
        Arguments:
        * record_id -- the Id of the SObject to delete
        * raw_response -- a boolean indicating whether to return the response
                          directly, instead of the status code.
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='DELETE',
            url=urljoin(self.base_url,
                        record_id
                        ),
            headers=headers
            )
        return self._raw_response(result,
                                  raw_response
                                  )

    def deleted(
            self,
            start: datetime,
            end: datetime,
            headers: Optional[Headers] = None
            ) -> Any:
        # pylint: disable=line-too-long
        """Gets a list of deleted records
        Use the SObject Get Deleted resource to get a list of deleted records
        for the specified object.
        .../deleted/?start=2013-05-05T00:00:00+00:00&end=2013-05-10T00:00:00
        +00:00
        * start -- start datetime object
        * end -- end datetime object
        * headers -- a dict with additional request headers.
        """
        url = urljoin(
            self.base_url,
            f'deleted/?start={date_to_iso8601(start)}&end='
            f'{date_to_iso8601(end)}'
            )
        result = self._call_salesforce(method='GET',
                                       url=url,
                                       headers=headers
                                       )
        return self.parse_result_to_json(result)

    def updated(
            self,
            start: datetime,
            end: datetime,
            headers: Optional[Headers] = None
            ) -> Any:
        # pylint: disable=line-too-long
        """Gets a list of updated records
        Use the SObject Get Updated resource to get a list of updated
        (modified or added) records for the specified object.
         .../updated/?start=2014-03-20T00:00:00+00:00&end=2014-03-22T00:00:00
         +00:00
        * start -- start datetime object
        * end -- end datetime object
        * headers -- a dict with additional request headers.
        """
        url = urljoin(
            self.base_url,
            f'updated/?start={date_to_iso8601(start)}&end='
            f'{date_to_iso8601(end)}'
            )
        result = self._call_salesforce(method='GET',
                                       url=url,
                                       headers=headers
                                       )
        return self.parse_result_to_json(result)

    def _call_salesforce(
            self,
            method: str,
            url: str,
            retries: int = 0,
            max_retries: int = 3,
            **kwargs: Any
            ) -> requests.Response:
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
            }
        additional_headers = kwargs.pop('headers',
                                        {}
                                        )
        headers.update(additional_headers or {})
        result = self.session.request(method,
                                      url,
                                      headers=headers,
                                      **kwargs
                                      )
        # pylint: disable=W0212
        if (self.salesforce
                and self.salesforce._salesforce_login_partial is not None
                and result.status_code == 401):
            error_details = result.json()[0]
            if error_details['errorCode'] == 'INVALID_SESSION_ID':
                self.salesforce._refresh_session()
                retries += 1
                if retries > max_retries:
                    exception_handler(result,
                                      name=self.name
                                      )

                return self._call_salesforce(method,
                                             url,
                                             **kwargs
                                             )

        if result.status_code >= 300:
            exception_handler(result,
                              self.name
                              )

        sforce_limit_info = result.headers.get('Sforce-Limit-Info')
        if sforce_limit_info:
            self.api_usage = Salesforce.parse_api_usage(sforce_limit_info)

        return result

    def _raw_response(
            self,
            response: requests.Response,
            body_flag: bool
            ) -> Union[int, requests.Response]:
        """Utility method for processing the response and returning either the
        status code or the response object.

        Returns either an `int` or a `requests.Response` object.
        """
        if not body_flag:
            return response.status_code

        return response

    def parse_result_to_json(self,
                             result: requests.Response
                             ) -> Any:
        """"Parse json from a Response object"""
        return result.json(object_pairs_hook=self._object_pairs_hook,
                           parse_float=self._parse_float
                           )

    def upload_base64(
            self,
            file_path: str,
            base64_field: str = 'Body',
            headers: Optional[Headers] = None,
            **kwargs: Any
            ) -> requests.Response:
        """Upload base64 encoded file to Salesforce"""
        data = {}
        body = base64.b64encode(Path(file_path).read_bytes()).decode()
        data[base64_field] = body
        result = self._call_salesforce(method='POST',
                                       url=self.base_url,
                                       headers=headers,
                                       json=data,
                                       **kwargs
                                       )

        return result

    def update_base64(
            self,
            record_id: str,
            file_path: str,
            base64_field: str = 'Body',
            headers: Optional[Headers] = None,
            raw_response: bool = False,
            **kwargs: Any
            ) -> Union[int, requests.Response]:
        """Updated base64 image from file to Salesforce"""
        data = {}
        body = base64.b64encode(Path(file_path).read_bytes()).decode()
        data[base64_field] = body
        result = self._call_salesforce(method='PATCH',
                                       url=urljoin(self.base_url,
                                                   record_id
                                                   ),
                                       json=data,
                                       headers=headers,
                                       **kwargs
                                       )

        return self._raw_response(result,
                                  raw_response
                                  )

    def get_base64(
            self,
            record_id: str,
            base64_field: str = 'Body',
            data: Optional[Any] = None,
            headers: Optional[Headers] = None,
            **kwargs: Any
            ) -> bytes:
        """Returns binary stream of base64 object at specific path.

        Arguments:

        * path: The path of the request
            Example: sobjects/Attachment/ABC123/Body
                     sobjects/ContentVersion/ABC123/VersionData
        """
        result = self._call_salesforce(method='GET',
                                       url=urljoin(
                                           self.base_url,
                                           f'{record_id}/{base64_field}'
                                           ),
                                       data=data,
                                       headers=headers,
                                       **kwargs
                                       )

        return result.content
