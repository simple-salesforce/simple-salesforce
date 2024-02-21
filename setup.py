"""Simple-Salesforce Package Setup"""

import textwrap
from pathlib import Path

from setuptools import setup

here = Path(__file__).parent

about = {}
exec((here / 'simple_salesforce' / '__version__.py').read_text(), about)

setup(
    name=about['__title__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    maintainer=about['__maintainer__'],
    maintainer_email=about['__maintainer_email__'],
    packages=['simple_salesforce', ],
    url=about['__url__'],
    license=about['__license__'],
    description=about['__description__'],
    long_description=textwrap.dedent((here / 'README.rst').read_text()),
    long_description_content_type='text/x-rst',
    package_data={
        'simple_salesforce': ['metadata.wsdl', 'py.typed'],
        },
    install_requires = [
       'requests>=2.22.0',
       'typing-extensions',
       'zeep',
       'pyjwt[crypto]',
       'more-itertools'
       ],
    tests_require=[
        'pytest',
        'pytz>=2014.1.1',
        'responses>=0.5.1',
        ],
    test_suite='simple_salesforce.tests',
    keywords=about['__keywords__'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: PyPy'
        ],
    zip_safe=False,
)
