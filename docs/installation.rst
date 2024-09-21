============
Installation
============

You can install |EMODPY_s| in two different ways. If you intend to use |EMODPY_s| as
|IDM_s| builds it, follow the instructions in :doc:`basic-installation`.
However, if you intend to modify the |EMODPY_s| source code to add new
functionality, follow the instructions in :doc:`dev-installation`. Whichever
installation method you choose, the prerequisites are the same.

.. _idmtools-prereqs:

Prerequisites
=============

* Windows 10 Pro or Enterprise

* |Python_supp| (https://www.python.org/downloads/release)

  .. warning::

    Do not install Python 3.8, which includes breaking changes.

* Python virtual environments

    Python virtual environments enable you to isolate your Python environments from one
    another and give you the option to run multiple versions of Python on the same computer. When using a
    virtual environment, you can indicate the version of Python you want to use and the packages you
    want to install, which will remain separate from other Python environments. You may use
    ``virtualenv``, which requires a separate installation, but ``venv`` is recommended and included with Python 3.3+.

.. toctree::

    basic-installation
    dev-installation