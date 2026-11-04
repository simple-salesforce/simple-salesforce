"""Simple-Salesforce Package"""
# flake8: noqa

from .api import Salesforce, SFType
from .bulk import SFBulkHandler
from .exceptions import (SalesforceAuthenticationFailed, SalesforceError,
                         SalesforceExpiredSession, SalesforceGeneralError,
                         SalesforceMalformedRequest,
                         SalesforceMoreThanOneRecord, SalesforceRefusedRequest,
                         SalesforceResourceNotFound)
from .login import (SalesforceLogin, generate_pkce_pair,
                    get_authorization_url)
from .format import format_soql, format_external_id
