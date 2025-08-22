"""All exceptions for Simple Salesforce"""
from typing import Union


class SalesforceError(Exception):
    """Base Salesforce API exception"""

    message: str = \
        'Unknown error occurred for {url}. Response content: {content}'

    def __init__(
            self,
            url: str,
            status: int,
            resource_name: str,
            content: bytes):
        """Initialize the SalesforceError exception

        SalesforceError is the base class of exceptions in simple-salesforce

        Args:
            url: Salesforce URL that was called
            status: Status code of the error response
            resource_name: Name of the Salesforce resource being queried
            content: content of the response
        """
        super().__init__(self.message)
        self.url = url
        self.status = status
        self.resource_name = resource_name
        self.content = content

    def __str__(self) -> str:
        return self.message.format(url=self.url, content=self.content)

    def __unicode__(self) -> str:
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

    def __str__(self) -> str:
        return self.message.format(name=self.resource_name,
                                   content=self.content)


class SalesforceAuthenticationFailed(SalesforceError):
    """
    Thrown to indicate that authentication with Salesforce failed.

    This exception is raised when authentication with Salesforce fails,
    typically during login or token validation. It maintains compatibility
    with the SalesforceError base class while providing a simplified
    constructor for authentication-specific error reporting.

    Args:
        code: Error code from Salesforce authentication response
        message: Descriptive error message from authentication failure
    """

    message = 'Authentication failed. Response content: {content}'

    def __init__(self, code: Union[str, int, None], auth_message: str) -> None:
        """Initialize SalesforceAuthenticationFailed exception.

        Args:
            code: Error code from Salesforce (can be string, int, or None)
            auth_message: Authentication failure message

        Raises:
            TypeError: If auth_message is not a string
        """
        if not isinstance(auth_message, str):
            raise TypeError("auth_message must be a string")

        # Provide minimal context expected by SalesforceError.__init__
        url = 'authentication_endpoint'
        status = 401
        resource_name = 'Authentication'
        content = auth_message.encode('utf-8')

        super().__init__(url, status, resource_name, content)
        self.code = code
        self.auth_message = auth_message

    def __str__(self) -> str:
        """Return string representation of the authentication error."""
        if self.code is not None:
            return f'Authentication failed (code: {self.code}): {self.auth_message}'
        return f'Authentication failed: {self.auth_message}'


class SalesforceGeneralError(SalesforceError):
    """
    A non-specific Salesforce error.
    """

    message = 'Error Code {status}. Response content: {content}'

    def __str__(self) -> str:
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
