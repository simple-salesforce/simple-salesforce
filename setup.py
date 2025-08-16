"""Simple-Salesforce Package Setup (minimal shim; canonical metadata in pyproject.toml)"""

from pathlib import Path
from setuptools import setup

here = Path(__file__).parent

about = {}
exec((here / "simple_salesforce" / "__version__.py").read_text(), about)

setup(
    name=about["__title__"],
    version=about["__version__"],
    packages=["simple_salesforce"],
    include_package_data=True,
    python_requires=">=3.9",
)
