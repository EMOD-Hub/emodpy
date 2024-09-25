#!/usr/bin/python

import os
# import sys
import json

# CURRENT_DIRECTORY = os.path.dirname(__file__)
# LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
# sys.path.insert(0, LIBRARY_PATH)  # Very Important!

# import emod_api.config.dtk_pre_process_adhocevents as adhoc  # the code in this emod_api submodule should be updated then we can use it instad of having our own modified version.


def convert_plugin_reports(config_json):
    # Could do a nifty for loop but obsessing about copy-pasting can sometimes lead to unnecessarily opaque code
    crf = ""
    if "Custom_Reports_Filename" in config_json["parameters"]:
        crf = config_json["parameters"]["Custom_Reports_Filename"]
    if os.path.exists(crf):
        report_json = None
        with open(crf) as crf_handle:
            # could just read string, do replace, and write string but seems nasty to skip json parsing....
            report_json_str = json.dumps(json.load(crf_handle))
            event_map = config_json["parameters"]["Event_Map"]
            for replacement, event in event_map.items():
                report_json_str = report_json_str.replace(f'"{event}"', f'"{replacement}"')
            report_json = json.loads(report_json_str)

        with open("custom_reports_xform.json", "w") as report_json_handle:
            report_json_handle.write(json.dumps(report_json, sort_keys=True, indent=4))

        config_json["parameters"]["Custom_Reports_Filename"] = "custom_reports_xform.json"

    return config_json


def application(json_config_path):
    # Check if config.json has "Adhoc_Events". If so, process
    config_json = json.load(open(json_config_path, "r"))
    # campaign is written with GP_EVENT_XXX's but custom_reports need to be modified.
    if "Event_Map" in config_json["parameters"] and len(config_json["parameters"]["Event_Map"]) > 0:
        event_map = config_json["parameters"]["Event_Map"]
        config_json = convert_plugin_reports(config_json)

        config_json_str = json.dumps(config_json)
        for replacement, event in event_map.items():
            config_json_str = config_json_str.replace(f'"{event}"', f'"{replacement}"')
        config_json = json.loads(config_json_str)
        config_json["parameters"]["Event_Map"] = event_map
        with open("config_xform.json", "w") as new_config:
            json.dump(config_json, new_config)
        return "config_xform.json"
        # return adhoc.do_mapping_from_events( json_config_path, adhoc_events )
    else:
        return json_config_path
