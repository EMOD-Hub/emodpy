#!/usr/bin/python

import os
import sys
import emod_api.config.dtk_post_process_adhocevents as dpp

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!

# import emod_api.channelreports as emod_json
# import emod_api.spatialreports as spat
# import emod_api.tabularoutput as emod_csv


def application(output_path):
    dpp.application(output_path)
    print("dtk_post_process.py ran!")
