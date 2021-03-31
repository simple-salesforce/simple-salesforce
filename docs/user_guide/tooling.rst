Using Tooling API
-----------------

You can also use this library to call custom Tooling methods:

Retrieve objects:
.. code-block:: python


    result = sf.toolingexecute('sobjects/GlobalValueSet/ABCDEFG')

This would retrieve data from the endpoint ``https://<instance>.salesforce.com/data/v{version}}/tooling/sobjects/GlobalValueSet``

Patch objects:
.. code-block:: python

    payload = {
      "Metadata": {

        'customValue' : [
            {'color': None,
            'default': False,
            'description': None,
            'isActive': None,
            'label': 'ABC',
            'urls': None,
            'valueName': 'ABC'
            }

        ]

      },

    'FullName': 'ABCDEFG'
    }
    result = sf.toolingexecute('sobjects/GlobalValueSet/ABCDEFG', method='PATCH', data=payload)

This would call the endpoint ``https://<instance>.salesforce.com/data/v{version}}/tooling/sobjects/GlobalValueSet`` with ``data=`` as
the body content encoded with ``json.dumps``

You can read more about Tooling API on the `Force.com Tooling API Code Developer's Guide`_

.. _Force.com Tooling API Code Developer's Guide: https://developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/intro_api_tooling.htm
