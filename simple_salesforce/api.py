"""Core classes and exceptions for Simple-Salesforce"""


# has to be defined prior to login import
DEFAULT_API_VERSION = '29.0'


import logging
import warnings
import requests
import json

try:
    from urlparse import urlparse, urljoin
except ImportError:
    # Python 3+
    from urllib.parse import urlparse, urljoin
from simple_salesforce.login import SalesforceLogin
from simple_salesforce.util import date_to_iso8601, SalesforceError

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


# pylint: disable=too-many-instance-attributes
class Salesforce(object):
    """Salesforce Instance

    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    # pylint: disable=too-many-arguments
    def __init__(
            self, username=None, password=None, security_token=None,
            session_id=None, instance=None, instance_url=None,
            organizationId=None, sandbox=False, version=DEFAULT_API_VERSION,
            proxies=None, session=None, client_id=None):
        """Initialize the instance with the given parameters.

        Available kwargs

        Password Authentication:

        * username -- the Salesforce username to use for authentication
        * password -- the password for the username
        * security_token -- the security token for the username
        * sandbox -- True if you want to login to `test.salesforce.com`, False
                     if you want to login to `login.salesforce.com`.

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

        # Determine if the user passed in the optional version and/or sandbox
        # kwargs
        self.sf_version = version
        self.sandbox = sandbox
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
                sandbox=self.sandbox,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id)

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
                sandbox=self.sandbox,
                sf_version=self.sf_version,
                proxies=self.proxies,
                client_id=client_id)

        else:
            raise TypeError(
                'You must provide login information or an instance and token'
            )

        if self.sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'

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

    def describe(self):
        """Describes all available objects
        """
        url = self.base_url + "sobjects"
        result = self._call_salesforce('GET', url)
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         'describe',
                                         result.status_code,
                                         result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
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

        return SFType(
            name, self.session_id, self.sf_instance, sf_version=self.sf_version,
            proxies=self.proxies, session=self.session)

    # User utlity methods
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
                                         'User',
                                         result.status_code,
                                         result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
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
            "Please use set_password instread.",
            DeprecationWarning)
        return self.set_password(user, password)

    # Generic Rest Function
    def restful(self, path, params, method='GET'):
        """Allows you to make a direct REST call if you know the path

        Arguments:

        * path: The path of the request
            Example: sobjects/User/ABC123/password'
        * params: dict of parameters to pass to the path
        * method: HTTP request method, default GET
        """

        url = self.base_url + path
        result = self._call_salesforce(method, url, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         path,
                                         result.status_code,
                                         result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
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
        result = self._call_salesforce('GET', url, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         'search',
                                         result.status_code,
                                         result.content)
        json_result = result.json(object_pairs_hook=OrderedDict)
        if len(json_result) == 0:
            return None
        else:
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

    # Query Handler
    def query(self, query, **kwargs):
        """Return the result of a Salesforce SOQL query as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * query -- the SOQL query to send to Salesforce, e.g.
                   `SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"`
        """
        url = self.base_url + 'query/'
        params = {'q': query}
        # `requests` will correctly encode the query string passed as `params`
        result = self._call_salesforce('GET', url, params=params, **kwargs)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json(object_pairs_hook=OrderedDict)

    def query_more(
            self, next_records_identifier, identifier_is_url=False, **kwargs):
        """Retrieves more results from a query that returned more results
        than the batch maximum. Returns a dict decoded from the Salesforce
        response JSON payload.

        Arguments:

        * next_records_identifier -- either the Id of the next Salesforce
                                     object in the result, or a URL to the
                                     next record in the result.
        * identifier_is_url -- True if `next_records_identifier` should be
                               treated as a URL, False if
                               `next_records_identifer` should be treated as
                               an Id.
        """
        if identifier_is_url:
            # Don't use `self.base_url` here because the full URI is provided
            url = (u'https://{instance}{next_record_url}'
                   .format(instance=self.sf_instance,
                           next_record_url=next_records_identifier))
        else:
            url = self.base_url + 'query/{next_record_id}'
            url = url.format(next_record_id=next_records_identifier)
        result = self._call_salesforce('GET', url, **kwargs)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json(object_pairs_hook=OrderedDict)

    def query_all(self, query, **kwargs):
        """Returns the full set of results for the `query`. This is a
        convenience wrapper around `query(...)` and `query_more(...)`.

        The returned dict is the decoded JSON payload from the final call to
        Salesforce, but with the `totalSize` field representing the full
        number of results retrieved and the `records` list representing the
        full list of records retrieved.

        Arguments

        * query -- the SOQL query to send to Salesforce, e.g.
                   `SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"`
        """
        def get_all_results(previous_result, **kwargs):
            """Inner function for recursing until there are no more results.

            Returns the full set of results that will be the return value for
            `query_all(...)`

            Arguments:

            * previous_result -- the modified result of previous calls to
                                 Salesforce for this query
            """
            if previous_result['done']:
                return previous_result
            else:
                result = self.query_more(previous_result['nextRecordsUrl'],
                                         identifier_is_url=True, **kwargs)
                result['totalSize'] += previous_result['totalSize']
                # Include the new list of records with the previous list
                previous_result['records'].extend(result['records'])
                result['records'] = previous_result['records']
                # Continue the recursion
                return get_all_results(result, **kwargs)

        # Make the initial query to Salesforce
        result = self.query(query, **kwargs)
        # The number of results might have exceeded the Salesforce batch limit
        # so check whether there are more results and retrieve them if so.
        return get_all_results(result, **kwargs)

    def apexecute(self, action, method='GET', data=None, **kwargs):
        """Makes an HTTP request to an APEX REST endpoint

        Arguments:

        * action -- The REST endpoint for the request.
        * method -- HTTP method for the request (default GET)
        * data -- A dict of parameters to send in a POST / PUT request
        * kwargs -- Additional kwargs to pass to `requests.request`
        """
        result = self._call_salesforce(method, self.apex_url + action,
                                       data=json.dumps(data), **kwargs)

        if result.status_code == 200:
            try:
                response_content = result.json()
            # pylint: disable=broad-except
            except Exception:
                response_content = result.text
            return response_content

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        result = self.session.request(
            method, url, headers=self.headers, **kwargs)

        if result.status_code >= 300:
            _exception_handler(result)

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


class SFType(object):
    """An interface to a specific type of SObject"""

    # pylint: disable=too-many-arguments
    def __init__(
            self, object_name, session_id, sf_instance, sf_version='27.0',
            proxies=None, session=None):
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
            _exception_handler(result, self.name)

        return result

    # pylint: disable=no-self-use
    def _raw_response(self, response, body_flag):
        """Utility method for processing the response and returning either the
        status code or the response object.

        Returns either an `int` or a `requests.Response` object.
        """
        if not body_flag:
            return response.status_code
        else:
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


def _exception_handler(result, name=""):
    """Exception router. Determines which error to raise for bad results"""
    try:
        response_content = result.json()
    # pylint: disable=broad-except
    except Exception:
        response_content = result.text

    exc_map = {
        300: SalesforceMoreThanOneRecord,
        400: SalesforceMalformedRequest,
        401: SalesforceExpiredSession,
        403: SalesforceRefusedRequest,
        404: SalesforceResourceNotFound,
    }
    exc_cls = exc_map.get(result.status_code, SalesforceGeneralError)

    raise exc_cls(result.url, result.status_code, name, response_content)


class SalesforceMoreThanOneRecord(SalesforceError):
    """
    Error Code: 300
    The value returned when an external ID exists in more than one record. The
    response body contains the list of matching records.
    """
    message = u"More than one record for {url}. Response content: {content}"


class SalesforceMalformedRequest(SalesforceError):
    """
    Error Code: 400
    The request couldn't be understood, usually becaue the JSON or XML body
    contains an error.
    """
    message = u"Malformed request {url}. Response content: {content}"


class SalesforceExpiredSession(SalesforceError):
    """
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response
    body contains the message and errorCode.
    """
    message = u"Expired session for {url}. Response content: {content}"


class SalesforceRefusedRequest(SalesforceError):
    """
    Error Code: 403
    The request has been refused. Verify that the logged-in user has
    appropriate permissions.
    """
    message = u"Request refused for {url}. Response content: {content}"


class SalesforceResourceNotFound(SalesforceError):
    """
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and
    verify that there are no sharing issues.
    """
    message = u'Resource {name} Not Found. Response content: {content}'

    def __str__(self):
        return self.message.format(name=self.resource_name,
                                   content=self.content)


class SalesforceGeneralError(SalesforceError):
    """
    A non-specific Salesforce error.
    """
    message = u'Error Code {status}. Response content: {content}'

    def __str__(self):
        return self.message.format(status=self.status, content=self.content)
