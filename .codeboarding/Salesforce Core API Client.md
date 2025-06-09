```mermaid
graph LR
    SalesforceClient["SalesforceClient"]
    SalesforceObjectHandler["SalesforceObjectHandler"]
    MetadataAPIHandler["MetadataAPIHandler"]
    BulkAPIHandler["BulkAPIHandler"]
    UtilityFunctions["UtilityFunctions"]
    SalesforceExceptions["SalesforceExceptions"]
    SalesforceClient -- "provides access to" --> SalesforceObjectHandler
    SalesforceClient -- "delegates to" --> MetadataAPIHandler
    SalesforceClient -- "delegates to" --> BulkAPIHandler
    SalesforceClient -- "uses" --> UtilityFunctions
    SalesforceObjectHandler -- "uses" --> UtilityFunctions
    BulkAPIHandler -- "uses" --> UtilityFunctions
    BulkAPIHandler -- "uses" --> SalesforceExceptions
    MetadataAPIHandler -- "uses" --> UtilityFunctions
    UtilityFunctions -- "handles" --> SalesforceExceptions
```
[![CodeBoarding](https://img.shields.io/badge/Generated%20by-CodeBoarding-9cf?style=flat-square)](https://github.com/CodeBoarding/GeneratedOnBoardings)[![Demo](https://img.shields.io/badge/Try%20our-Demo-blue?style=flat-square)](https://www.codeboarding.org/demo)[![Contact](https://img.shields.io/badge/Contact%20us%20-%20contact@codeboarding.org-lightgrey?style=flat-square)](mailto:contact@codeboarding.org)

## Component Details

This component provides the primary interface for interacting with the Salesforce REST API. It handles session management, general queries (SOQL), searches (SOSL), direct REST calls, and acts as a gateway to specific SObject types (via SFType), Bulk API v1, Bulk API v2, and Metadata API.

### SalesforceClient
The primary interface for interacting with the Salesforce REST API, handling session management, authentication, and providing methods for general API operations.


**Related Classes/Methods**:

- <a href="https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/api.py#L39-L460" target="_blank" rel="noopener noreferrer">`simple_salesforce.api.Salesforce` (39:460)</a>


### SalesforceObjectHandler
Manages operations on specific Salesforce object types, facilitating standard CRUD operations and providing access to object-specific metadata.


**Related Classes/Methods**:

- <a href="https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/api.py#L463-L549" target="_blank" rel="noopener noreferrer">`simple_salesforce.api.SFType` (463:549)</a>


### MetadataAPIHandler
Manages interactions with the Salesforce Metadata API, enabling deployment of metadata components and checking deployment status.


**Related Classes/Methods**:

- <a href="https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/metadata.py#L196-L656" target="_blank" rel="noopener noreferrer">`simple_salesforce.metadata.SfdcMetadataApi` (196:656)</a>


### BulkAPIHandler
Provides functionality for executing bulk data operations against Salesforce, encompassing both Bulk API v1 and v2.


**Related Classes/Methods**:

- <a href="https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/bulk.py#L18-L66" target="_blank" rel="noopener noreferrer">`simple_salesforce.bulk.SFBulkHandler` (18:66)</a>
- `simple_salesforce.bulk2.SFBulk2Handler` (full file reference)


### UtilityFunctions
A collection of helper functions supporting various operations across the library, including error handling and data format conversions.


**Related Classes/Methods**:

- `simple_salesforce.util` (full file reference)


### SalesforceExceptions
Defines custom exception types used throughout the simple-salesforce library to provide specific error information for API interaction issues.


**Related Classes/Methods**:

- `simple_salesforce.exceptions` (full file reference)




### [FAQ](https://github.com/CodeBoarding/GeneratedOnBoardings/tree/main?tab=readme-ov-file#faq)