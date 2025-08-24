""" Classes for interacting with Salesforce Bulk API """

import concurrent.futures
import json
from collections import OrderedDict
from functools import partial
from time import sleep
from typing import Any, Dict, Iterable, List, Optional, Union, cast

import requests

from .exceptions import SalesforceGeneralError
from .util import BulkDataAny, BulkDataStr, Headers, Proxies, \
    call_salesforce, \
    list_from_generator


class SFBulkHandler:
    """ Bulk API request handler
    Intermediate class which allows us to use commands,
     such as 'sf.bulk.Contacts.create(...)'
    This is really just a middle layer, whose sole purpose is
    to allow the above syntax
    """

    def __init__(
            self,
            session_id: str,
            bulk_url: str,
            proxies: Optional[Proxies] = None,
            session: Optional[requests.Session] = None
            ):
        """Initialize the instance with the given parameters.

        Arguments:

        * session_id -- the session ID for authenticating to Salesforce
        * bulk_url -- API endpoint set in Salesforce instance
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.session_id = session_id
        self.session = session or requests.Session()
        self.bulk_url = bulk_url
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies

        # Define these headers separate from Salesforce class,
        # as bulk uses a slightly different format
        self.headers = {
            'Content-Type': 'application/json',
            'X-SFDC-Session': self.session_id,
            'X-PrettyPrint': '1'
            }

    def __getattr__(self,
                    name: str
                    ) -> "SFBulkType":
        return SFBulkType(object_name=name,
                          bulk_url=self.bulk_url,
                          headers=self.headers,
                          session=self.session
                          )

    def submit_dml(self,
                   object_name: str,
                   dml: str,
                   data: BulkDataAny,
                   external_id_field: str = None,
                   batch_size: int = 10000,
                   use_serial: bool = False,
                   bypass_results: bool = False,
                   include_detailed_results: bool = False
                   ):
        """ Perform any DML operation on any custom or
            standard object in Salesforce
            i.e. insert/upsert/update/delete

            Required to put this function in this class due to error:
            TypeError: 'SFBulkType' object is not callable
            - this makes SFBulkType callable for this specific function

            The main purpose of this function is to
            build customizable reporting functions and reduce code reuse
            in individual execution scripts mainly with pandas

        Arguments:

        * object_name       -- SF object
        * dml               -- insert, upsert, update, delete
        * data              -- JSON formatted salesforce records.

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`

        * batch_size        -- default to 10,000
        * use_serial        -- default: bool = False
        * bypass_results    -- default: bool = False,
        * include_detailed_results  --default: bool = False,
        * external_id_field -- unique identifier field for upsert operations.
        """
        return SFBulkType(object_name=object_name,
                          bulk_url=self.bulk_url,
                          headers=self.headers,
                          session=self.session).submit_dml(dml,
                                                           data,
                                                           external_id_field,
                                                           batch_size,
                                                           use_serial,
                                                           bypass_results,
                                                           include_detailed_results)


class SFBulkType:
    """ Interface to Bulk/Async API functions"""

    def __init__(
            self,
            object_name: str,
            bulk_url: str,
            headers: Headers,
            session: requests.Session
            ):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * bulk_url -- API endpoint set in Salesforce instance
        * headers -- bulk API headers
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.object_name = object_name
        self.bulk_url = bulk_url
        self.session = session
        self.headers = headers

    def _create_job(self,
                    operation: str,
                    use_serial: bool,
                    external_id_field: Optional[str] = None
                    ) -> Any:
        """ Create a bulk job

        Arguments:

        * operation -- Bulk operation to be performed by job
        * use_serial -- Process batches in order
        * external_id_field -- unique identifier field for upsert operations
        """

        payload = {
            'operation': operation,
            'object': self.object_name,
            'concurrencyMode': 1 if use_serial else 0,
            'contentType': 'JSON'
            }

        if operation == 'upsert':
            payload['externalIdFieldName'] = external_id_field

        url = f'{self.bulk_url}job'

        result = call_salesforce(url=url,
                                 method='POST',
                                 session=self.session,
                                 headers=self.headers,
                                 data=json.dumps(payload,
                                                 allow_nan=False
                                                 )
                                 )
        return result.json(object_pairs_hook=OrderedDict)

    def _close_job(self,
                   job_id: str
                   ) -> Any:
        """ Close a bulk job """
        payload = {
            'state': 'Closed'
            }

        url = f'{self.bulk_url}job/{job_id}'

        result = call_salesforce(url=url,
                                 method='POST',
                                 session=self.session,
                                 headers=self.headers,
                                 data=json.dumps(payload,
                                                 allow_nan=False
                                                 )
                                 )
        return result.json(object_pairs_hook=OrderedDict)

    def _get_job(self,
                 job_id: str
                 ) -> Any:
        """ Get an existing job to check the status """
        url = f'{self.bulk_url}job/{job_id}'

        result = call_salesforce(url=url,
                                 method='GET',
                                 session=self.session,
                                 headers=self.headers
                                 )
        return result.json(object_pairs_hook=OrderedDict)

    def _add_batch(
            self,
            job_id: str,
            data: BulkDataAny,
            operation: str
            ) -> Any:
        """ Add a set of data as a batch to an existing job
        Separating this out in case of later
        implementations involving multiple batches
        """

        url = f'{self.bulk_url}job/{job_id}/batch'

        data_: Union[BulkDataAny, str]
        if operation not in ('query', 'queryAll'):
            data_ = json.dumps(data,
                               allow_nan=False
                               )
        else:
            data_ = data

        result = call_salesforce(url=url,
                                 method='POST',
                                 session=self.session,
                                 headers=self.headers,
                                 data=data_
                                 )
        return result.json(object_pairs_hook=OrderedDict)

    def _get_batch(self,
                   job_id: str,
                   batch_id: str
                   ) -> Any:
        """ Get an existing batch to check the status """

        url = f'{self.bulk_url}job/{job_id}/batch/{batch_id}'

        result = call_salesforce(url=url,
                                 method='GET',
                                 session=self.session,
                                 headers=self.headers
                                 )
        return result.json(object_pairs_hook=OrderedDict)

    def _get_batch_results(
            self,
            job_id: str,
            batch_id: str,
            operation: str
            ) -> Iterable[Any]:
        """ retrieve a set of results from a completed job """

        url = f'{self.bulk_url}job/{job_id}/batch/{batch_id}/result'

        result = call_salesforce(url=url,
                                 method='GET',
                                 session=self.session,
                                 headers=self.headers
                                 )

        if operation in ('query', 'queryAll'):
            for batch_result in result.json():
                url_query_results = f'{url}/{batch_result}'
                batch_query_result = call_salesforce(url=url_query_results,
                                                     method='GET',
                                                     session=self.session,
                                                     headers=self.headers
                                                     ).json()
                yield batch_query_result
        else:
            yield result.json()

    def _get_batch_request_with_batch_results(self,
                                              job_id: str,
                                              batch_id: str,
                                              ) -> Iterable[Any]:
        """ retrieve a set of results from a completed job """
 
        url = f'{self.bulk_url}job/{job_id}/batch/{batch_id}/request'
 
        batch_request = call_salesforce(url=url,
                                        method='GET',
                                        session=self.session,
                                        headers=self.headers
                                        )
 
        batch_results = self._get_batch_results(job_id,
                                               batch_id,
                                               operation='batch_results'
                                               )
        results = []
        for batch_result in batch_results:
            for idx, i in enumerate(batch_result):
                flattened_request_dict = [{
                                              k + '.' + list(v.keys())[0]: v.get(
                                                  list(v.keys())[0]
                                                  )
                                              } if isinstance(v,
                                                              dict
                                                              ) else {
                    k: v
                    }
                                          for k, v in
                                          batch_request.json()[idx].items()]
                for request_field in flattened_request_dict:
                    i.update(request_field)
                results.append(i)
        yield results

    def worker(self,
               batch: Dict[str, Any],
               operation: str,
               wait: int = 5,
               bypass_results: bool = False,
               include_detailed_results: bool = False
               ) -> Iterable[Any]:
        """ Gets batches from concurrent worker threads.
        self._bulk_operation passes batch jobs.
        The worker function checks each batch job waiting for it complete
        and appends the results.
        """
        if not bypass_results:
            batch_status = self._get_batch(job_id=batch['jobId'],
                                           batch_id=batch['id']
                                           )['state']

            while batch_status not in ['Completed', 'Failed', 'NotProcessed']:
                sleep(wait)
                batch_status = self._get_batch(job_id=batch['jobId'],
                                               batch_id=batch['id']
                                               )['state']

            if include_detailed_results:
                result = self._get_batch_request_with_batch_results(
                    job_id=batch['jobId'],
                    batch_id=batch['id']
                    )
            else:
                result = self._get_batch_results(job_id=batch['jobId'],
                                                 batch_id=batch['id'],
                                                 operation=operation
                                                 )
        else:
            result = [{
                'bypass_results': bypass_results,
                'job_id': batch['jobId']
                }]
        return result

    def _add_autosized_batches(
            self,
            data: BulkDataAny,
            operation: str,
            job: str
            ) -> List[Any]:
        """
        Auto-create batches that respect bulk api V1 limits.

        bulk v1 api has following limits
        number of records <= 10000
        AND
        file_size_limit <= 10MB
        AND
        number_of_character_limit <= 10000000

        Documentation on limits can be found at:
        https://developer.salesforce.com/docs/atlas.en-us
        .salesforce_app_limits_cheatsheet.meta
        /salesforce_app_limits_cheatsheet
        /salesforce_app_limits_platform_bulkapi.htm#ingest_jobs

        Our JSON serialization uses the default `ensure_ascii=True`, so the
        character and byte lengths will be the same. Therefore we only need
        to adhere to a single length limit of 10,000,000 characters.

        TODO: In future when simple-salesforce supports bulk api V2
        we should detect api version and set max file size accordingly. V2
        increases file size limit to 150MB

        TODO: support for the following limits have not been added since these
        are record / field level limits and not chunk level limits:
        * Maximum number of fields in a record: 5,000
        * Maximum number of characters in a record: 400,000
        * Maximum number of characters in a field: 131,072
        """
        record_limit = 10_000
        char_limit = 10_000_000

        batches = []
        last_break = 0
        record_count, char_count = 0, 0
        for i, record in enumerate(data):
            # 2 is added to account for the enclosing `[]` for the first record
            # and the separator `, ` between records for subsequent records.
            additional_chars = len(json.dumps(record,
                                              default=str
                                              )
                                   ) + 2
            if any([
                char_count + additional_chars > char_limit,
                record_count == record_limit
                ]
                    ):
                batches.append(data[last_break:i])
                last_break = i
                record_count, char_count = 0, 0
            char_count += additional_chars
            record_count += 1
        if last_break < len(data) - 1:
            batches.append(data[last_break:])

        return [self._add_batch(job_id=job,
                                data=i,
                                operation=operation
                                ) for i in batches]

    # pylint: disable=R0913,line-too-long
    def _bulk_operation(
            self,
            operation: str,
            data: BulkDataAny,
            use_serial: bool = False,
            external_id_field: Optional[str] = None,
            batch_size: Union[int, str] = 10000,
            wait: int = 5,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Iterable[Any]]:
        """ String together helper functions to create a complete
        end-to-end bulk API request
        Arguments:
        * operation -- Bulk operation to be performed by job
        * data -- list of dict to be passed as a batch
        * use_serial -- Process batches in serial mode
        * external_id_field -- unique identifier field for upsert operations
        * wait -- seconds to sleep between checking batch status
        * batch_size -- number of records to assign for each batch in the job
                        or `auto`
        """
        # check for batch size type since now it accepts both integers
        # & the string `auto`
        if not (isinstance(batch_size,
                           int
                           ) or batch_size == 'auto'):
            raise ValueError('batch size should be auto or an integer')
        results: Iterable[Iterable[Any]]
        if operation not in ('query', 'queryAll'):
            # Checks if data is present
            if not data:
                raise ValueError(f'data should not be empty for {operation}')

            # Checks to prevent batch limit
            if batch_size != 'auto':
                batch_size = min(batch_size,
                                 len(data),
                                 10000
                                 )

            with concurrent.futures.ThreadPoolExecutor() as pool:

                job = self._create_job(operation=operation,
                                       use_serial=use_serial,
                                       external_id_field=external_id_field
                                       )
                if batch_size == 'auto':
                    batches = self._add_autosized_batches(job=job['id'],
                                                          data=data,
                                                          operation=operation
                                                          )
                else:
                    batch_size = cast(int,
                                      batch_size
                                      )
                    batches = [
                        self._add_batch(job_id=job['id'],
                                        data=i,
                                        operation=operation
                                        )
                        for i in
                        [data[i * batch_size:(i + 1) * batch_size]
                         for i in range(len(data) // batch_size + 1)] if i]

                multi_thread_worker = partial(self.worker,
                                              operation=operation,
                                              wait=wait,
                                              bypass_results=bypass_results,
                                              include_detailed_results=include_detailed_results
                                              )
                list_of_results = pool.map(multi_thread_worker,
                                           batches
                                           )

                results = [x for sublist in list_of_results for i in
                           sublist for x in i] if not bypass_results else \
                    [{
                        k: v
                        } for sublist in list_of_results for i in
                        sublist for k, v in i.items()]

                self._close_job(job_id=job['id'])

        elif operation in ('query', 'queryAll'):
            job = self._create_job(operation=operation,
                                   use_serial=use_serial,
                                   external_id_field=external_id_field
                                   )

            batch = self._add_batch(job_id=job['id'],
                                    data=data,
                                    operation=operation
                                    )

            self._close_job(job_id=job['id'])

            batch_status = self._get_batch(job_id=batch['jobId'],
                                           batch_id=batch['id']
                                           )

            while batch_status['state'] not in [
                    'Completed', 'Failed', 'NotProcessed'
                    ]:
                sleep(wait)
                batch_status = self._get_batch(job_id=batch['jobId'],
                                               batch_id=batch['id']
                                               )

            if batch_status['state'] == 'Failed':
                raise SalesforceGeneralError('',
                                             batch_status['state'],
                                             batch_status['jobId'],
                                             batch_status['stateMessage']
                                             )
            results = self._get_batch_results(job_id=batch['jobId'],
                                              batch_id=batch['id'],
                                              operation=operation
                                              )
        return results

    # _bulk_operation wrappers to expose supported Salesforce bulk operations
    def delete(
            self,
            data: BulkDataStr,
            batch_size: int = 10000,
            use_serial: bool = False,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Any]:
        """ soft delete records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = self._bulk_operation(use_serial=use_serial,
                                       operation='delete',
                                       data=data,
                                       batch_size=batch_size,
                                       bypass_results=bypass_results,
                                       include_detailed_results=include_detailed_results
                                       )
        return results

    def insert(
            self,
            data: BulkDataAny,
            batch_size: int = 10000,
            use_serial: bool = False,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Any]:
        """ insert records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = self._bulk_operation(use_serial=use_serial,
                                       operation='insert',
                                       data=data,
                                       batch_size=batch_size,
                                       bypass_results=bypass_results,
                                       include_detailed_results=include_detailed_results
                                       )
        return results

    def upsert(
            self,
            data: BulkDataAny,
            external_id_field: str,
            batch_size: int = 10000,
            use_serial: bool = False,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Any]:
        """ upsert records based on a unique identifier

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = self._bulk_operation(use_serial=use_serial,
                                       operation='upsert',
                                       external_id_field=external_id_field,
                                       data=data,
                                       batch_size=batch_size,
                                       bypass_results=bypass_results,
                                       include_detailed_results=include_detailed_results
                                       )
        return results

    def update(
            self,
            data: BulkDataAny,
            batch_size: int = 10000,
            use_serial: bool = False,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Any]:
        """ update records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = self._bulk_operation(use_serial=use_serial,
                                       operation='update',
                                       data=data,
                                       batch_size=batch_size,
                                       bypass_results=bypass_results,
                                       include_detailed_results=include_detailed_results
                                       )
        return results

    def hard_delete(
            self,
            data: BulkDataStr,
            batch_size: int = 10000,
            use_serial: bool = False,
            bypass_results: bool = False,
            include_detailed_results: bool = False
            ) -> Iterable[Any]:
        """ hard delete records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = self._bulk_operation(use_serial=use_serial,
                                       operation='hardDelete',
                                       data=data,
                                       batch_size=batch_size,
                                       bypass_results=bypass_results,
                                       include_detailed_results=include_detailed_results
                                       )
        return results

    def query(
            self,
            data: BulkDataStr,
            lazy_operation: bool = False,
            wait: int = 5
            ) -> Iterable[Any]:
        """ bulk query """
        results = self._bulk_operation(operation='query',
                                       data=data,
                                       wait=wait
                                       )

        if lazy_operation:
            return results

        return list_from_generator(results)

    def query_all(
            self,
            data: BulkDataStr,
            lazy_operation: bool = False,
            wait: int = 5
            ) -> Iterable[Any]:
        """ bulk queryAll """
        results = self._bulk_operation(operation='queryAll',
                                       data=data,
                                       wait=wait
                                       )

        if lazy_operation:
            return results
        return list_from_generator(results)

    def submit_dml(
                self,
                function_name: str,
                data: BulkDataAny,
                external_id_field: str = None,
                batch_size: int = 10000,
                use_serial: bool = False,
                bypass_results: bool = False,
                include_detailed_results: bool = False
                ):
        """ modular bulk dml operations -
            perform insert/upsert/update/delete
            on any standard and custom objects in Salesforce."""
        if function_name == 'upsert' and external_id_field is not None:
            return getattr(self, function_name)(data,
                                                external_id_field,
                                                batch_size,
                                                use_serial,
                                                bypass_results,
                                                include_detailed_results,
                                                )
        else:
            return getattr(self, function_name)(data,
                                                batch_size,
                                                use_serial,
                                                bypass_results,
                                                include_detailed_results)
