from setuptools import setup

setup(
    name='simple-salesforce',
    version='0.1',
    author='Nick Catalano',
    packages=['simple_salesforce',],
    url='https://github.com/neworganizing/simple-salesforce',
    license='APACHE',
    long_description=open('README.rst').read(),
    install_requires=[
        'requests',
    ],
    keywords = "python salesforce salesforce.com",
    classifiers=['Development Status :: 4 - Beta', 'Environment :: Console', 'Intended Audience :: Developers', 'Natural Language :: English', 'Operating System :: OS Independent', 'Topic :: Internet :: WWW/HTTP'],
)