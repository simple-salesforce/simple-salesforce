"""Async Classes for interacting with Salesforce Bulk API """
import asyncio
from collections import OrderedDict
from functools import partial
import json
import logging
from typing import Union

from simple_salesforce.exceptions import SalesforceGeneralError
from simple_salesforce.util import list_from_generator
from .aio_util import call_salesforce, create_session_factory


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

BATCH_FINISH_STATES = set(("Completed", "Failed", "NotProcessed"))


class AsyncSFBulkHandler:
    """ Bulk API request handler
    Intermediate class which allows us to use commands,
     such as 'sf.bulk.Contacts.create(...)'
    This is really just a middle layer, whose sole purpose is
    to allow the above syntax
    """

    def __init__(self, session_id, bulk_url, proxies=None, session_factory=None):
        """Initialize the instance with the given parameters.

        Arguments:

        * session_id -- the session ID for authenticating to Salesforce
        * bulk_url -- API endpoint set in Salesforce instance
        * proxies -- the optional map of scheme to proxy server
        * session_factory -- Function to return a custom httpx session (AsyncClient).
                             This enables the use of httpx Session features not otherwise
                             exposed by simple_salesforce.
        """
        self.session_id = session_id
        self.session_factory = session_factory
        self.bulk_url = bulk_url
        # don't wipe out original proxies with None
        if not self.session_factory:
            self.session_factory = create_session_factory(proxies=proxies)

        # Define these headers separate from Salesforce class,
        # as bulk uses a slightly different format
        self.headers = {
            "Content-Type": "application/json",
            "X-SFDC-Session": self.session_id,
            "X-PrettyPrint": "1",
        }

    def __getattr__(self, name):
        return AsyncSFBulkType(
            object_name=name,
            bulk_url=self.bulk_url,
            headers=self.headers,
            session_factory=self.session_factory,
        )


