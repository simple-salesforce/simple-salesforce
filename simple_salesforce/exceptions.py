"""All exceptions for Simple Salesforce"""


class SalesforceError(Exception):
    """Base Salesforce API exception"""

    message = 'Unknown error occurred for {url}. Response content: {content}'

    def __init__(self, url, status, resource_name, content):
        """Initialize the SalesforceError exception

        SalesforceError is the base class of exceptions in simple-salesforce

        Args:
            url: Salesforce URL that was called
            status: Status code of the error response
            resource_name: Name of the Salesforce resource being queried
            content: content of the response
        """
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


class SalesforceMoreThanOneRecord(SalesforceError):
    """
    Error Code: 300
    The value returned when an external ID exists in more than one record. The
    response body contains the list of matching records.
    """

    message = 'More than one record for {url}. Response content: {content}'


class SalesforceMalformedRequest(SalesforceError):
    """
    Error Code: 400
    The request couldn't be understood, usually because the JSON or XML body
    contains an error.
    """

    message = 'Malformed request {url}. Response content: {content}'


class SalesforceExpiredSession(SalesforceError):
    """
    Error Code: 401
    The session ID or OAuth token used has expired or is invalid. The response
    body contains the message and errorCode.
    """

    message = 'Expired session for {url}. Response content: {content}'


class SalesforceRefusedRequest(SalesforceError):
    """
    Error Code: 403
    The request has been refused. Verify that the logged-in user has
    appropriate permissions.
    """

    message = 'Request refused for {url}. Response content: {content}'


class SalesforceResourceNotFound(SalesforceError):
    """
    Error Code: 404
    The requested resource couldn't be found. Check the URI for errors, and
    verify that there are no sharing issues.
    """

    message = 'Resource {name} Not Found. Response content: {content}'

    def __str__(self):
        return self.message.format(name=self.resource_name,
                                   content=self.content)


class SalesforceAuthenticationFailed(SalesforceError):
    """
    Thrown to indicate that authentication with Salesforce failed.
    """

    def __init__(self, code, message):
        # TODO exceptions don't seem to be using parent constructors at all.
        # this should be fixed.
        # pylint: disable=super-init-not-called
        self.code = code
        self.message = message

    def __str__(self):
        return f'{self.code}: {self.message}'


class SalesforceGeneralError(SalesforceError):
    """
    A non-specific Salesforce error.
    """

    message = 'Error Code {status}. Response content: {content}'

    def __str__(self):
        return self.message.format(status=self.status, content=self.content)


class SalesforceOperationError(Exception):
    """Base error for Bulk API 2.0 operations"""


class SalesforceBulkV2LoadError(SalesforceOperationError):
    """
    Error occurred during bulk 2.0 load
    """


class SalesforceBulkV2ExtractError(SalesforceOperationError):
    """
    Error occurred during bulk 2.0 extract
    """
