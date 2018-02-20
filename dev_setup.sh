#!/bin/bash -ex

cd "$( dirname "${BASH_SOURCE[0]}" )"

virtualenv -p python3.6 venv
source venv/bin/activate
pip3 install -r requirements.txt
