import json
import sys
import os

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!

import shutil

import emod_api.schema.get_schema as get_schema
import emod_api.config.default_from_schema as default
from emod_api.schema_to_class import ReadOnlyDict
import poi_1 # loaded to Assets/python in comps
import build_my_campaign as bmc  # loaded to Assets/site-packages

def make_config(camp_filename):
    # get_schema.dtk_to_schema(eradication_path, "/var/tmp/schema.json")
    default.write_default_from_schema("Assets/schema.json")
    config = json.load(open("default_config.json"), object_hook=ReadOnlyDict)
    config = poi_1.set_params(config)
    config["parameters"]["Campaign_Filename"] = camp_filename
    with open("config_from_emodapi.json", "w") as config_file:
        json.dump(config, config_file, indent=4, sort_keys=True)
    return "config_from_emodapi.json"

def application(config_filename="config.json", debug=True): 
    shutil.copy("Assets/schema.json", "schema.json")
    camp_filename = bmc.set_random_campaign_file()
    return make_config(camp_filename)


if __name__ == "__main__":
    # execute only if run as a script
    application("config.json")
