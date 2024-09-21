"""
This file demonstrates how to create experiment/simulations using built-in reporters provided by the user.
/!\ The built-in reporters is a feature only supported with HIV-Ongoing and Malaria-Ongoing executables! /!\
"""
import os
import sys
from functools import partial

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.reporters.builtin import ReportNodeDemographics

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(INPUT_PATH, "Eradication.exe")

if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:
        ip = partial(os.path.join, INPUT_PATH)
        # Create EMODTask with the set of provided files
        task = EMODTask.from_files(eradication_path=ip("Eradication.exe"), config_path=ip("config.json"),
                                   campaign_path=ip("campaign.json"),
                                   demographics_paths=[ip("Base_Demog_Trunk_TB.json"), ip("Base_Overlay_TB.json")])

        # Create a reporter
        reporter = ReportNodeDemographics()
        reporter.Age_Bins.append(125.0)
        task.reporters.add_reporter(reporter)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
        experiment.run(wait_until_done=True)

        # use system status as the exit code
        sys.exit(0 if experiment.succeeded else -1)
