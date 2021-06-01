"""Simple-Salesforce Package"""
# flake8: noqa

from .api import Salesforce, SFType
from .bulk import SFBulkHandler
from .exceptions import (
    SalesforceAuthenticationFailed,
    SalesforceError,
    SalesforceExpiredSession,
    SalesforceGeneralError,
    SalesforceMalformedRequest,
    SalesforceMoreThanOneRecord,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
)
from .format import format_soql, format_external_id
from .login import SalesforceLogin
from .metadata import SfdcMetadataApi
from .sfdc_session import SfdcSession
