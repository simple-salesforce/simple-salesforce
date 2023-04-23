""" Classes for interacting with Salesforce Bulk 2.0 API """

import copy
import http.client as http
import json
import os
import re
import sys
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from time import sleep
from typing import Dict, Tuple, Union, Generator

import requests

from .exceptions import (
    SalesforceBulkV2ExtractError,
    SalesforceBulkV2LoadError,
)
from .util import call_salesforce


# pylint: disable=missing-class-docstring
class Operation:
    insert = "insert"
    upsert = "upsert"
    update = "update"
    delete = "delete"
    hard_delete = "hardDelete"
    query = "query"
    query_all = "queryAll"


# pylint: disable=missing-class-docstring
class JobState:
    open = "Open"
    aborted = "Aborted"
    failed = "Failed"
    upload_complete = "UploadComplete"
    in_progress = "InProgress"
    job_complete = "JobComplete"


# pylint: disable=missing-class-docstring
class ColumnDelimiter:
    BACKQUOTE = "BACKQUOTE"  # (`)
    CARET = "CARET"  # (^)
    COMMA = "COMMA"  # (,)
    PIPE = "PIPE"  # (|)
    SEMICOLON = "SEMICOLON"  # (;)
    TAB = "TAB"  # (\t)


_delimiter_char = {
    ColumnDelimiter.BACKQUOTE: "`",
    ColumnDelimiter.CARET: "^",
    ColumnDelimiter.COMMA: ",",
    ColumnDelimiter.PIPE: "|",
    ColumnDelimiter.SEMICOLON: ";",
    ColumnDelimiter.TAB: "\t",
}


# pylint: disable=missing-class-docstring
class LineEnding:
    LF = "LF"  # pylint: disable=invalid-name
    CRLF = "CRLF"


_line_ending_char = {LineEnding.LF: "\n", LineEnding.CRLF: "\r\n"}


class ResultsType:
    failed = "failedResults"
    successful = "successfulResults"
    unprocessed = "unprocessedRecords"


# https://developer.salesforce.com/docs/atlas.en-us.242.0.salesforce_app_limits_cheatsheet.meta/salesforce_app_limits_cheatsheet/salesforce_app_limits_platform_bulkapi.htm
# https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/datafiles_prepare_csv.htm
MAX_INGEST_FILE_SIZE = 100 * 1024 * 1024
MAX_INGEST_SIZE = 10000
MAX_INGEST_BYTES = 10_000_000
MAX_EXTRACT_SIZE = 50000


def _split_csv(filename, max_records=MAX_INGEST_SIZE):
    """Split a CSV file into chunks to avoid exceeding the Salesforce
    bulk 2.0 API limits.
    """
    max_bytes = MAX_INGEST_BYTES
    records_size = 0
    bytes_size = 0
    buff = []
    with open(filename, encoding="utf-8") as bis:
        header = bis.readline()
        max_bytes -= sys.getsizeof(header)
        max_records -= 1
        for line in bis:
            records_size += 1
            bytes_size += sys.getsizeof(line)
            if records_size > max_records or bytes_size > max_bytes:
                if buff:
                    yield records_size - 1, header + "".join(buff)
                buff = [line]
                records_size = 1
                bytes_size = sys.getsizeof(line)
            else:
                buff.append(line)
        if buff:
            yield records_size, header + "".join(buff)


def _count_csv(
    filename=None, data=None, skip_header=False, line_ending=LineEnding.LF
):
    """Count the number of records in a CSV file."""
    if filename:
        with open(filename, encoding="utf-8") as bis:
            count = sum(1 for _ in bis)
    elif data:
        pat = repr(_line_ending_char[line_ending])[1:-1]
        count = sum(1 for _ in re.finditer(pat, data))
    else:
        raise ValueError("Either filename or data must be provided")

    if skip_header:
        count -= 1
    return count


