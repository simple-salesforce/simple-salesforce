CRUD Metadata API Calls
-----------------------

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

   result = sf.mdapi.deploy("path/to/zip", sandbox=False)
   asyncId = result.get('asyncId')
   state = result.get('state')

Both deploy and check_deploy_status take keyword arguments. The single package argument is not currently available to be set for deployments. More details on the deploy options can be found at https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_deploy.htm

You can check on the progress of the deploy which returns a dictionary with status, state_detail, deployment_detail, unit_test_detail:

.. code-block:: python

   sf.mdapi.check_deploy_status(asyncId)

Example of a use-case:

.. code-block:: python

   from simple_salesforce import Salesforce

   deployment_finished = False
   successful = False

   sf = Salesforce(session_id="id", instance="instance")
   sf.mdapi.deploy("path/to/zip", sandbox=False)

   while not deployment_finished:
       result = sf.mdapi.check_deploy_status(asyncId)
       if result.get('status') in ["Succeeded", "Completed", "Error", "Failed", None]:
           deployment_finished = True
       if result.get('status') in ["Succeeded", "Completed"]:
           successful = True

   if successful:
       print("✅")
   else:
       print("🥔")
