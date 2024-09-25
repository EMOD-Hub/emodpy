"""
This file demonstrates how to create experiment/simulations using legacy malaria and custom report.
"""
import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "..", "inputs", "malaria_2_15")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(INPUT_PATH, "Assets", "Eradication.exe")

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # Create EMODTask with the set of provided files
    # The climate files will automatically get loaded from the asset_path with what is in the config.json
    task = EMODTask.from_files(eradication_path=ERADICATION_PATH,
                               config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=[os.path.join(INPUT_PATH, "Assets", "under_5_demographics_with_SMC_access.json")],
                               custom_reports_path=os.path.join(INPUT_PATH, "custom_reports.json"),
                               asset_path=os.path.join(INPUT_PATH, "Assets"))

    # No need to update dlls with following line since they are loaded from assets_path above in task
    # task.reporters.add_dll_folder(os.path.join(INPUT_PATH, "Assets", "reporter_plugins"))

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
