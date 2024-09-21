import json
import os
import sys

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!

"""
This is an almost no-op sample dtk_post_process.py script that just prints the disease death 
channel from InsetChart.json as a benign bit of demo functionality.
"""


def application(output_folder="output", InsetChart_filename="InsetChart.json"):
    with open(os.path.join(output_folder, InsetChart_filename), "r") as inset_chart:
        disease_deaths = json.load(inset_chart)["Channels"]["Disease Deaths"]
        print(json.dumps(disease_deaths, indent=1))


if __name__ == "__main__":
    application(output_folder="output", stdout_filename="InsetChart.json")
