Development
-----------

Setting up for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~

To set up a development environment, clone the repository and install the development dependencies:

.. code-block:: bash

    git clone https://github.com/simple-salesforce/simple-salesforce.git
    cd simple-salesforce
    pip install -e .[dev]

This will install the package in editable mode along with all development dependencies including ``tox``, ``pytest``, ``pylint``, ``mypy``, and other testing/linting tools.

Running Tests
~~~~~~~~~~~~~

The project uses ``tox`` for testing across multiple Python versions. To run all tests:

.. code-block:: bash

    tox

To run tests for a specific Python version:

.. code-block:: bash

    tox -e py312-unit  # Run unit tests with Python 3.12

To run static analysis (linting and type checking):

.. code-block:: bash

    tox -e static

To run tests directly with pytest (after installing dev dependencies):

.. code-block:: bash

    pytest

Available tox environments:

* ``py{39,310,311,312,313}-unit`` - Run unit tests with different Python versions
* ``static`` - Run pylint and mypy for code quality checks
* ``docs`` - Build documentation
* ``clean`` - Clean up coverage files

Contributing
~~~~~~~~~~~~

Pull requests are welcome! Please make sure to:

1. Run tests with ``tox`` to ensure compatibility across Python versions
2. Follow the existing code style (enforced by the static analysis tools)
3. Add tests for any new functionality
