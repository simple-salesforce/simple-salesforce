Record Management
-----------------

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

To retrieve a list of deleted records between ``2013-10-20`` to ``2013-10-29`` (datetimes are required to be in UTC):

.. code-block:: python

    import pytz
    import datetime
    end = datetime.datetime.now(pytz.UTC)  # we need to use UTC as salesforce API requires this!
    sf.Contact.deleted(end - datetime.timedelta(days=10), end)

To retrieve a list of updated records between ``2014-03-20`` to ``2014-03-22`` (datetimes are required to be in UTC):

.. code-block:: python

    import pytz
    import datetime
    end = datetime.datetime.now(pytz.UTC) # we need to use UTC as salesforce API requires this
    sf.Contact.updated(end - datetime.timedelta(days=10), end)

Note that Update, Delete and Upsert actions return the associated `Salesforce HTTP Status Code`_

.. _Salesforce HTTP Status Code: http://www.salesforce.com/us/developer/docs/api_rest/Content/errorcodes.htm

Use the same format to create any record, including 'Account', 'Opportunity', and 'Lead'.
Make sure to have all the required fields for any entry. The `Salesforce API`_ has all objects found under 'Reference -> Standard Objects' and the required fields can be found there.

.. _Salesforce HTTP Status Code: http://www.salesforce.com/us/developer/docs/api_rest/Content/errorcodes.htm
.. _Salesforce API: https://www.salesforce.com/developer/docs/api/
