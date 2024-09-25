#!/usr/bin/python

import os
import sys

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!

# import emod_api.config as conf
# import emod_api.campaign as camp
# import emod_api.demographics as demo
# import emod_api.migration as mig
# import emod_api.weather as clim
# import emod_api.serialization as serial


def application(timestep):
    print(f"Hello from dtk_in_process.py at timestep {timestep}.")
    return ""
