Using Bulk 2.0
--------------

You can use this library to access Bulk 2.0 API functions.

Create new records:

.. code-block:: text

    "Custom_Id__c","AccountId","Email","FirstName","LastName"
    "CustomID1","ID-13","contact1@example.com","Bob","x"
    "CustomID2","ID-24","contact2@example.com","Alice","y"
    ...

.. code-block:: python

    sf.bulk2.Contact.insert(data="./sample.csv", batch_size=10000)


Create new records concurrently:

.. code-block:: python

    sf.bulk2.Contact.insert(data="./sample.csv", batch_size=10000, concurrency=10)


Update existing records:

.. code-block:: text

    "Custom_Id__c","AccountId","Email","FirstName","LastName"
    "CustomID1","ID-13","contact1@example.com","Bob","X"
    "CustomID2","ID-24","contact2@example.com","Alice","Y"
    ...

.. code-block:: python

    sf.bulk2.Contact.update(data="./sample.csv")


Upsert records from csv:

.. code-block:: text

    "Custom_Id__c","LastName"
    "CustomID1","X"
    "CustomID2","Y"
    ...

.. code-block:: python

    sf.bulk2.Contact.upsert(data="./sample.csv", external_id_field='Custom_Id__c')


Upsert records from dict:


.. code-block:: python

    data = [
          {'Custom_Id__c': 'CustomID1', 'LastName': 'X'},
          {'Custom_Id__c': 'CustomID2', 'LastName': 'Y'}
        ]

    sf.bulk2.Contact.upsert(data=df.to_dict(orient='records'), external_id_field='Custom_Id__c')


Query records:

.. code-block:: python

    query = 'SELECT Id, Name FROM Account LIMIT 100000'

    results = sf.bulk2.Account.query(
        query, max_records=50000, column_delimiter="COMMA", line_ending="LF"
    )
    for i, data in enumerate(results):
        with open(f"results/part-{i}.csv", "w") as bos:
            bos.write(data)


Download records(low memory usage):

.. code-block:: python

    query = 'SELECT Id, Name FROM Account'

    sf.bulk2.Account.download(
        query, path="results/", max_records=200000
    )


Delete records (soft deletion):

.. code-block:: text

    "Id"
    "0000000000AAAAA"
    "0000000000BBBBB"
    ...


.. code-block:: python

    sf.bulk2.Contact.delete(data="./sample.csv")


Hard deletion:

.. code-block:: python

    sf.bulk2.Contact.hard_delete(data="./sample.csv")


Retrieve failed/successful/unprocessed records for ingest(insert,update...) job:

.. code-block:: python

    results = sf.bulk2.Contact.insert(data="./sample.csv")
    # [{"numberRecordsFailed": 123, "numberRecordsProcessed": 2000, "numberRecordsTotal": 2000, "job_id": "Job-1"}, ...]
    for result in results:
        job_id = result['job_id']
        # also available: get_unprocessed_records, get_successful_records
        data = sf.bulk2.Contact.get_failed_records(job_id)
        # or save to file
        sf.bulk2.Contact.get_failed_records(job_id, path=f'{job_id}.csv')
