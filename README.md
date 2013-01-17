#Simple Salesforce
A Basic Salesforce.com REST API Client for Python

## Example
To login, simply include the SalesforceAPI method and pass in your Salesforce username, password and token (this is usually provided when you change your password)

    from simple_salesforce import SalesforceAPI
    sf = SalesforceAPI('myemail@example.com', 'password', 'token')

#### Record Management

To create a new 'Contact' in Salesforce

    sf.Contact.create({'LastName':'Smith','Email':'example@example.com'})

This will return a dictionary such as `{u'errors': [], u'id': u'003e0000003GuNXAA0', u'success': True}`

To get a dictionary with all the information regarding that record, use 

    contact = sf.Contact.get('003e0000003GuNXAA0')

To change that contact's last name from 'Smith' to 'Jones' and add a first name of 'John' use

    sf.Contact.update('003e0000003GuNXAA0',{'LastName': 'Jones', 'FirstName': 'John'})

To delete the contact

    sf.Contact.delete('003e0000003GuNXAA0')

#### Queries

It's also possible to write select queries in Salesforce Object Query Language (SOQL) and search queries in Salesforce Object Search Language (SOSL).

SOQL queries are done via

    sf.query("SELECT Id, Email FROM Contact WHERE LastName = 'Jones'")

SOSL queries are done via

    sf.search("FIND {Jones}")

There is also 'Quick Search', which inserts your query inside the {} in the SOSL syntax. Be careful, there is no escaping!

    sf.quick_search("Jones")

Search and Quick Search return `None` if there are no records, otherwise they return a dictionary of search results.

More details about syntax is available on the [Salesforce Developer Website](http://www.salesforce.com/us/developer/docs/soql_sosl/index.htm)

#### Other Options

To insert or update (upsert) a record using an external ID, use

    sf.Contact.upsert('customExtIdField__c/11999',{'LastName': 'Smith','Email': 'smith@example.com'})

To retrieve basic metadata use

    sf.Contact.metadata()

To retrieve a description of the object, use

    sf.Contact.describe()


# Authors & License

This plugin was built in-house by the team at [New Organizing Institute](http://neworganizing.com/) led by [Nick Catalano](https://github.com/nickcatal) and is released under an open source Apache 2.0 license.

Authentication mechanisms were adapted from Dave Wingate's [RestForce](http://pypi.python.org/pypi/RestForce/) and licensed under a MIT license