class SFBulk2Handler:
    """Bulk 2.0 API request handler
    Intermediate class which allows us to use commands,
     such as 'sf.bulk2.Contacts.insert(...)'
    This is really just a middle layer, whose sole purpose is
    to allow the above syntax
    """

    def __init__(self, session_id, bulk2_url, proxies=None, session=None):
        """Initialize the instance with the given parameters.

        Arguments:

        * session_id -- the session ID for authenticating to Salesforce
        * bulk2_url -- 2.0 API endpoint set in Salesforce instance
        * proxies -- the optional map of scheme to proxy server
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.session_id = session_id
        self.session = session or requests.Session()
        self.bulk2_url = bulk2_url
        # don't wipe out original proxies with None
        if not session and proxies is not None:
            self.session.proxies = proxies

        # Define these headers separate from Salesforce class,
        # as bulk uses a slightly different format
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.session_id,
            "X-PrettyPrint": "1",
        }

    def __getattr__(self, name):
        return SFBulk2Type(
            object_name=name,
            bulk2_url=self.bulk2_url,
            headers=self.headers,
            session=self.session,
        )


class _Bulk2Client:
    """Bulk 2.0 API client"""

    JSON_CONTENT_TYPE = "application/json"
    CSV_CONTENT_TYPE = "text/csv"

    def __init__(self, object_name, bulk2_url, headers, session):
        """
        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * bulk2_url -- 2.0 API endpoint set in Salesforce instance
        * headers -- bulk 2.0 API headers
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.object_name = object_name
        self.bulk2_url = bulk2_url
        self.session = session
        self.headers = headers

    def _get_headers(self, request_content_type=None, accept_content_type=None):
        """Get headers for bulk 2.0 API request"""
        headers = copy.deepcopy(self.headers)
        headers["Content-Type"] = request_content_type or self.JSON_CONTENT_TYPE
        headers["ACCEPT"] = accept_content_type or self.JSON_CONTENT_TYPE
        return headers

    def _construct_request_url(self, job_id, is_query: bool):
        """Construct bulk 2.0 API request URL"""
        if not job_id:
            job_id = ""
        if is_query:
            url = self.bulk2_url + "query"
        else:
            url = self.bulk2_url + "ingest"
        if job_id:
            url = f"{url}/{job_id}"
        return url

    def create_job(
        self,
        operation,
        query=None,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        external_id_field=None,
    ):
        """Create job

        Arguments:

        * operation -- Bulk operation to be performed by job
        * query -- SOQL query to be performed by job
        * column_delimiter -- The column delimiter used for CSV job data
        * line_ending -- The line ending used for CSV job data
        * external_id_field -- The external ID field in the object being updated
        """
        payload = {
            "operation": operation,
            "columnDelimiter": column_delimiter,
            "lineEnding": line_ending,
        }
        if external_id_field:
            payload["externalIdFieldName"] = external_id_field

        is_query = operation in (Operation.query, Operation.query_all)
        url = self._construct_request_url(None, is_query)
        if is_query:
            headers = self._get_headers(
                self.JSON_CONTENT_TYPE, self.CSV_CONTENT_TYPE
            )
            if not query:
                raise SalesforceBulkV2ExtractError(
                    "Query is required for query jobs"
                )
            payload["query"] = query
        else:
            headers = self._get_headers(
                self.JSON_CONTENT_TYPE, self.JSON_CONTENT_TYPE
            )
            payload["object"] = self.object_name
            payload["contentType"] = "CSV"
        result = call_salesforce(
            url=url,
            method="POST",
            session=self.session,
            headers=headers,
            data=json.dumps(payload, allow_nan=False),
        )
        return result.json(object_pairs_hook=OrderedDict)

    def abort_job(self, job_id, is_query: bool):
        """Abort query/ingest job"""
        return self._set_job_state(job_id, is_query, JobState.aborted)

    def close_job(self, job_id):
        """Close ingest job"""
        return self._set_job_state(job_id, False, JobState.upload_complete)

    def delete_job(self, job_id, is_query: bool):
        """Delete query/ingest job"""
        url = self._construct_request_url(job_id, is_query)
        headers = self._get_headers()
        result = call_salesforce(
            url=url, method="DELETE", session=self.session, headers=headers
        )
        return result.json(object_pairs_hook=OrderedDict)

    def _set_job_state(self, job_id, is_query: bool, state: str):
        """Set job state"""
        url = self._construct_request_url(job_id, is_query)
        headers = self._get_headers()
        payload = {"state": state}
        result = call_salesforce(
            url=url,
            method="PATCH",
            session=self.session,
            headers=headers,
            data=json.dumps(payload, allow_nan=False),
        )
        return result.json(object_pairs_hook=OrderedDict)

    def get_job(self, job_id, is_query: bool):
        """Get job info"""
        url = self._construct_request_url(job_id, is_query)

        result = call_salesforce(
            url=url, method="GET", session=self.session, headers=self.headers
        )
        return result.json(object_pairs_hook=OrderedDict)

    def get_query_results(self, job_id, locator: str = "", max_records=10000):
        """Get results for a query job"""
        url = self._construct_request_url(job_id, True) + "/results"
        url += "?maxRecords=" + str(max_records)
        if locator and locator != "null":
            url += "&locator=" + locator

        headers = self._get_headers(
            self.JSON_CONTENT_TYPE, self.CSV_CONTENT_TYPE
        )
        result = call_salesforce(
            url=url, method="GET", session=self.session, headers=headers
        )
        locator = result.headers.get("Sforce-Locator", "")
        if locator == "null":
            locator = ""
        number_of_records = int(result.headers.get("Sforce-NumberOfRecords"))
        return {
            "locator": locator,
            "number_of_records": number_of_records,
            "records": result.text,
        }

    def upload_job_data(self, job_id, data: str, content_url=None):
        """Upload job data"""
        if not data:
            raise SalesforceBulkV2LoadError("Data is required for ingest jobs")

        if sys.getsizeof(data) > MAX_INGEST_FILE_SIZE:
            raise SalesforceBulkV2LoadError(
                "Data size exceeds the max file size accepted by "
                "Bulk V2 (100 MB)"
            )

        url = (
            content_url
            or self._construct_request_url(job_id, False) + "/batches"
        )
        headers = self._get_headers(
            self.CSV_CONTENT_TYPE, self.JSON_CONTENT_TYPE
        )
        result = call_salesforce(
            url=url,
            method="PUT",
            session=self.session,
            headers=headers,
            data=data,
        )
        if result.status_code != http.CREATED:
            raise SalesforceBulkV2LoadError(
                f"Failed to upload job data. Error Code {result.status_code}. "
                f"Response content: {result.content}"
            )

    def get_ingest_results(self, job_id, results_type):
        """Get record results"""
        url = self._construct_request_url(job_id, False) + "/" + results_type
        headers = self._get_headers(
            self.JSON_CONTENT_TYPE, self.CSV_CONTENT_TYPE
        )
        result = call_salesforce(
            url=url, method="GET", session=self.session, headers=headers
        )
        return result.text


