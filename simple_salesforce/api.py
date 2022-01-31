"""Core classes and exceptions for Simple-Salesforce"""

# has to be defined prior to login import
DEFAULT_API_VERSION = '52.0'
import base64
import json
import logging
import re
from collections import OrderedDict, namedtuple
from urllib.parse import urljoin, urlparse

import requests

from .bulk import SFBulkHandler
from .exceptions import SalesforceGeneralError
from .login import SalesforceLogin
from .util import date_to_iso8601, exception_handler
from .metadata import SfdcMetadataApi

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

Usage = namedtuple('Usage', 'used total')
PerAppUsage = namedtuple('PerAppUsage', 'used total name')


# pylint: disable=too-many-instance-attributes
class Salesforce:
    """Salesforce Instance

    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    _parse_float = None

    # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
    def __init__(
            self,
            username=None,
            password=None,
            security_token=None,
            session_id=None,
            instance=None,
            instance_url=None,
            organizationId=None,
            version=DEFAULT_API_VERSION,
            proxies=None,
            session=None,
            client_id=None,
            domain=None,
            consumer_key=None,
            privatekey_file=None,
            privatekey=None,
            parse_float=None,
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
        """

        if domain is None:
            domain = 'login'

        # Determine if the user passed in the optional version and/or
        # domain kwargs
        self.sf_version = version
        self.domain = domain
        self.session = session or requests.Session()
        self.proxies = self.session.proxies
        # override custom session proxies dance
        if proxies is not None:
            if not session:
                self.session.proxies = self.proxies = proxies
            else:
                logger.warning(
                    'Proxies must be defined on custom session object, '
                    'ignoring proxies: %s', proxies
                    )

        # Determine if the user wants to use our username/password auth or pass
        # in their own information
        if all(arg is not None for arg in (
                username, password, security_token)):
            self.auth_type = "password"

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                session=self.session,
                username=username,
                password=password,
                security_token=security_token,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id,
                domain=self.domain)

        elif all(arg is not None for arg in (
                session_id, instance or instance_url)):
            self.auth_type = "direct"
            self.session_id = session_id

            # If the user provides the full url (as returned by the OAuth
            # interface for example) extract the hostname (which we rely on)
            if instance_url is not None:
                self.sf_instance = urlparse(instance_url).hostname
                port = urlparse(instance_url).port
                if port not in (None, 443):
                    self.sf_instance += ':' + str(port)
            else:
                self.sf_instance = instance

        elif all(arg is not None for arg in (
                username, password, organizationId)):
            self.auth_type = 'ipfilter'

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                session=self.session,
                username=username,
                password=password,
                organizationId=organizationId,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id,
                domain=self.domain)

        elif all(arg is not None for arg in (
                username, consumer_key, privatekey_file or privatekey)):
            self.auth_type = "jwt-bearer"

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                session=self.session,
                username=username,
                consumer_key=consumer_key,
                privatekey_file=privatekey_file,
                privatekey=privatekey,
                proxies=self.proxies,
                domain=self.domain)

        else:
            raise TypeError(
                'You must provide login information or an instance and token'
                )

        self.auth_site = ('https://{domain}.salesforce.com'
                          .format(domain=self.domain))

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
            }

        self.base_url = ('https://{instance}/services/data/v{version}/'
                         .format(instance=self.sf_instance,
                                 version=self.sf_version))
        self.apex_url = ('https://{instance}/services/apexrest/'
                         .format(instance=self.sf_instance))
        self.bulk_url = ('https://{instance}/services/async/{version}/'
                         .format(instance=self.sf_instance,
                                 version=self.sf_version))
        self.metadata_url = ('https://{instance}/services/Soap/m/{version}/'
                             .format(instance=self.sf_instance,
                                     version=self.sf_version))
        self.tooling_url = '{base_url}tooling/'.format(base_url=self.base_url)
        self.api_usage = {}
        self._parse_float = parse_float
        self._mdapi = None

    @property
    def mdapi(self):
        """Utility to interact with metadata api functionality"""
        if not self._mdapi:
            self._mdapi = SfdcMetadataApi(session=self.session,
                                          session_id=self.session_id,
                                          instance=self.sf_instance,
                                          metadata_url=self.metadata_url,
                                          api_version=self.sf_version,
                                          headers=self.headers)
        return self._mdapi

    def describe(self, **kwargs):
        """Describes all available objects

        Arguments:

        * keyword arguments supported by requests.request (e.g. json, timeout)
        """
        url = self.base_url + "sobjects"
        result = self._call_salesforce('GET', url, name='describe', **kwargs)

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    def is_sandbox(self):
        """After connection returns is the organization in a sandbox"""
        is_sandbox = None
        if self.session_id:
            is_sandbox = self.query_all("SELECT IsSandbox "
                                        "FROM Organization LIMIT 1")
            is_sandbox = is_sandbox.get('records', [{'IsSandbox': None}])[
                0].get(
                'IsSandbox')
        return is_sandbox

    # SObject Handler
    def __getattr__(self, name):
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
            return super().__getattr__(name)

        if name == 'bulk':
            # Deal with bulk API functions
            return SFBulkHandler(self.session_id, self.bulk_url, self.proxies,
                                 self.session)

        return SFType(
            name, self.session_id, self.sf_instance, sf_version=self.sf_version,
            proxies=self.proxies, session=self.session)

    # User utility methods
    def set_password(self, user, password):
        """Sets the password of a user

        salesforce dev documentation link:
        https://www.salesforce.com/us/developer/docs/api_rest/Content
        /dome_sobject_user_password.htm

        Arguments:

        * user: the userID of the user to set
        * password: the new password
        """

        url = self.base_url + 'sobjects/User/%s/password' % user
        params = {'NewPassword': password}

        result = self._call_salesforce('POST', url, data=json.dumps(params))

        if result.status_code == 204:
            return None

        # salesforce return 204 No Content when the request is successful
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         result.status_code,
                                         'User',
                                         result.content)
        return self.parse_result_to_json(result)

    # Generic Rest Function
    def restful(self, path, params=None, method='GET', **kwargs):
        """Allows you to make a direct REST call if you know the path

        Arguments:

        * path: The path of the request
            Example: sobjects/User/ABC123/password'
        * params: dict of parameters to pass to the path
        * method: HTTP request method, default GET
        * other arguments supported by requests.request (e.g. json, timeout)
        """

        url = self.base_url + path
        result = self._call_salesforce(method, url, name=path, params=params,
                                       **kwargs)

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    # Search Functions
    def search(self, search):
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * search -- the fully formatted SOSL search string, e.g.
                    `FIND {Waldo}`
        """
        url = self.base_url + 'search/'

        # `requests` will correctly encode the query string passed as `params`
        params = {'q': search}
        result = self._call_salesforce('GET', url, name='search', params=params)

        json_result = self.parse_result_to_json(result)
        if len(json_result) == 0:
            return None

        return json_result

    def quick_search(self, search):
        """Returns the result of a Salesforce search as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * search -- the non-SOSL search string, e.g. `Waldo`. This search
                    string will be wrapped to read `FIND {Waldo}` before being
                    sent to Salesforce
        """
        search_string = 'FIND {{{search_string}}}'.format(search_string=search)
        return self.search(search_string)

    def limits(self, **kwargs):
        """Return the result of a Salesforce request to list Organization
        limits.
        """
        url = self.base_url + 'limits/'
        result = self._call_salesforce('GET', url, **kwargs)

        if result.status_code != 200:
            exception_handler(result)

        return self.parse_result_to_json(result)

    # Query Handler
    def query(self, query, include_deleted=False, **kwargs):
        """Return the result of a Salesforce SOQL query as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * query -- the SOQL query to send to Salesforce, e.g.
                   SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"
        * include_deleted -- True if deleted records should be included
        """
        url = self.base_url + ('queryAll/' if include_deleted else 'query/')
        params = {'q': query}
        # `requests` will correctly encode the query string passed as `params`
        result = self._call_salesforce('GET', url, name='query',
                                       params=params, **kwargs)

        return self.parse_result_to_json(result)

    def query_more(
            self, next_records_identifier, identifier_is_url=False,
            include_deleted=False, **kwargs):
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
            url = ('https://{instance}{next_record_url}'
                   .format(instance=self.sf_instance,
                           next_record_url=next_records_identifier))
        else:
            endpoint = 'queryAll' if include_deleted else 'query'
            url = self.base_url + '{query_endpoint}/{next_record_id}'
            url = url.format(query_endpoint=endpoint,
                             next_record_id=next_records_identifier)
        result = self._call_salesforce('GET', url, name='query_more', **kwargs)

        return self.parse_result_to_json(result)

    def query_all_iter(self, query, include_deleted=False, **kwargs):
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

        result = self.query(query, include_deleted=include_deleted, **kwargs)
        while True:
            for record in result['records']:
                yield record
            # fetch next batch if we're not done else break out of loop
            if not result['done']:
                result = self.query_more(result['nextRecordsUrl'],
                                         identifier_is_url=True,
                                         **kwargs)
            else:
                return

    def query_all(self, query, include_deleted=False, **kwargs):
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

        records = self.query_all_iter(query, include_deleted=include_deleted,
                                      **kwargs)
        all_records = list(records)
        return {
            'records': all_records,
            'totalSize': len(all_records),
            'done': True,
            }

    def toolingexecute(self, action, method='GET', data=None, **kwargs):
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
            data=json_data, **kwargs
            )
        try:
            response_content = result.json()
        # pylint: disable=broad-except
        except Exception:
            response_content = result.text

        return response_content

    def apexecute(self, action, method='GET', data=None, **kwargs):
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
            data=json_data, **kwargs
            )
        try:
            response_content = result.json()
        # pylint: disable=broad-except
        except Exception:
            response_content = result.text

        return response_content

    def _call_salesforce(self, method, url, name="", **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = self.headers.copy()
        additional_headers = kwargs.pop('headers', {})
        headers.update(additional_headers)

        result = self.session.request(
            method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            exception_handler(result, name=name)

        sforce_limit_info = result.headers.get('Sforce-Limit-Info')
        if sforce_limit_info:
            self.api_usage = self.parse_api_usage(sforce_limit_info)

        return result

    @staticmethod
    def parse_api_usage(sforce_limit_info):
        """parse API usage and limits out of the Sforce-Limit-Info header

        Arguments:

        * sforce_limit_info: The value of response header 'Sforce-Limit-Info'
            Example 1: 'api-usage=18/5000'
            Example 2: 'api-usage=25/5000;
                per-app-api-usage=17/250(appName=sample-connected-app)'
        """
        result = {}

        api_usage = re.match(r'[^-]?api-usage=(?P<used>\d+)/(?P<tot>\d+)',
                             sforce_limit_info)
        pau = r'.+per-app-api-usage=(?P<u>\d+)/(?P<t>\d+)\(appName=(?P<n>.+)\)'
        per_app_api_usage = re.match(pau, sforce_limit_info)

        if api_usage and api_usage.groups():
            groups = api_usage.groups()
            result['api-usage'] = Usage(used=int(groups[0]),
                                        total=int(groups[1]))
        if per_app_api_usage and per_app_api_usage.groups():
            groups = per_app_api_usage.groups()
            result['per-app-api-usage'] = PerAppUsage(used=int(groups[0]),
                                                      total=int(groups[1]),
                                                      name=groups[2])

        return result

    # file-based deployment function
    def deploy(self, zipfile, sandbox, **kwargs):

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
        asyncId, state = self.mdapi.deploy(zipfile, sandbox, **kwargs)
        result = {'asyncId': asyncId, 'state': state}
        return result

    # check on a file-based deployment
    def checkDeployStatus(self, asyncId, **kwargs):
        """Check on the progress of a file-based deployment via Salesforce
        Metadata API.
        Wrapper for SfdcMetaDataApi.check_deploy_status(...).

        Arguments:

        * asyncId: deployment async process ID, returned by Salesforce.deploy()

        Returns status of the deployment the asyncId given.
        """
        state, state_detail, deployment_detail, unit_test_detail = \
            self.mdapi.check_deploy_status(asyncId, **kwargs)
        results = {
            'state': state,
            'state_detail': state_detail,
            'deployment_detail': deployment_detail,
            'unit_test_detail': unit_test_detail
            }
        return results

    def parse_result_to_json(self, result):
        """"Parse json from a Response object"""
        return result.json(object_pairs_hook=OrderedDict,
                           parse_float=self._parse_float)


