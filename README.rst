*****************
Simple Salesforce
*****************

.. image:: https://api.travis-ci.org/simple-salesforce/simple-salesforce.svg?branch=master
   :target: https://travis-ci.org/simple-salesforce/simple-salesforce

.. image:: https://readthedocs.org/projects/simple-salesforce/badge/?version=latest
   :target: http://simple-salesforce.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Simple Salesforce is a basic Salesforce.com REST API client built for Python 3.6, 3.7 3.8, 3.9, 3.10, and 3.11. The goal is to provide a very low-level interface to the REST Resource and APEX API, returning a dictionary of the API JSON response.

=============

You can find out more regarding the format of the results in the `Official Salesforce.com REST API Documentation`_

.. _Official Salesforce.com REST API Documentation: http://www.salesforce.com/us/developer/docs/api_rest/index.htm

Examples
--------------------------
There are two ways to gain access to Salesforce

The first is to simply pass the domain of your Salesforce instance and an access token straight to ``Salesforce()``

For example:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(instance='na1.salesforce.com', session_id='')

If you have the full URL of your instance (perhaps including the schema, as is included in the OAuth2 request process), you can pass that in instead using ``instance_url``:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(instance_url='https://na1.salesforce.com', session_id='')

There are also four means of authentication, one that uses username, password and security token; one that uses IP filtering, username, password  and organizationId, one that uses a private key to sign a JWT, and one for connected apps that uses username, password, consumer key, and consumer secret;

To login using the security token method, simply include the Salesforce method and pass in your Salesforce username, password and token (this is usually provided when you change your password):

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com', password='password', security_token='token')

To login using IP-whitelist Organization ID method, simply use your Salesforce username, password and organizationId:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(password='password', username='myemail@example.com', organizationId='OrgId')

To login using the JWT method, use your Salesforce username, consumer key from your app, and private key (`How To <https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_auth_jwt_flow.htm#sfdx_dev_auth_jwt_flow>`_):

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com', consumer_key='XYZ', privatekey_file='filename.key')
    
To login using a connected app, simply include the Salesforce method and pass in your Salesforce username, password, consumer_key and consumer_secret (the consumer key and consumer secret are provided when you setup your connected app):

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com', password='password', consumer_key='consumer_key', consumer_secret='consumer_secret')


If you'd like to enter a sandbox, simply add ``domain='test'`` to your ``Salesforce()`` call.

For example:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com.sandbox', password='password', security_token='token', domain='test')

Note that specifying if you want to use a domain is only necessary if you are using the built-in username/password/security token authentication and is used exclusively during the authentication step.

If you'd like to keep track where your API calls are coming from, simply add ``client_id='My App'`` to your ``Salesforce()`` call.

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com.sandbox', password='password', security_token='token', client_id='My App', domain='test')

If you view the API calls in your Salesforce instance by Client Id it will be prefixed with ``simple-salesforce/``, for example ``simple-salesforce/My App``.

When instantiating a `Salesforce` object, it's also possible to include an
instance of `requests.Session`. This is to allow for specialized
session handling not otherwise exposed by simple_salesforce.

For example:

.. code-block:: python

   from simple_salesforce import Salesforce
   import requests

   session = requests.Session()
   # manipulate the session instance (optional)
   sf = Salesforce(
      username='user@example.com', password='password', organizationId='OrgId',
      session=session)

Record Management
--------------------------

To create a new 'Contact' in Salesforce:

.. code-block:: python

    sf.Contact.create({'LastName':'Smith','Email':'example@example.com'})

This will return a dictionary such as ``{u'errors': [], u'id': u'003e0000003GuNXAA0', u'success': True}``

To get a dictionary with all the information regarding that record, use:

.. code-block:: python

    contact = sf.Contact.get('003e0000003GuNXAA0')

To get a dictionary with all the information regarding that record, using a **custom** field that was defined as External ID:

.. code-block:: python

    contact = sf.Contact.get_by_custom_id('My_Custom_ID__c', '22')

To change that contact's last name from 'Smith' to 'Jones' and add a first name of 'John' use:

.. code-block:: python

    sf.Contact.update('003e0000003GuNXAA0',{'LastName': 'Jones', 'FirstName': 'John'})

To delete the contact:

.. code-block:: python

    sf.Contact.delete('003e0000003GuNXAA0')

To retrieve a list of Contact records deleted over the past 10 days (datetimes are required to be in UTC):

