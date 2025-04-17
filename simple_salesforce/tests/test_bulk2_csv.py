import random
import string
import csv
import math

import pytest
from simple_salesforce.bulk2 import (
    _count_csv,
    _split_csv,
    ColumnDelimiter,
    LineEnding,
    _delimiter_char,
    _line_ending_char,
    _convert_dict_to_csv,
    MAX_INGEST_JOB_FILE_SIZE,
)

PART_SIZE = MAX_INGEST_JOB_FILE_SIZE - 1 * 1024 * 1024


@pytest.fixture
def simple_csv_data():
    return "id,name\n1,Alice\n2,Bob\n3,Charlie\n"


@pytest.fixture
def simple_csv_dict_data():
    return [
        {"id": "1", "name": "Alice"},
        {"id": "2", "name": "Bob"},
        {"id": "3", "name": "Charlie"},
    ]


def generate_large_csv_data(
        num_records,
        num_fields=10,
        field_length=10,
        include_special_chars=False,
        line_ending: LineEnding = LineEnding.LF,
        column_delimiter: ColumnDelimiter = ColumnDelimiter.COMMA,
        quoting: int = csv.QUOTE_MINIMAL,
):
    """
    Generate a large CSV data string.

    Parameters:
        num_records (int): The number of records to generate.
        num_fields (int): The number of fields per record (default is 5).
        field_length (int): The length of each field value (default is 10).
        include_special_chars (bool): If True, include special characters in field values (default is False).
        line_ending (LineEnding): The line ending character for the CSV (default is LineEnding.LF).
        column_delimiter (ColumnDelimiter): The column delimiter for the CSV (default is ColumnDelimiter.COMMA).
        quoting (int): The quoting style for the CSV (default is csv.QUOTE_MINIMAL).

    Returns:
        str: A CSV formatted string.

    """
    special_chars = ["\n", "\r", ",", ";", "|", "\t", "`", "^", '"']
    data = []
    fieldnames = [f"field{i}" for i in range(num_fields)]
    for _ in range(num_records):
        record = {}
        for fieldname in fieldnames:
            value = "".join(
                random.choices(string.ascii_letters + string.digits, k=field_length)
            )
            if (
                    include_special_chars and random.random() < 0.5
            ):  # Randomly decide to include special chars
                value += random.choice(special_chars)
            record[fieldname] = value
        data.append(record)
    return _convert_dict_to_csv(
        data, column_delimiter, line_ending, quoting, sort_keys=True
    )


def test_convert_dict_to_csv(simple_csv_dict_data, simple_csv_data):
    converted_csv = _convert_dict_to_csv(data=simple_csv_dict_data, sort_keys=True)
    # Assert the converted CSV matches the expected CSV data
    assert converted_csv == simple_csv_data


# Tests for count_csv
@pytest.mark.parametrize("quoting", [csv.QUOTE_ALL, csv.QUOTE_MINIMAL, csv.QUOTE_NONE])
@pytest.mark.parametrize("line_ending", [LineEnding.LF, LineEnding.CRLF])
@pytest.mark.parametrize(
    "column_delimiter",
    [
        ColumnDelimiter.BACKQUOTE,
        ColumnDelimiter.CARET,
        ColumnDelimiter.COMMA,
        ColumnDelimiter.PIPE,
        ColumnDelimiter.SEMICOLON,
        ColumnDelimiter.TAB,
    ],
)
def test_count_csv(simple_csv_data, quoting, line_ending, column_delimiter):
    # Convert the simple_csv_data to the desired format based on parameters
    converted_data = simple_csv_data.replace(
        ",", _delimiter_char[column_delimiter]
    ).replace("\n", _line_ending_char[line_ending])
    record_count = _count_csv(
        data=converted_data,
        quoting=quoting,
        line_ending=line_ending,
        column_delimiter=column_delimiter,
        skip_header=True,
    )
    assert record_count == 3


