Examples
-------
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

There are also two means of authentication, one that uses username, password and security token and the other that uses IP filtering, username, password  and organizationId

To login using the security token method, simply include the Salesforce method and pass in your Salesforce username, password and token (this is usually provided when you change your password):

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com', password='password', security_token='token')

To login using IP-whitelist Organization ID method, simply use your Salesforce username, password and organizationId:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(password='password', username='myemail@example.com', organizationId='OrgId')

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

If you view the API calls in your Salesforce instance by Client Id it will be prefixed with ``RestForce/``, for example ``RestForce/My App``.

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
