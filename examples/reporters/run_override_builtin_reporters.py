"""
This file demonstrates how to create experiment/simulations using builtin reports.
"""
import os
import sys
from dataclasses import dataclass, field

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.reporters.builtin import MalariaSummaryReport
from emodpy.utils import bamboo_api_login, download_from_url

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "..", "inputs", "malaria_on_going")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name


@dataclass
class MyMalariaSummaryReport(MalariaSummaryReport):
    Age_Bins: list = field(default_factory=list)
    Infectiousness_Bins: list = field(default_factory=list)
    Parasitemia_Bins = [50.0, 500.0, 5000.0, 9223372036854775807]
    Max_Number_Reports: int = 10000
    Duration_Days: int = 100000
    Reporting_Interval: int = 365
    Start_Day: int = 0
    Nodeset_Config = {"class": "NodeSetAll"}


if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # login to bamboo with your company email as username and password
    bamboo_api_login()

    # base bamboo url for downloading eradication and reporter_plugins
    base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKACTIVEMALBRANCH-DTKACTMALRELWINSCONS/shared/build-240/"

    # Eradication.exe url
    eradication_url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/Eradication.exe"

    # download Eradication.exe from bamboo to local, here we saved to INPUT_PATH/bin dir
    local_eradication_path = download_from_url(eradication_url, os.path.join(INPUT_PATH, "bin", "Eradication.exe"))

    # Create EMODTask with the set of provided files
    # The climate files will automatically get loaded from the asset_path with what is in the config.json
    task = EMODTask.from_files(eradication_path=local_eradication_path,
                               config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=[os.path.join(INPUT_PATH, "Assets", "Namawala",
                                                                "Namawala_single_node_demographics.json")],
                               asset_path=os.path.join(INPUT_PATH, "Assets"))

    # override builtin MalariaSummaryReport
    reporter = MyMalariaSummaryReport()
    age_bins = [10, 20]
    [reporter.Age_Bins.append(x) for x in age_bins]
    infectiousness_bins = [20.0, 40.0, 60.0]
    [reporter.Infectiousness_Bins.append(x) for x in infectiousness_bins]
    task.reporters.add_reporter(reporter)

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)

    # note: this example depends on bug fix 57.
    # workaround for now is to remove following line in emod_task.py
    # self.config["Custom_Individual_Events"] = []
