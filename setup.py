from codecs import open
from os import path
from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="sisyphus-control",
    version="3.0",
    description="Control your Sisyphus kinetic art tables "
                "(sisyphus-industries.com)",
    long_description=long_description,
    url="https://github.com/jkeljo/sisyphus-control",
    author="Jonathan Keljo",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Home Automation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="sisyphus",
    packages=["sisyphus_control"],
    package_data={
        "sisyphus_control": ["py.typed"]
    },
    install_requires=[
        "aiohttp",
        "netifaces",
        "python-socketio==4.6.1",
        "python-engineio==3.14.2"
    ],
    python_requires=">=3.9",
)
