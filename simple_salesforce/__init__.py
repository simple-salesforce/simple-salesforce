"""Simple-Salesforce Package"""
# flake8: noqa

from simple_salesforce.api import (
    Salesforce,
    SalesforceAPI,
    SFType,
    SalesforceError,
    SalesforceMoreThanOneRecord,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError,
    SalesforceMalformedRequest
)

from simple_salesforce.login import (
    SalesforceLogin, SalesforceAuthenticationFailed
)
