Queries
-------

It's also possible to write select queries in Salesforce Object Query Language (SOQL) and search queries in Salesforce Object Search Language (SOSL).

SOQL queries are done via:

.. code-block:: python

    sf.query("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

If, due to an especially large result, Salesforce adds a ``nextRecordsUrl`` to your query result, such as ``"nextRecordsUrl" : "/services/data/v26.0/query/01gD0000002HU6KIAW-2000"``, you can pull the additional results with either the ID or the full URL (if using the full URL, you must pass 'True' as your second argument)

.. code-block:: python

    sf.query_more("01gD0000002HU6KIAW-2000")
    sf.query_more("/services/data/v26.0/query/01gD0000002HU6KIAW-2000", True)

As a convenience, to retrieve all of the results in a single local method call use

.. code-block:: python

    sf.query_all("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

While ``query_all`` materializes the whole result into a Python list, ``query_all_iter`` returns an iterator, which allows you to lazily process each element separately

.. code-block:: python

    data = sf.query_all_iter("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")
    for row in data:
      process(row)

Values used in SOQL queries can be quoted and escaped using ``format_soql``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName = {}", "Jones"))
    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName = {last_name}", last_name="Jones"))
    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE LastName IN {names}", names=["Smith", "Jones"]))

To skip quoting and escaping for one value while still using the format string, use ``:literal``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE Income > {:literal}", "USD100"))

To escape a substring used in a LIKE expression while being able to use % around it, use ``:like``:

.. code-block:: python

    sf.query(format_soql("SELECT Id, Email FROM Contact WHERE Name LIKE '{:like}%'", "Jones"))

SOSL queries are done via:

.. code-block:: python

    sf.search("FIND {Jones}")

There is also 'Quick Search', which inserts your query inside the {} in the SOSL syntax. Be careful, there is no escaping!

.. code-block:: python

    sf.quick_search("Jones")

Search and Quick Search return ``None`` if there are no records, otherwise they return a dictionary of search results.

More details about syntax is available on the `Salesforce Query Language Documentation Developer Website`_

.. _Salesforce Query Language Documentation Developer Website: http://www.salesforce.com/us/developer/docs/soql_sosl/index.htm
