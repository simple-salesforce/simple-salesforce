"""Simple-Salesforce Package"""
# flake8: noqa

from simple_salesforce.api import (
    Salesforce,
    SalesforceAPI,
    SFType
)

from simple_salesforce.bulk import (
    SFBulkHandler
)

from simple_salesforce.login import (
    SalesforceLogin
)

from simple_salesforce.exceptions import (
    SalesforceError,
    SalesforceMoreThanOneRecord,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError,
    SalesforceMalformedRequest,
    SalesforceAuthenticationFailed
)
