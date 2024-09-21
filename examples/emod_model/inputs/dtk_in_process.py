import sys
import os

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!

import emod_api

def application(timestep):
    print(f"dtk_in_process.py called on timestep {timestep}.")
    return ""
