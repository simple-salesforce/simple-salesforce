"""Core classes and exceptions for Simple-Salesforce"""

import requests
import json

from urlparse import urlparse

from simple_salesforce.login import SalesforceLogin


class Salesforce(object):
    """Salesforce Instance

    An instance of Salesforce is a handy way to wrap a Salesforce session
    for easy use of the Salesforce REST API.
    """
    def __init__(self, **kwargs):
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
        * instance -- Domain of your Salesforce instance, i.e. `na1.salesforce.com`
        OR
        * instance_url -- Full URL of your instance i.e. `https://na1.salesforce.com


        Universal Kwargs:
        * version -- the version of the Salesforce API to use, for example `29.0`
        """

        # Determine if the user passed in the optional version and/or sandbox kwargs
        self.sf_version = kwargs.get('version', '29.0')
        self.sandbox = kwargs.get('sandbox', False)

        # Determine if the user wants to use our username/password auth or pass in their own information
        if ('username' in kwargs) and ('password' in kwargs) and ('security_token' in kwargs):
            self.auth_type = "password"
            username = kwargs['username']
            password = kwargs['password']
            security_token = kwargs['security_token']

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                        username = username,
                        password = password,
                        security_token = security_token,
                        sandbox = self.sandbox,
                        sf_version = self.sf_version)

        elif ('session_id' in kwargs) and (('instance' in kwargs) or ('instance_url' in kwargs)):
            self.auth_type = "direct"
            self.session_id = kwargs['session_id']

            # If the user provides the full url (as returned by the OAuth interface for
            # example) extract the hostname (which we rely on)
            if ('instance_url' in kwargs):
                self.sf_instance = urlparse(kwargs['instance_url']).hostname
            else:
                self.sf_instance = kwargs['instance']

        elif ('username' in kwargs) and ('password' in kwargs) and ('organizationId' in kwargs):
            self.auth_type = 'ipfilter'
            username = kwargs['username']
            password = kwargs['password']
            organizationId = kwargs['organizationId']

            # Pass along the username/password to our login helper
            self.session_id, self.sf_instance = SalesforceLogin(
                            username = username,
                            password = password,
                            organizationId = organizationId,
                            sandbox = self.sandbox,
                            sf_version = self.sf_version)

        else:
            raise SalesforceGeneralError(
                'You must provide login information or an instance and token')

        if self.sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'

        self.request = requests.Session()
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }
        self.base_url = ('https://{instance}/services/data/v{version}/'
                         .format(instance=self.sf_instance,
                                 version=self.sf_version))

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
        return SFType(name, self.session_id, self.sf_instance, self.sf_version)

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
        result = self.request.get(url, headers=self.headers, params=params)
        if result.status_code != 200:
            raise SalesforceGeneralError(result.content)
        json_result = result.json()
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
        search_string = 'FIND {{{search_string}}}'.format(search_string=search)
        return self.search(search_string)

    # Query Handler
    def query(self, query):
        """Return the result of a Salesforce SOQL query as a dict decoded from
        the Salesforce response JSON payload.

        Arguments:

        * query -- the SOQL query to send to Salesforce, e.g.
                   `SELECT Id FROM Lead WHERE Email = "waldo@somewhere.com"`
        """
        url = self.base_url + 'query/'
        params = {'q': query}
        # `requests` will correctly encode the query string passed as `params`
        result = self.request.get(url, headers=self.headers, params=params)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json()

    def query_more(self, next_records_identifier, identifier_is_url=False):
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
            url = ('https://{instance}{next_record_url}'
                   .format(instance=self.sf_instance,
                           next_record_url=next_records_identifier))
        else:
            url = self.base_url + 'query/{next_record_id}'
            url = url.format(next_record_id=next_records_identifier)
        result = self.request.get(url, headers=self.headers)

        if result.status_code != 200:
            _exception_handler(result)

        return result.json()

    def query_all(self, query):
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
        def get_all_results(previous_result):
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
                                         identifier_is_url=True)
                result['totalSize'] += previous_result['totalSize']
                # Include the new list of records with the previous list
                previous_result['records'].extend(result['records'])
                result['records'] = previous_result['records']
                # Continue the recursion
                return get_all_results(result)

        # Make the initial query to Salesforce
        result = self.query(query)
        # The number of results might have exceeded the Salesforce batch limit
        # so check whether there are more results and retrieve them if so.
        return get_all_results(result)


class SFType(object):
    """An interface to a specific type of SObject"""

    def __init__(self, object_name, session_id, sf_instance, sf_version='27.0'):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * session_id -- the session ID for authenticating to Salesforce
        * sf_instance -- the domain of the instance of Salesforce to use
        * sf_version -- the version of the Salesforce API to use
        """
        self.session_id = session_id
        self.name = object_name
        self.base_url = ('https://{instance}/services/data/v{sf_version}/sobjects/{object_name}/'
                         .format(instance=sf_instance,
                                 object_name=object_name,
                                 sf_version=sf_version))
        self.request = requests.Session()

    def metadata(self):
        """Returns the result of a GET to `.../{object_name}/` as a dict
        decoded from the JSON payload returned by Salesforce.
        """
        result = self._call_salesforce('GET', self.base_url)
        return result.json()

    def describe(self):
        """Returns the result of a GET to `.../{object_name}/describe` as a
        dict decoded from the JSON payload returned by Salesforce.
        """
        result = self._call_salesforce('GET', self.base_url + 'describe')
        return result.json()

    def get(self, record_id):
        """Returns the result of a GET to `.../{object_name}/{record_id}` as a
        dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to get
        """
        result = self._call_salesforce('GET', self.base_url + record_id)
        return result.json()

    def create(self, data):
        """Creates a new SObject using a POST to `.../{object_name}/`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * data -- a dict of the data to create the SObject from. It will be
                  JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('POST', self.base_url,
                                       data=json.dumps(data))
        return result.json()

    def upsert(self, record_id, data):
        """Creates or updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- an identifier for the SObject as described in the
                       Salesforce documentation
        * data -- a dict of the data to create or update the SObject from. It
                  will be JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('PATCH', self.base_url + record_id,
                                       data=json.dumps(data))
        return result.status_code

    def update(self, record_id, data):
        """Updates an SObject using a PATCH to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to update
        * data -- a dict of the data to update the SObject from. It will be
                  JSON-encoded before being transmitted.
        """
        result = self._call_salesforce('PATCH', self.base_url + record_id,
                                       data=json.dumps(data))
        return result.status_code

    def delete(self, record_id):
        """Deletess an SObject using a DELETE to
        `.../{object_name}/{record_id}`.

        Returns a dict decoded from the JSON payload returned by Salesforce.

        Arguments:

        * record_id -- the Id of the SObject to delete
        """
        result = self._call_salesforce('DELETE', self.base_url + record_id)
        return result.status_code

    def deleted(self, start, end):
        """Use the SObject Get Deleted resource to get a list of deleted records for the specified object.
         .../deleted/?start=2013-05-05T00:00:00+00:00&end=2013-05-10T00:00:00+00:00

        * start -- start datetime string with format, ex: urllib.quote('2013-10-20T00:00:00+00:00')
        * end -- end dattime string with format ex: urllib.quote('2013-10-20T00:00:00+00:00')
        """
        url = self.base_url + 'deleted/?start=%s&end=%s' % (start, end)
        result = self._call_salesforce('GET', url)
        return result.json()

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }
        result = self.request.request(method, url, headers=headers, **kwargs)

        if result.status_code >= 300:
            _exception_handler(result, self.name)

        return result


class SalesforceAPI(Salesforce):
    """Depreciated SalesforceAPI Instance

    This class implements the Username/Password Authentication Mechanism using Arguments
    It has since been surpassed by the 'Salesforce' class, which relies on kwargs

    """
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
        import warnings
        warnings.warn(
            "Use of login arguments has been depreciated. Please use kwargs", DeprecationWarning)

        super(
            SalesforceAPI, self).__init__(username=username, password=password,
                                          security_token=security_token, sandbox=sandbox, version=sf_version)


def _exception_handler(result, name=""):
    """Exception router. Determines which error to raise for bad results"""
    url = result.url
    try:
        response_content = result.json()
    except Exception:
        response_content = result.text

    if result.status_code == 300:
        message = "More than one record for {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceMoreThanOneRecord(message)
    elif result.status_code == 400:
        message = "Malformed request {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceMalformedRequest(message)
    elif result.status_code == 401:
        message = "Expired session for {url}. Response content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceExpiredSession(message)
    elif result.status_code == 403:
        message = "Request refused for {url}. Resonse content: {content}"
        message = message.format(url=url, content=response_content)
        raise SalesforceRefusedRequest(message)
    elif result.status_code == 404:
        message = 'Resource {name} Not Found. Response content: {content}'
        message = message.format(name=name, content=response_content)
        raise SalesforceResourceNotFound(message)
    else:
        message = 'Error Code {status}. Response content: {content}'
        message = message.format(status=result.status_code, content=response_content)
        raise SalesforceGeneralError(message)


class SalesforceMoreThanOneRecord(Exception):
    """
    Error Code: 300
    The value returned when an external ID exists in more than one record. The
    response body contains the list of matching records.
    """
    pass


class SalesforceMalformedRequest(Exception):
    """
    Error Code: 400
    The request couldn't be understood, usually becaue the JSON or XML body contains an error.
    """
    pass


class SalesforceExpiredSession(Exception):
    """
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response
    body contains the message and errorCode.
    """
    pass


class SalesforceRefusedRequest(Exception):
    """
    Error Code: 403
    The request has been refused. Verify that the logged-in user has
    appropriate permissions.
    """
    pass


class SalesforceResourceNotFound(Exception):
    """
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and
    verify that there are no sharing issues.
    """
    pass


class SalesforceGeneralError(Exception):
    """
    A non-specific Salesforce error.
    """
    pass
