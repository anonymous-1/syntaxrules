#!/usr/bin/env python

from distutils.core import setup

# sudo apt-get install libgraphviz-dev

setup(
    name="syntaxrules",
    version="0.0.02",
    description="Tools for manipulating syntax trees",
    packages=["syntaxrules"],
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering",
        "Topic :: Text Processing",
    ],
    install_requires=[
        "unidecode",
        "rdflib>=4.0.0",
        "pygraphviz",
        "requests",
    ],
)
