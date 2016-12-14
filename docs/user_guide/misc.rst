Other Options
-------------

To insert or update (upsert) a record using an external ID, use:

.. code-block:: python

    sf.Contact.upsert('customExtIdField__c/11999',{'LastName': 'Smith','Email': 'smith@example.com'})

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
