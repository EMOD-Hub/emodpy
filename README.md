# emodpy

**emodpy** is a shared Python workflow infrastructure used by disease-specific EMOD packages.

[![Build docs and deploy to GH Pages](https://github.com/EMOD-Hub/emodpy/actions/workflows/mkdocs_deploy.yml/badge.svg)](https://github.com/EMOD-Hub/emodpy/actions/workflows/mkdocs_deploy.yml)
[![Lint](https://github.com/EMOD-Hub/emodpy/actions/workflows/lint.yml/badge.svg)](https://github.com/EMOD-Hub/emodpy/actions/workflows/lint.yml)
[![Test and update version](https://github.com/EMOD-Hub/emodpy/actions/workflows/test_and_bump_version.yml/badge.svg)](https://github.com/EMOD-Hub/emodpy/actions/workflows/test_and_bump_version.yml)

## Project status

EMOD-Hub projects are provided as open source software under the MIT License for
community use, research, and development.

**Unless otherwise noted, these projects are no longer actively maintained or supported
by IDM or the Gates Foundation.**

Community contributions are welcome, and trusted collaborators may review and
merge pull requests, but no guarantees are made regarding support, pull request
review, security response, maintenance, or release timelines.

## Python Version

Python 3.13 is the recommended and supported version.

## Documentation

Documentation available at https://emod.idmod.org/emodpy/

To build the documentation locally, do the following:

1. Create and activate a venv.
2. Navigate to the root directory of the repo.
    ```
    python -m pip install .[docs]
    mkdocs serve
    ```

## Running tests

Please see the documentation for [testing](/tests/README.md).

## Community

Have a question or a comment? Check out our
[Discussions](https://github.com/orgs/EMOD-Hub/discussions) space.

## Contributing

If you have feature requests, issues, or new code, please see our
[CONTRIBUTING](https://github.com/EMOD-Hub/.github/blob/main/CONTRIBUTING.md)
page for how to provide your feedback.
