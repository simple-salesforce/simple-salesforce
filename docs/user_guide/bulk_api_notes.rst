====================
Bulk API Usage Notes
====================

It is worth noting that the Bulk API is a common resource to build applications that extract or import data regularly on the Salesforce Platform. Its error messages can sometimes be cryptic, however. For example, if you try to insert a record with a duplicate external ID, you will get an error message that says "Duplicate External ID specified: [External ID Field Name]". This is not very helpful, as it does not tell you which record is causing the problem. You will need to query the records to find the duplicate. This is a common issue with the Bulk API, and it is worth noting that you will need to handle these errors in your application.

Exception Code "InvalidBatch" with message "Records not processed"
==================================================================

When processing your Bulk API request, one of the first things Salesforce does is to check the schema of your payload. If the schema is not correct, you will get an error message with the exception code "InvalidBatch" and the message "Records not processed".

A common cause for this error is to have a misrepresented field in your payload (that is: something that shouldn't be there). For example, if you are trying to insert a record with a field that does not exist in the object, you will get this error. Another common cause is to have a field with the *wrong data type*. For example, if you are trying to insert a record with a field that is a number, but you are sending a string, you will get this error.

Another, not so common cause, is to think to have the correct schema in place, while in fact you don't. For example, if you are trying to insert a record with a field that is a lookup to another object, but you are sending the wrong ID (external key or not), you will get this error. **Check that your schema is correct.** You might have two objects with the same name but different API names in Salesforce (for example: "Environment" from the DevOps Center managed package by salesforce and another "Environment" custom object that you have in your org, and when creating the lookup field in your other custom object, you accidentaly selected the managed package object instead of your custom object).

Working with an output from Pandas
==================================

If you are working with the Pandas library in Python, you might want to use the `to_dict` method to convert your DataFrame to a dictionary. This is a good idea, but you need to be careful with the data types.

For example, if you have a column that is going to be mapped to a Salesforce date/time field, you might want to convert it to the ISO format before uploading the data with the Bulk API. There are many ways of converting a number or string to the ISO format, but here's an example:

.. code-block:: python

    my_dataframe['CreatedDate'] = my_dataframe['CreatedDate'].dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')

This will convert the `CreatedDate` column to the ISO format, which is one of the formats that Salesforce expects.

Preparing the dataframe for the Bulk API if you are using external ids in a lookup relationship
-----------------------------------------------------------------------------------------------

If you are upserting data that looks up to existing data in Salesforce through an external id, make sure you define the dictionary object in the Python code before calling the *sf.bulk.* methods. For example, if you have a custom object called "MyCustomObject__c" that has a lookup relationship to the Account object, and you are using the `AccountNumber` field as the external id, you will need to define the dictionary object like this:

.. code-block:: python

    my_dataframe['Account__r'] = my_dataframe['Account__r'].apply(lambda x: {'AccountNumber': x})

This will convert the `Account__r` column to a dictionary with the external id field that you are using to look up the Account object, as in:

.. code-block:: python

    # suppose the account record was a simple dictionary like this:
    account_row = { "Name": "Acme, Inc" } 

    # after applying that lambda specified above, the object looks like this:
    account_row = { "Name": "Acme, Inc", "Account__r": { "AccountNumber": "1234" }}

This is because of the way relationships work in Salesforce. If you are somewhat familiar with how the platform's database works, you will notice that for the row that is going to be inserted the column that references the lookup field is going to be transformed into an attribute that points to an object, in a similar way that in Apex you use the relationship field to access the fields of the related object. This works for standard objects as well, where instead of *ContactId* you would use just *Contact*.