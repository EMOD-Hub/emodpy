#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script for the emodpy platform"""
import sys

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('requirements.txt') as requirements_file:
    lines = requirements_file.read().strip().split("\n")
requirements = []
arguments = []
develop_install = 'develop' in sys.argv
for line in lines:
    if line[0] == '-':
        # we have a flag to handle by insertion on the command line
        arguments.extend(line.split(' '))
    else:
        # we have an actual package requirement
        requirements.append(line)
if develop_install:
    sys.argv.extend(arguments)

build_requirements = ['flake8', 'coverage', 'py-make', 'bump2version', 'twine']
setup_requirements = []
test_requirements = ['pytest', 'pytest-runner', 'pytest-timeout', 'pytest-cache'] + build_requirements

extras = dict(test=test_requirements, packaging=build_requirements)

authors = [
    ("Ross Carter", "rcarter@idmod.org"),
    ("Sharon Chen", "shchen@idmod.org"),
    ("Clinton Collins", "ccollins@idmod.org"),
    ("Zhaowei Du", "zdu@idmod.org"),
    ("Mandy Izzo", "mizzo@idmod.org"),
    ("Clark Kirkman IV", "ckirkman@idmod.org"),
    ("Jen Schripsema", "jschripsema@idmod.org"),
    ("J. Bloedow", "jbloedow@idmod.org")
]

setup(
    author=[author[0] for author in authors],
    author_email=[author[1] for author in authors],
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework:: IDM-Tools :: models'
    ],
    description="Core tools for modeling",
    install_requires=requirements,
    long_description=readme,
    include_package_data=True,
    keywords='modeling, IDM',
    name='emodpy',
    entry_points={"idmtools_task":  # noqa E521
                      ["idmtools_task_emod = emodpy.emod_task:EMODTaskSpecification"],
                  "idmtools_cli.cli_plugins": ["emodpy=emodpy_cli.cli.schema:emodpy"]
                  },
    packages=find_packages(),
    python_requires='>=3.6.*, !=3.7.0, !=3.7.1, !=3.7.2',
    setup_requires=setup_requirements,
    test_suite='tests',
    extras_require=extras,
    version='1.19.0'
)
