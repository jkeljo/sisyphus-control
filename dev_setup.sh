#!/bin/bash -ex

cd "$( dirname "${BASH_SOURCE[0]}" )"

pyenv virtualenv 3.7.1 sisyphus-control
pyenv local sisyphus-control
pip install --upgrade pip
pip install -r requirements.txt