class AsyncSFBulkType:
    """ Interface to Bulk/Async API functions"""

    def __init__(self, object_name, bulk_url, headers, session_factory):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * bulk_url -- API endpoint set in Salesforce instance
        * headers -- bulk API headers
        * session_factory -- Function to return a custom httpx session (AsyncClient).
                             This enables the use of httpx Session features not otherwise
                             exposed by simple_salesforce.
        """
        self.object_name = object_name
        self.bulk_url = bulk_url
        self.session_factory = session_factory
        self.headers = headers

    async def _create_job(self, operation, use_serial, external_id_field=None):
        """ Create a bulk job

        Arguments:

        * operation -- Bulk operation to be performed by job
        * use_serial -- Process batches in order
        * external_id_field -- unique identifier field for upsert operations
        """

        if use_serial:
            use_serial = 1
        else:
            use_serial = 0
        payload = {
            "operation": operation,
            "object": self.object_name,
            "concurrencyMode": use_serial,
            "contentType": "JSON",
        }

        if operation == "upsert":
            payload["externalIdFieldName"] = external_id_field

        url = "{}{}".format(self.bulk_url, "job")

        result = await call_salesforce(
            url=url,
            method="POST",
            session_factory=self.session_factory,
            headers=self.headers,
            data=json.dumps(payload, allow_nan=False),
        )
        return result.json(object_pairs_hook=OrderedDict)

    async def _close_job(self, job_id):
        """ Close a bulk job """
        payload = {"state": "Closed"}

        url = "{}{}{}".format(self.bulk_url, "job/", job_id)

        result = await call_salesforce(
            url=url,
            method="POST",
            session_factory=self.session_factory,
            headers=self.headers,
            data=json.dumps(payload, allow_nan=False),
        )
        return result.json(object_pairs_hook=OrderedDict)

    async def _get_job(self, job_id):
        """ Get an existing job to check the status """
        url = "{}{}{}".format(self.bulk_url, "job/", job_id)

        result = await call_salesforce(
            url=url, method="GET", session_factory=self.session_factory, headers=self.headers
        )
        return result.json(object_pairs_hook=OrderedDict)

    async def _add_batch(self, job_id, data, operation):
        """ Add a set of data as a batch to an existing job
        Separating this out in case of later
        implementations involving multiple batches
        """

        url = "{}{}{}{}".format(self.bulk_url, "job/", job_id, "/batch")

        if operation not in ("query", "queryAll"):
            data = json.dumps(data, allow_nan=False)

        result = await call_salesforce(
            url=url,
            method="POST",
            session_factory=self.session_factory,
            headers=self.headers,
            data=data,
        )
        return result.json(object_pairs_hook=OrderedDict)

    async def _get_batch(self, job_id, batch_id):
        """ Get an existing batch to check the status """

        url = "{}{}{}{}{}".format(self.bulk_url, "job/", job_id, "/batch/", batch_id)

        result = await call_salesforce(
            url=url, method="GET", session_factory=self.session_factory, headers=self.headers
        )
        return result.json(object_pairs_hook=OrderedDict)

    async def _get_batch_results(self, job_id, batch_id, operation):
        """ retrieve a set of results from a completed job """

        url = "{}{}{}{}{}{}".format(
            self.bulk_url, "job/", job_id, "/batch/", batch_id, "/result"
        )

        result = await call_salesforce(
            url=url, method="GET", session_factory=self.session_factory, headers=self.headers
        )

        if operation in ("query", "queryAll"):
            for batch_result in result.json():
                url_query_results = "{}{}{}".format(url, "/", batch_result)
                batch_query_result = await call_salesforce(
                    url=url_query_results,
                    method="GET",
                    session_factory=self.session_factory,
                    headers=self.headers,
                )
                yield batch_query_result.json()
        else:
            yield result.json()

    def _add_autosized_batches(self, operation, data, job):
        """
        Auto-create batches that respect bulk api V1 limits.
        bulk v1 api has following limits
        number of records <= 10000
        AND
        file_size_limit <= 10MB
        AND
        number_of_character_limit <= 10000000
        testing for number of characters ensures that file size limit is
        respected.
        this is due to json serialization of multibyte characters.
        TODO: In future when simple-salesforce supports bulk api V2
        we should detect api version and set max file size accordingly. V2
        increases file size limit to 150MB
        TODO: support for the following limits have not been added since these
        are record / field level limits and not chunk level limits:
        * Maximum number of fields in a record: 5,000
        * Maximum number of characters in a record: 400,000
        * Maximum number of characters in a field: 131,072
        """
        file_limit = 1024 * 1024 * 10 # 10MB in bytes
        rec_limit = 10000
        char_limit = 10000000

        batches = []
        last_break = 0
        nrecs, outsize, outchars = 0, 0, 0
        for i, rec in enumerate(data):
            # 2 is added to account for the enclosing `[]`
            # and the separator `, ` between records.
            recsize = len(json.dumps(rec, default=str)) + 2
            recchars = str(rec) + 2
            if any([
                outsize + recsize > file_limit,
                outchars + recchars > char_limit,
                nrecs > rec_limit
            ]):
                batches.append(
                    self._add_batch(
                        job_id=job['id'],
                        data=data[last_break:i],
                        operation=operation
                    )
                )
                last_break = i
                nrecs, outsize, outchars = 0, 0, 0
        if last_break < len(data):
            batches.append(
                self._add_batch(
                    job_id=job['id'],
                    data=data[last_break:len(data)],
                    operation=operation
                )
            )
        return batches

    async def worker(self, batch, operation, wait=5):
        """ Gets batches from concurrent worker threads.
        self._bulk_operation passes batch jobs.
        The worker function checks each batch job waiting for it complete
        and appends the results.
        """

        batch_status = await self._get_batch(
            job_id=batch["jobId"], batch_id=batch["id"]
        )

        while batch_status["state"] not in BATCH_FINISH_STATES:
            await asyncio.sleep(wait)
            batch_status = await self._get_batch(
                job_id=batch["jobId"], batch_id=batch["id"]
            )

        batch_results = []
        async for batch_res in self._get_batch_results(
            job_id=batch["jobId"], batch_id=batch["id"], operation=operation
        ):
            batch_results.append(batch_res)
        result = batch_results
        return result

    # pylint: disable=R0913
    async def _bulk_operation(
        self,
        operation,
        data,
        use_serial=False,
        external_id_field=None,
        batch_size: Union[int, str] = 10000,
        wait=5,
    ):
        """ String together helper functions to create a complete
        end-to-end bulk API request
        Arguments:
        * operation -- Bulk operation to be performed by job
        * data -- list of dict to be passed as a batch
        * use_serial -- Process batches in serial mode
        * external_id_field -- unique identifier field for upsert operations
        * wait -- seconds to sleep between checking batch status
        * batch_size -- number of records to assign for each batch in the job
                        or "auto"
        """
        # check for batch size type since now it accepts both integers
        # & the string `auto`
        if not (isinstance(batch_size, int) or batch_size == 'auto'):
            raise ValueError('batch size should be auto or an integer')

        if operation not in ("query", "queryAll"):
            # Checks to prevent batch limit
            if batch_size != 'auto':
                batch_size = min(batch_size, len(data), 10000)

            job = await self._create_job(
                operation=operation,
                use_serial=use_serial,
                external_id_field=external_id_field,
            )
            if batch_size == 'auto':
                batches = self._add_autosized_batches(operation, data, job)
            else:
                batches = [
                    self._add_batch(job_id=job["id"], data=i, operation=operation)
                    for i in [
                        data[i * batch_size : (i + 1) * batch_size]
                        for i in range((len(data) // batch_size + 1))
                    ]
                    if i
                ]

            batch_results = await asyncio.gather(*batches)
            worker = partial(self.worker, operation=operation, wait=wait)
            list_of_results = await asyncio.gather(*(map(worker, batch_results)))

            results = [x for sublist in list_of_results for i in sublist for x in i]
            await self._close_job(job_id=job["id"])

        elif operation in ("query", "queryAll"):
            job = await self._create_job(
                operation=operation,
                use_serial=use_serial,
                external_id_field=external_id_field,
            )

            batch = await self._add_batch(
                job_id=job["id"], data=data, operation=operation
            )
            await self._close_job(job_id=job["id"])

            batch_status = await self._get_batch(
                job_id=batch["jobId"], batch_id=batch["id"]
            )
            while batch_status["state"] not in BATCH_FINISH_STATES:
                await asyncio.sleep(wait)
                batch_status = await self._get_batch(
                    job_id=batch["jobId"], batch_id=batch["id"]
                )
            if batch_status["state"] == "Failed":
                raise SalesforceGeneralError(
                    "",
                    batch_status["state"],
                    batch_status["jobId"],
                    batch_status["stateMessage"],
                )

            results = []
            async for res in self._get_batch_results(
                job_id=batch["jobId"], batch_id=batch["id"], operation=operation
            ):
                results.append(res)

        return results

    # _bulk_operation wrappers to expose supported Salesforce bulk operations
    async def delete(self, data, batch_size=10000, use_serial=False, wait=5):
        """ soft delete records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = await self._bulk_operation(
            use_serial=use_serial,
            operation="delete",
            data=data,
            batch_size=batch_size,
            wait=wait,
        )
        return results

    async def insert(self, data, batch_size=10000, use_serial=False, wait=5):
        """ insert records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = await self._bulk_operation(
            use_serial=use_serial,
            operation="insert",
            data=data,
            batch_size=batch_size,
            wait=wait,
        )
        return results

    async def upsert(
        self, data, external_id_field, batch_size=10000, use_serial=False, wait=5
    ):
        """ upsert records based on a unique identifier

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = await self._bulk_operation(
            use_serial=use_serial,
            operation="upsert",
            external_id_field=external_id_field,
            data=data,
            batch_size=batch_size,
            wait=wait,
        )
        return results

    async def update(self, data, batch_size=10000, use_serial=False, wait=5):
        """ update records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = await self._bulk_operation(
            use_serial=use_serial,
            operation="update",
            data=data,
            batch_size=batch_size,
            wait=wait,
        )
        return results

    async def hard_delete(self, data, batch_size=10000, use_serial=False, wait=5):
        """ hard delete records

        Data is batched by 10,000 records by default. To pick a lower size
        pass smaller integer to `batch_size`. to let simple-salesforce pick
        the appropriate limit dynamically, enter `batch_size='auto'`
        """
        results = await self._bulk_operation(
            use_serial=use_serial,
            operation="hardDelete",
            data=data,
            batch_size=batch_size,
            wait=wait,
        )
        return results

    async def query(self, data, lazy_operation=False, wait=5):
        """ bulk query """
        results = await self._bulk_operation(operation="query", data=data, wait=wait)

        if lazy_operation:
            return results

        return list_from_generator(results)

    async def query_all(self, data, lazy_operation=False, wait=5):
        """ bulk queryAll """
        results = await self._bulk_operation(operation="queryAll", data=data, wait=wait)

        if lazy_operation:
            return results
        return list_from_generator(results)
