==================
Basic installation
==================

Follow the steps below if you will use |IT_s| to run and analyze simulations, but will not make
source code changes.

#.  Open a command prompt and create a virtual environment in any directory you choose. The
    command below names the environment "emodpy", but you may use any desired name::

        python -m venv emodpy

#.  Activate the virtual environment:

        * On Windows, enter the following::

            emodpy\Scripts\activate

        * On Linux, enter the following::

            source emodpy/bin/activate

#.  Install |IT_s| packages::

        pip install emodpy --index-url=https://packages.idmod.org/api/pypi/pypi-production/simple

#.  Verify installation by pulling up |IT_s| help::

        emodpy --help

#.  When you are finished, deactivate the virtual environment by entering the following at a command prompt::

        deactivate

