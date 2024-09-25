<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [run emodpy tests locally](#run-emodpy-tests-locally)
- [run emodpy tests on bamboo](#run-emodpy-tests-on-bamboo)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


# run emodpy tests locally


How to run these tests locally after you have emodpy installed in a virtual environment. 

1. Active your virtual environment

2. install idmtools-test from staging or production
```bash
pip install idmtools-test --index-url=https://email:password@packages.idmod.org/api/pypi/pypi-staging/simple
OR
pip install idmtools-test --index-url=https://packages.idmod.org/api/pypi/pypi-production/simple
```

3. install dataclasses
```bash
pip install dataclasses
```

4. login to bamboo and cache your credential(need VPN, can skiped if you choose to enter your credential in step 5 in console)
```bash
python bamboo_login_with_arguments.py -u youremail@idmod.org -p password
```

5. download eradication and schema files from bamboo(need VPN)
```bash
pytest test_download_from_bamboo.py
```
It may prompt to ask you to enter username and password if you didn not run step 4.

6. run emod tests
```bash
pytest -v -m emod
```

You will need to setup your environment if this is the first time you are running Eradication in your local environment:
https://www.idmod.org/docs/emod/generic/dev-install-windows-prerequisites.html?searchText=installation#id1

# run emodpy tests on bamboo

1. Connect to IDM VPN

2. go to https://bamboo.idmod.org/bamboo/browse/EMODPY-EMODPYTEST

* <b>WIN_EMODPY_Code_Test</b>: This plan will run all tests with emodpy package that is built from your code and all other dependencies from IDM pypi production environment. This is the plan that you will need to run if you are working on a PR for emodpy.

3. If you want to run against dev-next branch, you just click Run -> Run plan. 

If you want to run against a particular branch, click Run -> Run customized, in the pop up window, click 'override a variable', select 'GitHubURL' and paste url of the branch you want to run. Click 'Run'.


Here are descriptions for other bamboo plans in the same project that you may be interested to know/use:

* <b>WIN_EMODPY_Code_Emodapi_Staging_Test</b>: This plan will run all tests with emodpy package that is built from your code and emod-api from IDM pypi staging environment.

* <b>WIN_EMODPY_Staging_Test</b>: This plan will run all tests with emodpy package and emod-api from IDM pypi staging environment.

* <b>WIN_EMODPY_Staging_Emodapi_Prod_Test</b>: This plan will run all tests with emodpy package from IDM pypi staging environment and and emod-api package from IDM pypi production environment.

* <b>WIN_EMODPY_Prod_Test</b>: This plan will run all tests with emodpy package and other dependencies from IDM pypi production environment.

The <b>WIN_</b> prefix means the tests are running on Windows bamboo agent machine. 
