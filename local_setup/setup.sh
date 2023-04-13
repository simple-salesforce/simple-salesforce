#!/bin/bash
##
#   This script is used to setup the environment locally for this repository.
#
#   Sets up:
#       - pyenv: 3.6.15
##



# Virtual environment setup
pyenv virtualenv 3.6.15 simple-salesforce-3.6.15
pyenv local simple-salesforce-3.6.15
pip install --upgrade pip setuptools wheel
pip install -r test_requirements.txt
