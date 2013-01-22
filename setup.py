from setuptools import setup
import textwrap

setup(
    name='simple-salesforce',
    version='0.2',
    author='Nick Catalano',
    packages=['simple_salesforce',],
    url='https://github.com/neworganizing/simple-salesforce',
    license='APACHE',
    description="Simple Salesforce is a basic Salesforce.com REST API client. The goal is to provide a very low-level interface to the API, returning a dictionary of the API JSON response.",
    long_description=textwrap.dedent("""\

*****************
Simple Salesforce
*****************

Simple Salesforce is a basic Salesforce.com REST API client. The goal is to provide a very low-level interface to the API, returning a dictionary of the API JSON response.

You can find out more regarding the format of the results in the `Official Salesforce.com REST API Documentation`_

.. _Official Salesforce.com REST API Documentation: http://www.salesforce.com/us/developer/docs/api_rest/index.htm

Example
-------
To login, simply include the SalesforceAPI method and pass in your Salesforce username, password and token (this is usually provided when you change your password)::

    from simple_salesforce import SalesforceAPI
    sf = SalesforceAPI('myemail@example.com', 'password', 'token')

If you'd like to enter a sandbox, simply append ``True`` to your ``SalesforceAPI()`` call.

For example::

    from simple_salesforce import SalesforceAPI
    sf = SalesforceAPI('myemail@example.com.sandbox', 'password', 'token', True)

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


Authors & License
-----------------

This plugin was built in-house by the team at `New Organizing Institute`_ led by `Nick Catalano`_ and is released under an open source Apache 2.0 license.

Authentication mechanisms were adapted from Dave Wingate's `RestForce`_ and licensed under a MIT license

.. _New Organizing Institute: http://neworganizing.com/
.. _Nick Catalano: https://github.com/nickcatal
.. _RestForce: http://pypi.python.org/pypi/RestForce/

    """),
    install_requires=[
        'requests',
    ],
    keywords = "python salesforce salesforce.com",
    classifiers=['Development Status :: 4 - Beta', 'Environment :: Console', 'Intended Audience :: Developers', 'Natural Language :: English', 'Operating System :: OS Independent', 'Topic :: Internet :: WWW/HTTP'],
)