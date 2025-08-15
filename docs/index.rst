.. simple-salesforce documentation master file, created by
   sphinx-quickstart on Tue Nov 22 19:18:40 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to simple-salesforce's documentation!
=============================================

Simple Salesforce is a basic Salesforce.com REST API client built for Python 3.9, 3.10, 3.11, 3.12, and 3.13. The goal is to provide a very low-level interface to the REST Resource and APEX API, returning a dictionary of the API JSON response.

You can find out more regarding the format of the results in the `Official Salesforce.com REST API Documentation`_

.. _Official Salesforce.com REST API Documentation: http://www.salesforce.com/us/developer/docs/api_rest/index.htm

Contents:

.. toctree::
   :maxdepth: 2

   user_guide/examples
   user_guide/record_management
   user_guide/queries
   user_guide/misc
   user_guide/apex
   user_guide/additional_features

API documentation
-----------------
.. toctree::
  :maxdepth: 3

  simple_salesforce

Release history
---------------
.. toctree::
  :maxdepth: 2

  changes


Authors & License
-----------------

This package is released under an open source Apache 2.0 license. Simple-Salesforce was originally written by `Nick Catalano`_ but most newer features and bugfixes come from `community contributors`_. Pull requests submitted to the `GitHub Repo`_ are highly encouraged!

Authentication mechanisms were adapted from Dave Wingate's `RestForce`_ and licensed under a MIT license

The latest build status can be found at `GitHub Actions`_

.. _Nick Catalano: https://github.com/nickcatal
.. _community contributors: https://github.com/simple-salesforce/simple-salesforce/graphs/contributors
.. _RestForce: http://pypi.python.org/pypi/RestForce/
.. _GitHub Repo: https://github.com/simple-salesforce/simple-salesforce
.. _GitHub Actions: https://github.com/simple-salesforce/simple-salesforce/actions


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

