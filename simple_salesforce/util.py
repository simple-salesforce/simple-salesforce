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
