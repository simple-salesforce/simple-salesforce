*****************
Simple Salesforce
*****************

Simple Salesforce is a basic Salesforce.com REST API client. The goal is to provide a very low-level interface to the API, returning a dictionary of the API JSON response.

You can find out more regarding the format of the results in the `Official Salesforce.com REST API Documentation`_

.. _Official Salesforce.com REST API Documentation: http://www.salesforce.com/us/developer/docs/api_rest/index.htm

Example
-------
There are two ways to gain access to Salesforce

The first is to simply pass the domain of your Salesforce instance and an access token straight to ``Salesforce()``

For example::

    from simple_salesforce import Salesforce
    sf = Salesforce(instance='na1.salesforce.com', session_id='')

If you have the full URL of your instance (perhaps including the schema, as is included in the OAuth2 request process), you can pass that in instead using ``instance_url``::

    from simple_salesforce import Salesforce
    sf = Salesforce(instance_url='https://na1.salesforce.com', session_id='')

To login, simply include the Salesforce method and pass in your Salesforce username, password and token (this is usually provided when you change your password)::

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com', password='password', security_token='token')

If you'd like to enter a sandbox, simply add ``sandbox=True`` to your ``Salesforce()`` call.

For example::

    from simple_salesforce import Salesforce
    sf = Salesforce(username='myemail@example.com.sandbox', password='password', security_token='token', sandbox=True)

Note that specifying if you want to use a sandbox is only necessary if you are using the built-in username/password/security token authentication and is used exclusively during the authentication step.

Record Management
-----------------

To create a new 'Contact' in Salesforce::

    sf.Contact.create({'LastName':'Smith','Email':'example@example.com'})

This will return a dictionary such as ``{u'errors': [], u'id': u'003e0000003GuNXAA0', u'success': True}``

To get a dictionary with all the information regarding that record, use::

    contact = sf.Contact.get('003e0000003GuNXAA0')

To change that contact's last name from 'Smith' to 'Jones' and add a first name of 'John' use::

    sf.Contact.update('003e0000003GuNXAA0',{'LastName': 'Jones', 'FirstName': 'John'})

To delete the contact::

    sf.Contact.delete('003e0000003GuNXAA0')

Note that Update, Delete and Upsert actions return the associated `Salesforce HTTP Status Code`_

.. _Salesforce HTTP Status Code: http://www.salesforce.com/us/developer/docs/api_rest/Content/errorcodes.htm

Queries
-------

It's also possible to write select queries in Salesforce Object Query Language (SOQL) and search queries in Salesforce Object Search Language (SOSL).

SOQL queries are done via

::

    sf.query("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

If, due to an especially large result, Salesforce adds a ``nextRecordsUrl`` to your query result, such as ``"nextRecordsUrl" : "/services/data/v26.0/query/01gD0000002HU6KIAW-2000"``, you can pull the additional results with either the ID or the full URL (if using the full URL, you must pass 'True' as your second argument)

::

    sf.query_more("01gD0000002HU6KIAW-2000")
    sf.query_more("/services/data/v26.0/query/01gD0000002HU6KIAW-2000", True)

As a convenience, to retrieve all of the results in a single local method call use

::

    sf.query_all("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

SOSL queries are done via::

    sf.search("FIND {Jones}")

There is also 'Quick Search', which inserts your query inside the {} in the SOSL syntax. Be careful, there is no escaping!

::

    sf.quick_search("Jones")

Search and Quick Search return ``None`` if there are no records, otherwise they return a dictionary of search results.

More details about syntax is available on the `Salesforce Query Language Documentation Developer Website`_

.. _Salesforce Query Language Documentation Developer Website: http://www.salesforce.com/us/developer/docs/soql_sosl/index.htm

Other Options
-------------

To insert or update (upsert) a record using an external ID, use::

    sf.Contact.upsert('customExtIdField__c/11999',{'LastName': 'Smith','Email': 'smith@example.com'})

To retrieve basic metadata use::

    sf.Contact.metadata()

To retrieve a description of the object, use::

    sf.Contact.describe()


Additional Features
-------------------

There are a few helper classes that are used internally and available to you.

Included in them are ``SalesforceLogin``, which takes in a username, password, security token, optional boolean sandbox indicator and optional version and returns a touple of ``(session_id, sf_instance)`` where `session_id` is the session ID to use for authentication to Salesforce and ``sf_instance`` is the domain of the instance of Salesforce to use for the session.

For example, to use SalesforceLogin for a sandbox account you'd use::

    from simple_salesforce import SalesforceLogin
    session_id, instance = SalesforceLogin('myemail@example.com.sandbox', 'password', 'token', True)

Simply leave off the final ``True`` if you do not wish to use a sandbox.

Also exposed is the ``SFType`` class, which is used internally by the ``__getattr__()`` method in the ``Salesforce()`` class and represents a specific SObject type. ``SFType`` requires ``object_name`` (i.e. ``Contact``), ``session_id`` (an authentication ID), ``sf_instance`` (hostname of your Salesforce instance), and an optional ``sf_version``

To add a Contact using the default version of the API you'd use::

    from simple_salesforce import SFType
    contact = SFType('Contact','sesssionid','na1.salesforce.com')
    contact.create({'LastName':'Smith','Email':'example@example.com'})


Authors & License
-----------------

This plugin was built in-house by the team at `New Organizing Institute`_ led by `Nick Catalano`_ and is released under an open source Apache 2.0 license. The team at `Cedexis`_ has contributed to the project as well.

Authentication mechanisms were adapted from Dave Wingate's `RestForce`_ and licensed under a MIT license

.. _New Organizing Institute: http://neworganizing.com/
.. _Nick Catalano: https://github.com/nickcatal
.. _RestForce: http://pypi.python.org/pypi/RestForce/
.. _Cedexis: http://www.cedexis.com/
