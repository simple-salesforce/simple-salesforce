"""Core classes and exceptions for Simple-Salesforce"""


# has to be defined prior to login import
DEFAULT_API_VERSION = '38.0'


import logging
import warnings
import requests
import json
import re
from collections import namedtuple

try:
    from urlparse import urlparse, urljoin
except ImportError:
    # Python 3+
    from urllib.parse import urlparse, urljoin

from simple_salesforce.login import SalesforceLogin
from simple_salesforce.util import date_to_iso8601, exception_handler
from simple_salesforce.exceptions import (
    SalesforceGeneralError
)
from simple_salesforce.bulk import SFBulkHandler

try:
    from collections import OrderedDict
except ImportError:
    # Python < 2.7
    from ordereddict import OrderedDict

#pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def _warn_request_deprecation():
    """Deprecation for (Salesforce/SFType).request attribute"""
    warnings.warn(
        'The request attribute has been deprecated and will be removed in a '
        'future version. Please use Salesforce.session instead.',
        DeprecationWarning
    )


Usage = namedtuple('Usage', 'used total')
PerAppUsage = namedtuple('PerAppUsage', 'used total name')


# pylint: disable=too-many-instance-attributes
class Salesforce(object):
    """Salesforce Instance

    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
    def __init__(
            self, username=None, password=None, security_token=None,
            session_id=None, instance=None, instance_url=None,
            organizationId=None, sandbox=None, version=DEFAULT_API_VERSION,
            proxies=None, session=None, client_id=None, domain=None,
            consumer_key=None, privatekey_file=None):
        """Initialize the instance with the given parameters.

        Available kwargs

        Password Authentication:

        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * sandbox -- DEPRECATED: Use domain instead.
        * domain -- The domain to using for connecting to Salesforce. Use
                    common domains, such as 'login' or 'test', or
                    Salesforce My domain. If not used, will default to
                    'login'.

        OAuth 2.0 JWT Bearer Token Authentication:

        * consumer_key -- the consumer key generated for the user
        * privatekey_file -- the path to the private key file used
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
                username, consumer_key, privatekey_file)):
            self.auth_type = "jwt-bearer"

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                session=self.session,
                username=username,
                consumer_key=consumer_key,
                privatekey_file=privatekey_file,
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

        self.api_usage = {}

    def describe(self, **kwargs):
        """Describes all available objects

        Arguments:

        * keyword arguments supported by requests.request (e.g. json, timeout)
        """
        url = self.base_url + "sobjects"
        result = self._call_salesforce('GET', url, name='describe', **kwargs)

        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None

        return json_result

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
            return super(Salesforce, self).__getattr__(name)

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
        https://www.salesforce.com/us/developer/docs/api_rest/Content/dome_sobject_user_password.htm

        Arguments:

        * user: the userID of the user to set
        * password: the new password
        """

        url = self.base_url + 'sobjects/User/%s/password' % user
        params = {'NewPassword': password}

        result = self._call_salesforce('POST', url, data=json.dumps(params))

        # salesforce return 204 No Content when the request is successful
        if result.status_code != 200 and result.status_code != 204:
            raise SalesforceGeneralError(url,
                                         result.status_code,
                                         'User',
                                         result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None

        return json_result

    # pylint: disable=invalid-name
    def setPassword(self, user, password):
        # pylint: disable=line-too-long
        """Sets the password of a user

        salesforce dev documentation link:
        https://www.salesforce.com/us/developer/docs/api_rest/Content/dome_sobject_user_password.htm

        Arguments:

        * user: the userID of the user to set
        * password: the new password
        """
        warnings.warn(
            "This method has been deprecated."
            "Please use set_password instead.",
            DeprecationWarning)
        return self.set_password(user, password)

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

        json_result = result.json(object_pairs_hook=OrderedDict)
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

        json_result = result.json(object_pairs_hook=OrderedDict)
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
        search_string = u'FIND {{{search_string}}}'.format(search_string=search)
        return self.search(search_string)

    def limits(self, **kwargs):
        """Return the result of a Salesforce request to list Organization
        limits.
        """
        url = self.base_url + 'limits/'
        result = self._call_salesforce('GET', url, **kwargs)

        if result.status_code != 200:
            exception_handler(result)

        return result.json(object_pairs_hook=OrderedDict)

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

        return result.json(object_pairs_hook=OrderedDict)

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
            url = (u'https://{instance}{next_record_url}'
                   .format(instance=self.sf_instance,
                           next_record_url=next_records_identifier))
        else:
            endpoint = 'queryAll' if include_deleted else 'query'
            url = self.base_url + '{query_endpoint}/{next_record_id}'
            url = url.format(query_endpoint=endpoint,
                             next_record_id=next_records_identifier)
        result = self._call_salesforce('GET', url, name='query_more', **kwargs)

        return result.json(object_pairs_hook=OrderedDict)

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

        result = self.query(query, include_deleted=include_deleted, **kwargs)
        all_records = []

        while True:
            all_records.extend(result['records'])
            # fetch next batch if we're not done else break out of loop
            if not result['done']:
                result = self.query_more(result['nextRecordsUrl'],
                                         identifier_is_url=True)
            else:
                break

        result['records'] = all_records
        return result

    def apexecute(self, action, method='GET', data=None, **kwargs):
        """Makes an HTTP request to an APEX REST endpoint

        Arguments:

        * action -- The REST endpoint for the request.
        * method -- HTTP method for the request (default GET)
        * data -- A dict of parameters to send in a POST / PUT request
        * kwargs -- Additional kwargs to pass to `requests.request`
        """
        result = self._call_salesforce(
            method,
            self.apex_url + action,
            name="apexexcute",
            data=json.dumps(data), **kwargs
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
        additional_headers = kwargs.pop('headers', dict())
        headers.update(additional_headers)

        result = self.session.request(
            method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            exception_handler(result, name=name)

        sforce_limit_info = result.headers.get('Sforce-Limit-Info')
        if sforce_limit_info:
            self.api_usage = self.parse_api_usage(sforce_limit_info)

        return result

    @property
    def request(self):
        """Deprecated access to self.session for backwards compatibility"""
        _warn_request_deprecation()
        return self.session

    @request.setter
    def request(self, session):
        """Deprecated setter for self.session"""
        _warn_request_deprecation()
        self.session = session

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

class SFType(object):
    """An interface to a specific type of SObject"""

    # pylint: disable=too-many-arguments
    def __init__(
            self, object_name, session_id, sf_instance,
            sf_version=DEFAULT_API_VERSION, proxies=None, session=None):
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
        """
        self.session_id = session_id
        self.name = object_name
        self.session = session or requests.Session()
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies
        self.api_usage = {}

        self.base_url = (
            u'https://{instance}/services/data/v{sf_version}/sobjects'
            '/{object_name}/'.format(instance=sf_instance,
                                     object_name=object_name,
                                     sf_version=sf_version))

    def metadata(self, headers=None):
        """Returns the result of a GET to `.../{object_name}/` as a dict
        decoded from the JSON payload returned by Salesforce.

        Arguments:

        * headers -- a dict with additional request headers.
        """
        result = self._call_salesforce('GET', self.base_url, headers=headers)
        return result.json(object_pairs_hook=OrderedDict)

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
        return result.json(object_pairs_hook=OrderedDict)

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
        return result.json(object_pairs_hook=OrderedDict)

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
        return result.json(object_pairs_hook=OrderedDict)

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
        return result.json(object_pairs_hook=OrderedDict)

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
        return result.json(object_pairs_hook=OrderedDict)

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
        .../deleted/?start=2013-05-05T00:00:00+00:00&end=2013-05-10T00:00:00+00:00

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
        return result.json(object_pairs_hook=OrderedDict)

    def updated(self, start, end, headers=None):
        # pylint: disable=line-too-long
        """Gets a list of updated records

        Use the SObject Get Updated resource to get a list of updated
        (modified or added) records for the specified object.

         .../updated/?start=2014-03-20T00:00:00+00:00&end=2014-03-22T00:00:00+00:00

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
        return result.json(object_pairs_hook=OrderedDict)

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }
        additional_headers = kwargs.pop('headers', dict())
        headers.update(additional_headers or dict())
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

    @property
    def request(self):
        """Deprecated access to self.session for backwards compatibility"""
        _warn_request_deprecation()
        return self.session

    @request.setter
    def request(self, session):
        """Deprecated setter for self.session"""
        _warn_request_deprecation()
        self.session = session


class SalesforceAPI(Salesforce):
    """Deprecated SalesforceAPI Instance

    This class implements the Username/Password Authentication Mechanism using
    Arguments It has since been surpassed by the 'Salesforce' class, which
    relies on kwargs

    """
    # pylint: disable=too-many-arguments
    def __init__(self, username, password, security_token, sandbox=False,
                 sf_version='27.0'):
        """Initialize the instance with the given parameters.

        Arguments:

        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * sandbox -- True if you want to login to `test.salesforce.com`, False
                     if you want to login to `login.salesforce.com`.
        * sf_version -- the version of the Salesforce API to use, for example
                        "27.0"
        """
        warnings.warn(
            "Use of login arguments has been deprecated. Please use kwargs",
            DeprecationWarning
        )

        super(SalesforceAPI, self).__init__(username=username,
                                            password=password,
                                            security_token=security_token,
                                            sandbox=sandbox,
                                            version=sf_version)
