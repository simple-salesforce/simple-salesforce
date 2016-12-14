Using Apex
----------

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

.. _Force.com Apex Code Developer's Guide: http://www.salesforce.com/us/developer/docs/apexcode