class SFBulk2Type:
    """Interface to Bulk 2.0 API functions"""

    def __init__(self, object_name, bulk2_url, headers, session):
        """Initialize the instance with the given parameters.

        Arguments:

        * object_name -- the name of the type of SObject this represents,
                         e.g. `Lead` or `Contact`
        * bulk2_url -- API endpoint set in Salesforce instance
        * headers -- bulk API headers
        * session -- Custom requests session, created in calling code. This
                     enables the use of requests Session features not otherwise
                     exposed by simple_salesforce.
        """
        self.object_name = object_name
        self.bulk2_url = bulk2_url
        self.session = session
        self.headers = headers
        self._client = _Bulk2Client(object_name, bulk2_url, headers, session)

    # pylint: disable=too-many-arguments
    def _upload_data(
        self,
        operation,
        data: Union[str, Tuple[int, str]],
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        external_id_field=None,
        wait=5,
    ) -> Dict:
        """Upload data to Salesforce"""
        if len(data) == 2:
            total, data = data
        else:
            total = _count_csv(
                data=data, line_ending=line_ending, skip_header=True
            )
        res = self._client.create_job(
            operation,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            external_id_field=external_id_field,
        )
        job_id = res["id"]
        try:
            if res["state"] == JobState.open:
                self._client.upload_job_data(job_id, data)
                res = self._client.close_job(job_id)
                while res["state"] != JobState.job_complete:
                    if res["state"] == JobState.failed:
                        raise SalesforceBulkV2LoadError(
                            f"Failed to upload job data. Response content: "
                            f"{res.get('errorMessage')}"
                        )
                    sleep(wait)
                    res = self._client.get_job(job_id, False)
                return {
                    "numberRecordsFailed": int(res["numberRecordsFailed"]),
                    "numberRecordsProcessed": int(
                        res["numberRecordsProcessed"]
                    ),
                    "numberRecordsTotal": int(total),
                    "job_id": job_id,
                }
            raise SalesforceBulkV2LoadError(
                f"Failed to upload job data. Response content: "
                f"{res.content}"
            )
        except Exception:
            if res["state"] in (
                JobState.upload_complete,
                JobState.in_progress,
                JobState.open,
            ):
                self._client.abort_job(job_id, False)
            raise

    # pylint: disable=too-many-arguments,too-many-locals
    def _upload_file(
        self,
        operation,
        csv_file,
        batch_size=MAX_INGEST_SIZE,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        external_id_field=None,
        concurrency=1,
        wait=5,
    ) -> Dict:
        """Upload csv file to Salesforce"""
        if not os.path.exists(csv_file):
            raise SalesforceBulkV2LoadError(csv_file + " not found.")

        if operation in (Operation.delete, Operation.hard_delete):
            with open(csv_file, "r", encoding="utf-8") as bis:
                header = (
                    bis.readline()
                    .rstrip()
                    .split(_delimiter_char[column_delimiter])
                )
                if len(header) != 1:
                    raise SalesforceBulkV2LoadError(
                        f"InvalidBatch: The '{operation}' batch must contain "
                        f"only ids, {header}"
                    )

        results = []
        if concurrency == 1:
            for data in _split_csv(csv_file, max_records=batch_size):
                result = self._upload_data(
                    operation,
                    data,
                    column_delimiter,
                    line_ending,
                    external_id_field,
                    wait,
                )
                results.append(result)
        else:
            # OOM is possible if the file is too large
            chunks = list(_split_csv(csv_file, max_records=batch_size))
            concurrency = min(concurrency, len(chunks))
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                multi_thread_worker = partial(
                    self._upload_data,
                    operation,
                    column_delimiter=column_delimiter,
                    line_ending=line_ending,
                    external_id_field=external_id_field,
                    wait=wait,
                )
                results = pool.map(multi_thread_worker, chunks)
            results = list(results)

        job_id = results[0]["job_id"]
        total = processed = failed = 0
        for ret in results:
            failed += ret["numberRecordsFailed"]
            processed += ret["numberRecordsProcessed"]
            total += ret["numberRecordsTotal"]

        return {
            "numberRecordsFailed": failed,
            "numberRecordsProcessed": processed,
            "numberRecordsTotal": total,
            "job_id": job_id,
        }

    def delete(
        self,
        csv_file,
        batch_size=10000,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        external_id_field=None,
        wait=5,
    ) -> Dict:
        """soft delete records"""
        return self._upload_file(
            Operation.delete,
            csv_file,
            batch_size=batch_size,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            external_id_field=external_id_field,
            wait=wait,
        )

    def insert(
        self,
        csv_file,
        batch_size=10000,
        concurrency=1,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        wait=5,
    ) -> Dict:
        """insert records"""
        return self._upload_file(
            Operation.insert,
            csv_file,
            batch_size=batch_size,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            concurrency=concurrency,
            wait=wait,
        )

    def upsert(
        self,
        csv_file,
        external_id_field,
        batch_size=10000,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        wait=5,
    ) -> Dict:
        """upsert records based on a unique identifier"""
        return self._upload_file(
            Operation.upsert,
            csv_file,
            batch_size=batch_size,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            external_id_field=external_id_field,
            wait=wait,
        )

    def update(
        self,
        csv_file,
        batch_size=10000,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        wait=5,
    ) -> Dict:
        """update records"""
        return self._upload_file(
            Operation.update,
            csv_file,
            batch_size=batch_size,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            wait=wait,
        )

    def hard_delete(
        self,
        csv_file,
        batch_size=10000,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        wait=5,
    ) -> Dict:
        """hard delete records"""
        return self._upload_file(
            Operation.hard_delete,
            csv_file,
            batch_size=batch_size,
            column_delimiter=column_delimiter,
            line_ending=line_ending,
            wait=wait,
        )

    def query(
        self,
        query,
        max_records=MAX_EXTRACT_SIZE,
        column_delimiter=ColumnDelimiter.COMMA,
        line_ending=LineEnding.LF,
        wait=5,
    ) -> Generator[Dict, None, None]:
        """bulk 2.0 query

        Arguments:
        * query -- SOQL query
        * max_records -- max records to retrieve per batch, default 50000

        Returns:
        * locator  -- the locator for the next set of results
        * number_of_records -- the number of records in this set
        * records -- records in this set
        """
        res = self._client.create_job(
            Operation.query, query, column_delimiter, line_ending
        )
        job_id = res["id"]
        while res["state"] not in [
            JobState.job_complete,
            JobState.failed,
            JobState.aborted,
        ]:
            sleep(wait)
            res = self._client.get_job(job_id, True)

        locator = "INIT"
        while locator:
            if locator == "INIT":
                locator = ""
            result = self._client.get_query_results(
                job_id, locator, max_records
            )
            locator = result["locator"]
            yield result

    def get_failed_records(self, job_id):
        """Get failed record results

        Results Property:
            sf__Id:	[string] ID of the record
            sf__Error:	[Error]	Error code and message
            Fields from the original CSV request data:	various
        """
        return self._client.get_ingest_results(job_id, ResultsType.failed)

    def get_unprocessed_records(self, job_id):
        """Get unprocessed record results

        Results Property:
            Fields from the original CSV request data:	[various]
        """
        return self._client.get_ingest_results(job_id, ResultsType.unprocessed)

    def get_successful_records(self, job_id):
        """Get successful record results.

        Results Property:
            sf__Id:	[string] ID of the record
            sf__Created: [boolean] Indicates if the record was created
            Fields from the original CSV request data:	[various]
        """
        return self._client.get_ingest_results(job_id, ResultsType.successful)
