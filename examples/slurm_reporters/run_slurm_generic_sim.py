"""
This file demonstrates how to create experiment/simulations in slurm
"""
import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_file import MigrationPattern
from emodpy.emod_task import EMODTask
from emodpy.utils import download_from_url, bamboo_api_login

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(INPUT_PATH, "Eradication")

if __name__ == "__main__":
    # Create the platform
    platform = Platform('SLURM')
    bamboo_api_login()
    base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKGEN-DTKRELLNX/shared/build-137/"
    eradication_url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/Eradication"
    local_eradication_path = download_from_url(eradication_url, os.path.join(INPUT_PATH, "bin", "Eradication"))

    # base url to download
    dll_base_url = base_bamboo_url + "Reporter-Plugins/build/x64/Release/reporter_plugins/"
    dll_list = ["libhumanmigrationtracking.so", "libReportNodeDemographics.so"]

    # save dll files to local dir which named as filename prefix
    local_dll_dir = (os.path.split(sys.argv[0])[1]).split(".")[0]

    # download dlls
    [download_from_url(dll_base_url + dll_list[i], os.path.join(local_dll_dir, dll_list[i])) for i in
     range(len(dll_list))]

    # Create EMODTask with the set of provided files
    # The migrations files will automatically get loaded from the asset_path with what is in the config.json
    task = EMODTask.from_files(eradication_path=local_eradication_path,
                               config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               custom_reports_path=os.path.join(INPUT_PATH, "custom_reports.json"),
                               asset_path=os.path.join(INPUT_PATH, "assets"))

    task.migrations.update_migration_pattern(MigrationPattern.RANDOM_WALK_DIFFUSION, Enable_Migration_Heterogeneity=1)

    # Need to set this flag for linux Eradication
    task.is_linux = True

    demo_files = [os.path.join(INPUT_PATH, "1x3_demographics_migration_heterogeneity.json"),
                  os.path.join(INPUT_PATH, "X_0_0_all_overlay.json")]

    # add list of demographics files to task
    for demog in demo_files:
        task.demographics.add_demographics_from_file(demog)

    # load local dll folder to task
    task.reporters.add_dll_folder(local_dll_dir)

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
