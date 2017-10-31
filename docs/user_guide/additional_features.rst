Additional Features
-------------------

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
