Using REST
----------

In addition to built in functions that allow integrations with the Salesforce Apex and SOAP endpoints the Simple Salesforce package can be used to target the REST API. This example will demonstrate how to "Submit", `SFDC Submit documentation`_, a process approval in SFDC through the REST API.

.. _SFDC Submit documentation: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_process_approvals_submit.htm

1. Import any dependent packages to your script. For this example we use Simple Salesforce, Requests and the built in JSON package:

.. code-block:: python

    import json, requests, simple_salesforce


1. Authenticate and create an instance of your Salesforce environment using SalesForceLogin:

.. code-block:: python

    session_id, instance = simple_salesforce.SalesforceLogin(
            username=sf_user,
            password=sf_password,
            security_token=sf_token)

2. Build the body of the request using information specific to your environment:

.. code-block:: python

    body = {"requests" : [{
            "actionType": "Submit",
            "contextId": "001D000000I8mIm",
            "nextApproverIds": ["005D00000015rY9"],
            "comments":"this is a test",
            "contextActorId": "005D00000015rZy",
            "processDefinitionNameOrId" : "PTO_Request_Process",
            "skipEntryCriteria": "true"}]
            }

3. Generate the endpoint url and request headers dynamically using your specific SalesForceLogin instance and session id from above:

.. code-block:: python

    url = f"https://{instance}/services/data/v55.0/process/approvals/"
    headers = {"Content-Type": "application/json", 'Authorization': 'Bearer ' + session_id}

4. Use your favorite libraries, in this example we use Requests and JSON, to send a HTTP request to the REST API:

.. code-block:: python

    response = requests.post(url, data=json.dumps(body), headers=headers)

5. A response will be returned in a JSON string that can be loaded into your script using the following:

.. code-block:: python

    resp = response.json()

This response will match the following format:

.. code-block:: python

    [ {
      "actorIds" : [ "005D00000015rY9IAI" ],
       "entityId" : "001D000000I8mImIAJ",
       "errors" : null,
       "instanceId" : "04gD0000000Cvm5IAC",
       "instanceStatus" : "Pending",
       "newWorkitemIds" : [ "04iD0000000Cw6SIAS" ],
       "success" : true } ]

You can learn more about SFDC REST and the available calls on `Salesforce REST API Developer Guide`_

.. _Salesforce REST API Developer Guide: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_rest.htm