class SFType:
    """An interface to a specific type of SObject"""
    _parse_float = None

    # pylint: disable=too-many-arguments
    def __init__(
            self,
            object_name,
            session_id,
            sf_instance,
            sf_version=DEFAULT_API_VERSION,
            proxies=None,
            session=None,
            parse_float=None,
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
        """
        self.session_id = session_id
        self.name = object_name
        self.session = session or requests.Session()
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies
        self.api_usage = {}

        self.base_url = (
            'https://{instance}/services/data/v{sf_version}/sobjects'
            '/{object_name}/'.format(instance=sf_instance,
                                     object_name=object_name,
                                     sf_version=sf_version))

        self._parse_float = parse_float

    def metadata(self, headers=None):
        """Returns the result of a GET to `.../{object_name}/` as a dict
        decoded from the JSON payload returned by Salesforce.

        Arguments:

        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce('GET', self.base_url, headers=headers)
        return self.parse_result_to_json(result)

    def describe(self, headers=None):
        """Returns the result of a GET to `.../{object_name}/describe` as a
        dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='GET', url=urljoin(self.base_url, 'describe'),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def describe_layout(self, record_id, headers=None):
        """Returns the layout of the object

        Returns the result of a GET to
        `.../{object_name}/describe/layouts/<recordid>` as a dict decoded from
        the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to get
        * headers -- a dict with additional request headers.
        """
        custom_url_part = 'describe/layouts/{record_id}'.format(
            record_id=record_id
            )
        result = self._call_salesforce(
            method='GET',
            url=urljoin(self.base_url, custom_url_part),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def get(self, record_id, headers=None):
        """Returns the result of a GET to `.../{object_name}/{record_id}` as a
        dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to get
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='GET', url=urljoin(self.base_url, record_id),
            headers=headers
            )
        return self.parse_result_to_json(result)

    def get_by_custom_id(self, custom_id_field, custom_id, headers=None):
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
        custom_url = urljoin(
            self.base_url, '{custom_id_field}/{custom_id}'.format(
                custom_id_field=custom_id_field, custom_id=custom_id
                )
            )
        result = self._call_salesforce(
            method='GET', url=custom_url, headers=headers
            )
        return self.parse_result_to_json(result)

    def create(self, data, headers=None):
        """Creates a new SObject using a POST to `.../{object_name}/`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * data -- a dict of the data to create the SObject from. It will be
                  JSON-encoded before being transmitted.
        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce(
            method='POST', url=self.base_url,
            data=json.dumps(data), headers=headers
            )
        return self.parse_result_to_json(result)

    def upsert(self, record_id, data, raw_response=False, headers=None):
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
            method='PATCH', url=urljoin(self.base_url, record_id),
            data=json.dumps(data), headers=headers
            )
        return self._raw_response(result, raw_response)

    def update(self, record_id, data, raw_response=False, headers=None):
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
            method='PATCH', url=urljoin(self.base_url, record_id),
            data=json.dumps(data), headers=headers
            )
        return self._raw_response(result, raw_response)

    def delete(self, record_id, raw_response=False, headers=None):
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
            method='DELETE', url=urljoin(self.base_url, record_id),
            headers=headers
            )
        return self._raw_response(result, raw_response)

    def deleted(self, start, end, headers=None):
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
            self.base_url, 'deleted/?start={start}&end={end}'.format(
                start=date_to_iso8601(start), end=date_to_iso8601(end)
                )
            )
        result = self._call_salesforce(method='GET', url=url, headers=headers)
        return self.parse_result_to_json(result)

    def updated(self, start, end, headers=None):
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
            self.base_url, 'updated/?start={start}&end={end}'.format(
                start=date_to_iso8601(start), end=date_to_iso8601(end)
                )
            )
        result = self._call_salesforce(method='GET', url=url, headers=headers)
        return self.parse_result_to_json(result)

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
            }
        additional_headers = kwargs.pop('headers', {})
        headers.update(additional_headers or {})
        result = self.session.request(method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            exception_handler(result, self.name)

        sforce_limit_info = result.headers.get('Sforce-Limit-Info')
        if sforce_limit_info:
            self.api_usage = Salesforce.parse_api_usage(sforce_limit_info)

        return result

    # pylint: disable=no-self-use
    def _raw_response(self, response, body_flag):
        """Utility method for processing the response and returning either the
        status code or the response object.

        Returns either an `int` or a `requests.Response` object.
        """
        if not body_flag:
            return response.status_code

        return response

    def parse_result_to_json(self, result):
        """"Parse json from a Response object"""
        return result.json(object_pairs_hook=OrderedDict,
                           parse_float=self._parse_float)

    def upload_base64(self, file_path, base64_field='Body', headers=None,
                      **kwargs):
        """Upload base64 encoded file to Salesforce"""
        data = {}
        with open(file_path, "rb") as f:
            body = base64.b64encode(f.read()).decode('utf-8')
        data[base64_field] = body
        result = self._call_salesforce(method='POST', url=self.base_url,
                                       headers=headers, json=data, **kwargs)

        return result

    def update_base64(self, record_id, file_path, base64_field='Body',
                      headers=None, raw_response=False,
                      **kwargs):
        """Updated base64 image from file to Salesforce"""
        data = {}
        with open(file_path, "rb") as f:
            body = base64.b64encode(f.read()).decode('utf-8')
        data[base64_field] = body
        result = self._call_salesforce(method='PATCH',
                                       url=urljoin(self.base_url, record_id),
                                       json=data,
                                       headers=headers, **kwargs)

        return self._raw_response(result, raw_response)

    def get_base64(self, record_id, base64_field='Body', data=None,
                   headers=None, **kwargs):
        """Returns binary stream of base64 object at specific path.

        Arguments:

        * path: The path of the request
            Example: sobjects/Attachment/ABC123/Body
                     sobjects/ContentVersion/ABC123/VersionData
        """
        result = self._call_salesforce(method='GET', url=urljoin(
            self.base_url, '{record_id}/{base64_field}'.format(
                record_id=record_id, base64_field=base64_field)),
                                       data=data,
                                       headers=headers, **kwargs)

        return result.content
