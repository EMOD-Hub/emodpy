<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [run emodpy tests locally](#run-emodpy-tests-locally)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# run emodpy tests locally

How to run these tests locally after you have emodpy installed in a virtual environment. 

1. Active your virtual environment

2. Install testing requirements
```bash
pip install -r tests/requirements.txt --extra-index-url=https://packages.idmod.org/api/pypi/pypi-production/simple
```

3. run emod tests
```bash
pytest -v -m emod
```
