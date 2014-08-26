"""Just-Salesforce Package"""

from just_salesforce.api import (
    Salesforce,
    SalesforceAPI,
    SFType,
    SalesforceMoreThanOneRecord,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError,
    SalesforceMalformedRequest
)

from just_salesforce.login import (
    SalesforceLogin, SalesforceAuthenticationFailed
)
