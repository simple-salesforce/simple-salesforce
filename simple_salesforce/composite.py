""" Classes for interacting with Salesforce Composite collections API
Note that API version 42.0 or later is required
"""

try:
    from collections import OrderedDict
except ImportError:
    # Python < 2.7
    from ordereddict import OrderedDict

try:
    from urlparse import urljoin
except ImportError:
    # Python 3+
    from urllib.parse import urljoin

import json
import requests
from simple_salesforce.util import exception_handler


class SFCompositeHandler(object):
    """ Composite API request handler
    Intermediate class which allows us to use commands,
    such as 'sf.composite.Contacts.get(...)',
            'sf.composite.delete(...)'
    """

    def __init__(self, session_id, composite_url, proxies=None, session=None):
        """Initialize the instance with the given parameters.

        Arguments:

        * session_id -- the session ID for authenticating to Salesforce
        * composite_url -- API endpoint set in Salesforce instance
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.session_id = session_id
        self.session = session or requests.Session()
        self.composite_url = composite_url
        self.sobjects_url = urljoin(composite_url, 'sobjects')
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.session_id,
            'X-PrettyPrint': '1'
        }

    def create(self, records, all_or_none=False):
        """Create multiple objects (types may be mixed)"""
        params = OrderedDict([
            ('records', records),
            ('allOrNone', all_or_none),
        ])
        result = self._call_salesforce(
            method='POST', url=self.sobjects_url, name='create',
            data=json.dumps(params))
        return result.json(object_pairs_hook=OrderedDict)

    def update(self, records, all_or_none=False):
        """Update multiple objects (types may be mixed)"""
        params = OrderedDict([
            ('records', records),
            ('allOrNone', all_or_none),
        ])
        result = self._call_salesforce(
            method='PATCH', url=self.sobjects_url, name='update',
            data=json.dumps(params))
        return result.json(object_pairs_hook=OrderedDict)

    def delete(self, ids, all_or_none=False):
        """Delete multiple objects (types may be mixed)"""
        params = OrderedDict([
            ('ids', ','.join(ids)),
            ('allOrNone', all_or_none),
        ])
        result = self._call_salesforce(
            method='DELETE', url=self.sobjects_url, name='delete',
            params=params)
        return result.json(object_pairs_hook=OrderedDict)

    def __getattr__(self, name):
        return SFCompositeType(object_name=name,
                               composite_url=self.composite_url,
                               headers=self.headers, session=self.session)

    def _call_salesforce(self, method, url, name="", **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        result = self.session.request(
            method, url, headers=self.headers, **kwargs)

        if result.status_code >= 300:
            exception_handler(result, name=name)

        return result

class SFCompositeType(object):
    """Interface to Composite API functions which work on a
    single SObject type
    """
    def __init__(self, object_name, composite_url, headers, session):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * composite_url -- API endpoint set in Salesforce instance
        * headers -- composite API headers
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.name = object_name
        self.composite_url = composite_url
        self.session = session
        self.headers = headers

    def get(self, ids, fields):
        """ retrieve list of records, with selected fields """
        params = {'ids': ids, 'fields': fields}
        result = self._call_salesforce(
            method='POST',
            url=urljoin(self.composite_url, 'sobjects/' + self.name),
            data=json.dumps(params))
        return result.json(object_pairs_hook=OrderedDict)

    def tree_create(self, records):
        """create one or more trees of objects (allOrNone not available)"""
        params = {'records': records}
        result = self._call_salesforce(
            method='POST',
            url=urljoin(self.composite_url, 'tree/' + self.name),
            data=json.dumps(params))
        return result.json(object_pairs_hook=OrderedDict)

    def _call_salesforce(self, method, url, **kwargs):
        """Utility method for performing HTTP call to Salesforce.

        Returns a `requests.result` object.
        """
        result = self.session.request(
            method, url, headers=self.headers, **kwargs)

        if result.status_code >= 300:
            exception_handler(result, self.name)

        return result
