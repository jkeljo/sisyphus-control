#!/bin/bash -ex

cd "$( dirname "${BASH_SOURCE[0]}" )"

pyenv install 3.9.7
pyenv virtualenv 3.9.7 sisyphus-control
pyenv local sisyphus-control
pip install --upgrade pip
pip install -r requirements.txt
