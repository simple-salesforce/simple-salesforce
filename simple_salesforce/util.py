"""Utility functions for simple-salesforce"""

try:
   from collections import Mapping, Sequence
except ImportError:
    # +Python3.4
    from collections.abc import Mapping, Sequence

import xml.dom.minidom
try:
    from urllib2 import build_opener, Request, ProxyHandler
except ImportError:
    # +Python 3
    from urllib.request import build_opener, Request, ProxyHandler

try:
    from  urllib import urlencode
except ImportError:
    # +Python 3
    from urllib.parse import urlencode

try:
    basestring
except NameError:
    # +Python 3
    basestring = str


def getUniqueElementValueFromXmlString(xmlString, elementName):
    """
    Extracts an element value from an XML string.

    For example, invoking
    getUniqueElementValueFromXmlString('<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
    elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
    elementValue = None
    if len(elementsByName) > 0:
        elementValue = elementsByName[0].toxml().replace('<' + elementName + '>','').replace('</' + elementName + '>','')
    return elementValue


class RequestSession(object):
    """
    Simple wrapper around urllib2/urllib.request.

    Essentially builds an OpenerDirector and uses it to fetch data.

    Attributes:
      director: an instance of urllib2.OpenerDirector (on python2.x)
                or urllib.request.OpenerDirector (on python3.x)
    """

    def __init__(self, proxies=None):
        self.director = build_opener()
        self.add_proxies(proxies)

    def add_proxies(self, proxies):
        """Add proxies to the director."""
        if proxies is not None:
            self.director.add_handler(ProxyHandler(proxies))

    def post(self, url, data, headers):
        """
        Issue an HTTP POST request.

        Returns a "filelike" object with 3 additional methods:
        * geturl() -> URL where data came from
        * getcode() -> HTTP status code
        * info() -> HTTP response header info
        """
        if (isinstance(data, (Mapping, Sequence)) and 
            not isinstance(data, basestring)):
            data = urlencode(data)
        request = Request(url, data, headers)
        print "HELLOOOOOOOOO", request
        return self.director.open(request)

    def get(self, url, headers=(), params=()):
        """
        Issue an HTTP GET request.

        Returns a "filelike" object with 3 additional methods:
        * geturl() -> URL where data came from
        * getcode() -> HTTP status code
        * info() -> HTTP response header info

        Arguments:

        * url -- base url to fetch
        * headers -- Any additional headers, can be a mapping or sequence of
                     2 item sequences.
        * params -- Parameters to be added to query string.  Accepts same data
                    structure as headers.
        """
        if params:
            url += '?' + urlencode(params)
        request = Request(url)
        for k, v in dict(headers).items():
            request.add_header(k, v)
        return self.director.open(request)

    def request(self, method, url, *args, **kwargs):
        """
        Make a request by delegating to either get or post.

        Arguments:
          Same as `get` or `post` except that the first argument
          (method) is prepended first.
        """
        return getattr(self, method.lower())(url, *args, **kwargs)