.. code-block:: python

    import pytz
    import datetime
    end = datetime.datetime.now(pytz.UTC)  # we need to use UTC as salesforce API requires this!
    sf.Contact.deleted(end - datetime.timedelta(days=10), end)

To retrieve a list of Contact records updated over the past 10 days (datetimes are required to be in UTC):

.. code-block:: python

    import pytz
    import datetime
    end = datetime.datetime.now(pytz.UTC) # we need to use UTC as salesforce API requires this
    sf.Contact.updated(end - datetime.timedelta(days=10), end)

Note that Update, Delete and Upsert actions return the associated `Salesforce HTTP Status Code`_

Use the same format to create any record, including 'Account', 'Opportunity', and 'Lead'.
Make sure to have all the required fields for any entry. The `Salesforce API`_ has all objects found under 'Reference -> Standard Objects' and the required fields can be found there.

.. _Salesforce HTTP Status Code: http://www.salesforce.com/us/developer/docs/api_rest/Content/errorcodes.htm
.. _Salesforce API: https://www.salesforce.com/developer/docs/api/

Queries
--------------------------

It's also possible to write select queries in Salesforce Object Query Language (SOQL) and search queries in Salesforce Object Search Language (SOSL).

All SOQL queries are supported and parent/child relationships can be queried using the standard format (Parent__r.FieldName). SOQL queries are done via:

.. code-block:: python

    sf.query("SELECT Id, Email, ParentAccount.Name FROM Contact WHERE LastName = 'Jones'")

If, due to an especially large result, Salesforce adds a ``nextRecordsUrl`` to your query result, such as ``"nextRecordsUrl" : "/services/data/v26.0/query/01gD0000002HU6KIAW-2000"``, you can pull the additional results with either the ID or the full URL (if using the full URL, you must pass 'True' as your second argument)

.. code-block:: python

    sf.query_more("01gD0000002HU6KIAW-2000")
    sf.query_more("/services/data/v26.0/query/01gD0000002HU6KIAW-2000", True)

As a convenience, to retrieve all of the results in a single local method call use

