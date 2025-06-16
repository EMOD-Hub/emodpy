==================
Basic installation
==================

Follow the steps below if you will use |IT_s| to run and analyze simulations, but will not make
source code changes.

#.  Open a command prompt and create a virtual environment in any directory you choose. The
    command below names the environment "emodpy", but you may use any desired name, and any 
    available path you prefer::

        python -m venv /path/to/venv/root/emodpy

#.  Activate the virtual environment:

        * On Windows, enter the following::

            \path\to\venv\root\emodpy\Scripts\activate

        * On Linux, enter the following::

            source /path/to/venv/root/emodpy/bin/activate

#.  Install |IT_s| packages. ::

        pip install emodpy --extra-index-url=https://packages.idmod.org/api/pypi/pypi-production/simple

    (It's strongly recommended that you edit your pip.ini or pip.conf so you don't have to specificy --index-url.)

#.  Verify installation by doing a test import::

        python -c 'import emodpy'

#.  When you are finished, deactivate the virtual environment by entering the following at a command prompt::

        deactivate

