"""Utility functions for simple-salesforce"""

import xml.dom.minidom


# pylint: disable=invalid-name
def getUniqueElementValueFromXmlString(xmlString, elementName):
    """
    Extracts an element value from an XML string.

    For example, invoking
    getUniqueElementValueFromXmlString(
        '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    xmlStringAsDom = xml.dom.minidom.parseString(xmlString)
    elementsByName = xmlStringAsDom.getElementsByTagName(elementName)
    elementValue = None
    if len(elementsByName) > 0:
        elementValue = elementsByName[0].toxml().replace(
            '<' + elementName + '>', '').replace('</' + elementName + '>', '')
    return elementValue


def date_to_iso8601(date):
    """Returns an ISO8601 string from a date"""
    datetimestr = date.strftime('%Y-%m-%dT%H:%M:%S')
    timezone_sign = date.strftime('%z')[0:1]
    timezone_str = '%s:%s' % (
        date.strftime('%z')[1:3], date.strftime('%z')[3:5])
    return '{datetimestr}{tzsign}{timezone}'.format(
        datetimestr=datetimestr,
        tzsign=timezone_sign,
        timezone=timezone_str
        ).replace(':', '%3A').replace('+', '%2B')


class SalesforceError(Exception):
    """Base Salesforce API exception"""

    message = u'Unknown error occurred for {url}. Response content: {content}'

    def __init__(self, url, status, resource_name, content):
        # TODO exceptions don't seem to be using parent constructors at all.
        # this should be fixed.
        # pylint: disable=super-init-not-called
        self.url = url
        self.status = status
        self.resource_name = resource_name
        self.content = content

    def __str__(self):
        return self.message.format(url=self.url, content=self.content)

    def __unicode__(self):
        return self.__str__()