.. code-block:: python

    sf.query_all("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

While ``query_all`` materializes the whole result into a Python list, ``query_all_iter`` returns an iterator, which allows you to lazily process each element separately

.. code-block:: python

    data = sf.query_all_iter("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")
    for row in data:
      process(row)

Values used in SOQL queries can be quoted and escaped using ``format_soql``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName = {}", "Jones"))
    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName = {last_name}", last_name="Jones"))
    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName IN {names}", names=["Smith", "Jones"]))

To skip quoting and escaping for one value while still using the format string, use ``:literal``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE Income > {:literal}", "USD100"))

To escape a substring used in a LIKE expression while being able to use % around it, use ``:like``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE Name LIKE '{:like}%'", "Jones"))

SOSL queries are done via:

.. code-block:: python

    sf.search("FIND {Jones}")

There is also 'Quick Search', which inserts your query inside the {} in the SOSL syntax. Be careful, there is no escaping!

.. code-block:: python

    sf.quick_search("Jones")

Search and Quick Search return ``None`` if there are no records, otherwise they return a dictionary of search results.

More details about syntax is available on the `Salesforce Query Language Documentation Developer Website`_

.. _Salesforce Query Language Documentation Developer Website: http://www.salesforce.com/us/developer/docs/soql_sosl/index.htm

CRUD Metadata API Calls
_______________________

You can use simple_salesforce to make CRUD (Create, Read, Update and Delete) API calls to the metadata API.

First, get the metadata API object:

.. code-block:: python

    mdapi = sf.mdapi

To create a new metadata component in Salesforce, define the metadata component using the metadata types reference
given in Salesforce's `metadata API documentation`_

.. _metadata API documentation: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_types_list.htm

.. code-block:: python

    custom_object = mdapi.CustomObject(
        fullName = "CustomObject__c",
        label = "Custom Object",
        pluralLabel = "Custom Objects",
        nameField = mdapi.CustomField(
            label = "Name",
            type = mdapi.FieldType("Text")
        ),
        deploymentStatus = mdapi.DeploymentStatus("Deployed"),
        sharingModel = mdapi.SharingModel("Read")
    )

This custom object metadata can then be created in Salesforce using the createMetadata API call:

.. code-block:: python

    mdapi.CustomObject.create(custom_object)

Similarly, any metadata type can be created in Salesforce using the syntax :code:`mdapi.MetadataType.create()`. It is
also possible to create more than one metadata component in Salesforce with a single createMetadata API call. This can
be done by passing a list of metadata definitions to :code:`mdapi.MetadataType.create()`. Up to 10 metadata components
of the same metadata type can be created in a single API call (This limit is 200 in the case of CustomMetadata and
CustomApplication).

readMetadata, updateMetadata, upsertMetadata, deleteMetadata, renameMetadata and describeValueType API calls can be
performed with similar syntax to createMetadata:

.. code-block:: python

    describe_response = mdapi.CustomObject.describe()
    custom_object = mdapi.CustomObject.read("CustomObject__c")
    custom_object.sharingModel = mdapi.SharingModel("ReadWrite")
    mdapi.CustomObject.update(custom_object)
    mdapi.CustomObject.rename("CustomObject__c", "CustomObject2__c")
    mdapi.CustomObject.delete("CustomObject2__c")

The describe method returns a `DescribeValueTypeResult`_ object.

.. _DescribeValueTypeResult: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_describeValueTypeResult.htm

Just like with the createMetadata API call, multiple metadata components can be dealt with in a single API call for all
CRUD operations by passing a list to their respective methods. In the case of readMetadata, if multiple components are
read in a single API call, a list will be returned.

simple_salesforce validates the response received from Salesforce. Create, update, upsert, delete and rename
methods return :code:`None`, but raise an Exception with error message (from Salesforce) if Salesforce does not return
success. So, error handling can be done by catching the python exception.

simple_salesforce also supports describeMetadata and listMetadata API calls as follows. describeMetadata uses the API
version set for the Salesforce object and will return a DescribeMetadataResult object.

.. code-block:: python

    mdapi.describe()
    query = mdapi.ListMetadataQuery(type='CustomObject')
    query_response = mdapi.list_metadata(query)

Up to 3 ListMetadataQuery objects can be submitted in one list_metadata API call by passing a list. The list_metadata
method returns a list of `FileProperties`_ objects.

.. _FileProperties: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_retrieveresult.htm#retrieveresult_fileproperties

File Based Metadata API Calls
-----------------------------

You can use simple_salesforce to make file-based calls to the Metadata API, to deploy a zip file to an org.

First, convert and zip the file with:

.. code-block::

   sfdx force:source:convert -r src/folder_name -d dx

Then navigate into the converted folder and zip it up:

.. code-block::

   zip -r -X package.zip *

Then you can use this to deploy that zipfile:

.. code-block:: python

   result = sf.deploy("path/to/zip", sandbox=False, **kwargs)
   asyncId = result.get('asyncId')
   state = result.get('state')

Both deploy and checkDeployStatus take keyword arguments. The single package argument is not currently available to be set for deployments. More details on the deploy options can be found at https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_deploy.htm

You can check on the progress of the deploy which returns a dictionary with status, state_detail, deployment_detail, unit_test_detail:

.. code-block:: python

   sf.checkDeployStatus(asyncId)

Example of a use-case:

.. code-block:: python

   from simple_salesforce import Salesforce

   deployment_finished = False
   successful = False

   sf = Salesforce(session_id="id", instance="instance")
   sf.deploy("path/to/zip", sandbox=False ,**kwargs)

   while not deployment_finished:
       result = sf.checkDeployStatus(asyncId)
       if result.get('status') in ["Succeeded", "Completed", "Error", "Failed", None]:
           deployment_finished = True
       if result.get('status') in ["Succeeded", "Completed"]:
           successful = True

   if successful:
       print("✅")
   else:
       print("🥔")

Other Options
--------------------------

To insert or update (upsert) a record using an external ID, use:

.. code-block:: python

    sf.Contact.upsert('customExtIdField__c/11999',{'LastName': 'Smith','Email': 'smith@example.com'})

To format an external ID that could contain non-URL-safe characters, use:

.. code-block:: python

    external_id = format_external_id('customExtIdField__c', 'this/that & the other')

To retrieve basic metadata use:

.. code-block:: python

    sf.Contact.metadata()

To retrieve a description of the object, use:

.. code-block:: python

    sf.Contact.describe()

To retrieve a description of the record layout of an object by its record layout unique id, use:

.. code-block:: python

    sf.Contact.describe_layout('39wmxcw9r23r492')

To retrieve a list of top level description of instance metadata, user:

.. code-block:: python

    sf.describe()

    for x in sf.describe()["sobjects"]:
      print x["label"]


Using Bulk
--------------------------

You can use this library to access Bulk API functions. The data element can be a list of records of any size and by default batch sizes are 10,000 records and run in parallel concurrency mode. To set the batch size for insert, upsert, delete, hard_delete, and update use the batch_size argument. To set the concurrency mode for the salesforce job the use_serial argument can be set to use_serial=True.

Create new records:

.. code-block:: python

    data = [
          {'LastName':'Smith','Email':'example@example.com'},
          {'LastName':'Jones','Email':'test@test.com'}
        ]

    sf.bulk.Contact.insert(data,batch_size=10000,use_serial=True)

Update existing records:

.. code-block:: python

    data = [
          {'Id': '0000000000AAAAA', 'Email': 'examplenew@example.com'},
          {'Id': '0000000000BBBBB', 'Email': 'testnew@test.com'}
        ]

    sf.bulk.Contact.update(data,batch_size=10000,use_serial=True)
    
Update existing records and update lookup fields from an external id field:

.. code-block:: python

    data = [
          {'Id': '0000000000AAAAA', 'Custom_Object__r': {'Email__c':'examplenew@example.com'}},
          {'Id': '0000000000BBBBB', 'Custom_Object__r': {'Email__c': 'testnew@test.com'}}
        ]

    sf.bulk.Contact.update(data,batch_size=10000,use_serial=True)

Upsert records:

.. code-block:: python

    data = [
          {'Id': '0000000000AAAAA', 'Email': 'examplenew2@example.com'},
          {'Email': 'foo@foo.com'}
        ]

    sf.bulk.Contact.upsert(data, 'Id', batch_size=10000, use_serial=True)


Query records:

.. code-block:: python

    query = 'SELECT Id, Name FROM Account LIMIT 10'

    sf.bulk.Account.query(query)

To retrieve large amounts of data, use 

.. code-block:: python

    query = 'SELECT Id, Name FROM Account'

    # generator on the results page
    fetch_results = sf.bulk.Account.query(query, lazy_operation=True)

    # the generator provides the list of results for every call to next()
    all_results = []
    for list_results in fetch_results:
      all_results.extend(list_results)

Query all records:

QueryAll will return records that have been deleted because of a merge or delete. QueryAll will also return information about archived Task and Event records.

.. code-block:: python

    query = 'SELECT Id, Name FROM Account LIMIT 10'

    sf.bulk.Account.query_all(query)

To retrieve large amounts of data, use 

.. code-block:: python

    query = 'SELECT Id, Name FROM Account'

    # generator on the results page
    fetch_results = sf.bulk.Account.query_all(query, lazy_operation=True)

    # the generator provides the list of results for every call to next()
    all_results = []
    for list_results in fetch_results:
      all_results.extend(list_results)

Delete records (soft deletion):

.. code-block:: python

    data = [{'Id': '0000000000AAAAA'}]

    sf.bulk.Contact.delete(data,batch_size=10000,use_serial=True)

Hard deletion:

.. code-block:: python

    data = [{'Id': '0000000000BBBBB'}]

    sf.bulk.Contact.hard_delete(data,batch_size=10000,use_serial=True)


Using Apex
--------------------------

You can also use this library to call custom Apex methods:

.. code-block:: python

    payload = {
      "activity": [
        {"user": "12345", "action": "update page", "time": "2014-04-21T13:00:15Z"}
      ]
    }
    result = sf.apexecute('User/Activity', method='POST', data=payload)

This would call the endpoint ``https://<instance>.salesforce.com/services/apexrest/User/Activity`` with ``data=`` as
the body content encoded with ``json.dumps``

You can read more about Apex on the `Force.com Apex Code Developer's Guide`_

.. _Force.com Apex Code Developer's Guide: https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_dev_guide.htm

Additional Features
--------------------------

There are a few helper classes that are used internally and available to you.

Included in them are ``SalesforceLogin``, which takes in a username, password, security token, optional version and optional domain and returns a tuple of ``(session_id, sf_instance)`` where `session_id` is the session ID to use for authentication to Salesforce and ``sf_instance`` is the domain of the instance of Salesforce to use for the session.

For example, to use SalesforceLogin for a sandbox account you'd use:

.. code-block:: python

    from simple_salesforce import SalesforceLogin
    session_id, instance = SalesforceLogin(
        username='myemail@example.com.sandbox',
        password='password',
        security_token='token',
        domain='test')

Simply leave off the final domain if you do not wish to use a sandbox.

Also exposed is the ``SFType`` class, which is used internally by the ``__getattr__()`` method in the ``Salesforce()`` class and represents a specific SObject type. ``SFType`` requires ``object_name`` (i.e. ``Contact``), ``session_id`` (an authentication ID), ``sf_instance`` (hostname of your Salesforce instance), and an optional ``sf_version``

To add a Contact using the default version of the API you'd use:

.. code-block:: python

    from simple_salesforce import SFType
    contact = SFType('Contact','sesssionid','na1.salesforce.com')
    contact.create({'LastName':'Smith','Email':'example@example.com'})

To use a proxy server between your client and the SalesForce endpoint, use the proxies argument when creating SalesForce object.
The proxy argument is the same as what requests uses, a map of scheme to proxy URL:

.. code-block:: python

    proxies = {
      "http": "http://10.10.1.10:3128",
      "https": "http://10.10.1.10:1080",
    }
    SalesForce(instance='na1.salesforce.com', session_id='', proxies=proxies)

All results are returned as JSON converted OrderedDict to preserve order of keys from REST responses.

Helpful Datetime Resources
--------------------------
A list of helpful resources when working with datetime/dates from Salesforce

Convert SFDC Datetime to Datetime or Date object
.. code-block:: python

    import datetime
    # Formatting to SFDC datetime
    formatted_datetime =  datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z")
    
    #Formatting to SFDC date
    formatted_date = datetime.strptime(x, "%Y-%m-%d")
    
Helpful Pandas Resources
--------------------------
A list of helpful resources when working with Pandas and simple-salesforce

Generate list for SFDC Query "IN" operations from a Pandas Dataframe

.. code-block:: python
 
 import pandas as pd
 
 df = pd.DataFrame([{'Id':1},{'Id':2},{'Id':3}])
    def dataframe_to_sfdc_list(df,column):
      df_list = df[column].unique()
      df_list = [str(x) for x in df_list]
      df_list = ','.join("'"+item+"'" for item in df_list)
      return df_list
      
   sf.query(format_soql("SELECT Id, Email FROM Contact WHERE Id IN ({})", dataframe_to_sfdc_list(df,column)))
   
Generate Pandas Dataframe from SFDC API Query (ex.query,query_all)

.. code-block:: python
   
   import pandas as pd
   
   sf.query("SELECT Id, Email FROM Contact")
   
   df = pd.DataFrame(data['records']).drop(['attributes'],axis=1)
   
Generate Pandas Dataframe from SFDC API Query (ex.query,query_all) and append related fields from query to data frame

.. code-block:: python
   
   import pandas as pd
   
   def sf_api_query(data):
    df = pd.DataFrame(data['records']).drop('attributes', axis=1)
    listColumns = list(df.columns)
    for col in listColumns:
        if any (isinstance (df[col].values[i], dict) for i in range(0, len(df[col].values))):
            df = pd.concat([df.drop(columns=[col]),df[col].apply(pd.Series).drop('attributes',axis=1).add_prefix(col+'.')],axis=1)
            new_columns = np.setdiff1d(df.columns, listColumns)
            for i in new_columns:
                listColumns.append(i)
    return df
   
   df = sf_api_query(sf.query("SELECT Id, Email,ParentAccount.Name FROM Contact"))
      
Generate Pandas Dataframe from SFDC Bulk API Query (ex.bulk.Account.query)

.. code-block:: python
   
   import pandas as pd
   
   sf.bulk.Account.query("SELECT Id, Email FROM Contact")   
   df = pd.DataFrame.from_dict(data,orient='columns').drop('attributes',axis=1)
      

YouTube Tutorial
--------------------------
Here is a helpful  `YouTube tutorial`_  which shows how you can manage records in bulk using a jupyter notebook, simple-salesforce and pandas. 

This can be a effective way to manage records, and perform simple operations like reassigning accounts, deleting test records, inserting new records, etc...

.. _YouTube tutorial: https://youtu.be/nPQFUgsk6Oo?t=282

Authors & License
--------------------------

This package is released under an open source Apache 2.0 license. Simple-Salesforce was originally written by `Nick Catalano`_ but most newer features and bugfixes come from `community contributors`_. Pull requests submitted to the `GitHub Repo`_ are highly encouraged!

Authentication mechanisms were adapted from Dave Wingate's `RestForce`_ and licensed under a MIT license

The latest build status can be found at `Travis CI`_

.. _Nick Catalano: https://github.com/nickcatal
.. _community contributors: https://github.com/simple-salesforce/simple-salesforce/graphs/contributors
.. _RestForce: http://pypi.python.org/pypi/RestForce/
.. _GitHub Repo: https://github.com/simple-salesforce/simple-salesforce
.. _Travis CI: https://travis-ci.com/simple-salesforce/simple-salesforce
