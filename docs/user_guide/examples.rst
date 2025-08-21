Examples
-------
There are two ways to gain access to Salesforce

The first is to simply pass the domain of your Salesforce instance and an access token straight to ``Salesforce()``

For example:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(instance='na1.salesforce.com', session_id='')

If you have the full URL of your instance (perhaps including the scheme, as is included in the OAuth2 request process), you can pass that in instead using ``instance_url``:

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(instance_url='https://na1.salesforce.com', session_id='')

There are also four means of authentication, one that uses username, password and security token; one that uses IP filtering, username, password and organizationId, one that uses a private key to sign a JWT, and one for connected apps that uses username, password, consumer key, and consumer secret;

To login using the security token method, simply include the Salesforce method and pass in your Salesforce username, password and token (this is usually provided when you change your password or go to profile -> settings -> Reset My Security Token):

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

Connected apps may also be configured with a ``client_id`` and ``client_secret`` (renamed here as ``consumer_key`` and ``consumer_secret``), and a ``domain``.
The ``domain`` for the url ``https://organization.my.salesforce.com`` would be ``organization.my``

.. code-block:: python

    from simple_salesforce import Salesforce
    sf = Salesforce(consumer_key='sfdc_client_id', consumer_secret='sfdc_client_secret', domain='organization.my')

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
