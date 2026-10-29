Helpful Datetime Resources
--------------------------
A list of helpful resources when working with datetime/dates from Salesforce

Convert SFDC Datetime to Datetime or Date object

.. code-block:: python

    import datetime
    # Formatting to SFDC datetime
    formatted_datetime = datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z")

    # Formatting to SFDC date
    formatted_date = datetime.datetime.strptime(x, "%Y-%m-%d")

Helpful Pandas Resources
------------------------
A list of helpful resources when working with Pandas and simple-salesforce

Generate list for SFDC Query "IN" operations from a Pandas Dataframe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pandas as pd

    df = pd.DataFrame([{'Id':1},{'Id':2},{'Id':3}])
    def dataframe_to_sfdc_list(df, column):
        df_list = df[column].unique()
        df_list = [str(x) for x in df_list]
        df_list = ','.join("'" + item + "'" for item in df_list)
        return df_list

    sf.query(format_soql(
        "SELECT Id, Email FROM Contact WHERE Id IN ({})",
        dataframe_to_sfdc_list(df, column)
    ))

Generate Pandas Dataframe from SFDC API Query (ex.query,query_all)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pandas as pd

    sf.query("SELECT Id, Email FROM Contact")

    df = pd.DataFrame(data['records']).drop(['attributes'],axis=1)

Generate Pandas Dataframe from SFDC API Query (ex.query,query_all) and append related fields from query to data frame
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pandas as pd

    def sf_api_query(data):
        df = pd.DataFrame(data['records']).drop('attributes', axis=1)
        listColumns = list(df.columns)
        for col in listColumns:
            if any (isinstance (df[col].values[i], dict) for i in range(0, len(df[col].values))):
                df_no_col = df.drop(columns=[col])
                expanded_col = df[col].apply(pd.Series, dtype=df[col].dtype)
                expanded_col = expanded_col.drop('attributes', axis=1)
                expanded_col = expanded_col.add_prefix(col + '.')
                df = pd.concat([df_no_col, expanded_col], axis=1)
                new_columns = np.setdiff1d(df.columns, listColumns)
                for i in new_columns:
                    listColumns.append(i)
        return df

    df = sf_api_query(sf.query("SELECT Id, Email, ParentAccount.Name FROM Contact"))

Generate Pandas Dataframe from SFDC Bulk API Query (ex.bulk.Account.query)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import pandas as pd

    sf.bulk.Account.query("SELECT Id, Email FROM Contact")
    df = pd.DataFrame.from_dict(data,orient='columns').drop('attributes',axis=1)


YouTube Tutorial
----------------
Here is a helpful `YouTube tutorial`_ which shows how you can manage records in bulk using a jupyter notebook, simple-salesforce and pandas.

This can be a effective way to manage records, and perform simple operations like reassigning accounts, deleting test records, inserting new records, etc...

.. _YouTube tutorial: https://youtu.be/nPQFUgsk6Oo?t=282