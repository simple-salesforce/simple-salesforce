"""Simple-Salesforce Package Setup"""

from setuptools import setup
import textwrap
import sys

extra_install_requires = []
extra_tests_require = []
if sys.version_info < (2, 7):
    extra_install_requires.append('ordereddict>=1.1')
    extra_tests_require.append('unittest2>=0.5.1')

if sys.version_info < (3, 0):
    extra_tests_require.append('mock==1.0.1')

setup(
    name='simple-salesforce',
    version='0.61',
    author='Nick Catalano',
    packages=['simple_salesforce',],
    url='https://github.com/neworganizing/simple-salesforce',
    license='APACHE',
    description=("Simple Salesforce is a basic Salesforce.com REST API client. "
        "The goal is to provide a very low-level interface to the API, "
        "returning a dictionary of the API JSON response."),
    long_description=textwrap.dedent(open('README.rst', 'r').read()),
    install_requires=[
        'requests'
    ] + extra_install_requires,
    tests_require=[
        'nose==1.3.0'
    ] + extra_tests_require,
    test_suite = 'nose.collector',
    keywords = "python salesforce salesforce.com",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP'
    ]
)