# Tests for split_csv
@pytest.mark.parametrize("quoting", [csv.QUOTE_ALL, csv.QUOTE_MINIMAL, csv.QUOTE_NONE])
@pytest.mark.parametrize("line_ending", [LineEnding.LF, LineEnding.CRLF])
@pytest.mark.parametrize(
    "column_delimiter",
    [
        ColumnDelimiter.BACKQUOTE,
        ColumnDelimiter.CARET,
        ColumnDelimiter.COMMA,
        ColumnDelimiter.PIPE,
        ColumnDelimiter.SEMICOLON,
        ColumnDelimiter.TAB,
    ],
)
def test_split_csv(
        simple_csv_data, simple_csv_dict_data, quoting, line_ending, column_delimiter
):
    # Convert the simple_csv_data to the desired format based on parameters
    converted_data = simple_csv_data.replace(
        ",", _delimiter_char[column_delimiter]
    ).replace("\n", _line_ending_char[line_ending])
    split_results = list(
        _split_csv(
            records=converted_data,
            quoting=quoting,
            line_ending=line_ending,
            column_delimiter=column_delimiter,
        )
    )
    assert (
            len(split_results) == 1
    )  # Assuming the file is small and does not split into multiple chunks
    assert (
            sum(count for count, _ in split_results) == 3
    )  # Total record count should be 3

    # Split the data into chunks of max_records 1
    split_results = list(
        _split_csv(
            records=converted_data,
            max_records=1,
            quoting=quoting,
            line_ending=line_ending,
            column_delimiter=column_delimiter,
        )
    )
    assert len(split_results) == 3
    assert list([(count, data) for count, data in split_results]) == [
        (
            1,
            _convert_dict_to_csv(
                data=[record],
                line_ending=line_ending,
                column_delimiter=column_delimiter,
                quoting=quoting,
                sort_keys=True,
            ),
        )
        for record in simple_csv_dict_data
    ]


@pytest.mark.skip("High resources usage, test locally")
@pytest.mark.parametrize("quoting", [csv.QUOTE_ALL])
@pytest.mark.parametrize("line_ending", [LineEnding.LF])
@pytest.mark.parametrize(
    "column_delimiter",
    [
        ColumnDelimiter.BACKQUOTE,
        ColumnDelimiter.CARET,
        ColumnDelimiter.COMMA,
        ColumnDelimiter.PIPE,
        ColumnDelimiter.SEMICOLON,
        ColumnDelimiter.TAB,
    ],
)
@pytest.mark.parametrize("num_records", [500000, 1000000])
@pytest.mark.parametrize("num_fields", [10])
@pytest.mark.parametrize("field_length", [20])
@pytest.mark.parametrize("include_special_chars", [True])
def test_count_csv_large_data(
        quoting,
        line_ending,
        column_delimiter,
        num_records,
        num_fields,
        field_length,
        include_special_chars,
):
    large_csv_data = generate_large_csv_data(
        num_records,
        num_fields,
        field_length,
        include_special_chars,
        column_delimiter=column_delimiter,
        line_ending=line_ending,
        quoting=quoting,
    )
    record_count = _count_csv(
        data=large_csv_data,
        quoting=quoting,
        line_ending=line_ending,
        column_delimiter=column_delimiter,
        skip_header=True,
    )
    assert record_count == num_records  # We generated 100 records


@pytest.mark.skip("High resources usage, test locally")
@pytest.mark.parametrize("quoting", [csv.QUOTE_ALL])
@pytest.mark.parametrize("line_ending", [LineEnding.LF])
@pytest.mark.parametrize(
    "column_delimiter",
    [
        ColumnDelimiter.BACKQUOTE,
        ColumnDelimiter.CARET,
        ColumnDelimiter.COMMA,
        ColumnDelimiter.PIPE,
        ColumnDelimiter.SEMICOLON,
        ColumnDelimiter.TAB,
    ],
)
@pytest.mark.parametrize("num_records", [500000, 1000000])
@pytest.mark.parametrize("num_fields", [10])
@pytest.mark.parametrize("field_length", [20])
@pytest.mark.parametrize("include_special_chars", [True])
def test_split_csv_large_data(
        quoting,
        line_ending,
        column_delimiter,
        num_records,
        num_fields,
        field_length,
        include_special_chars,
):
    large_csv_data = generate_large_csv_data(
        num_records,
        num_fields,
        field_length,
        include_special_chars,
        column_delimiter=column_delimiter,
        line_ending=line_ending,
        quoting=quoting,
    )
    large_csv_data_size = len(large_csv_data.encode("utf8"))
    split_results = list(
        _split_csv(
            records=large_csv_data,
            quoting=quoting,
            line_ending=line_ending,
            column_delimiter=column_delimiter,
        )
    )
    record_count = _count_csv(
        data=large_csv_data,
        quoting=quoting,
        line_ending=line_ending,
        column_delimiter=column_delimiter,
        skip_header=True,
    )
    assert sum(count for count, _ in split_results) == record_count
    assert len(split_results) == math.ceil(large_csv_data_size / PART_SIZE)
