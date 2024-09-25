"""
This file demonstrates how to create experiment/simulations using custom reports.
Also show how to override custom reports
"""
import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.reporters.custom import MalariaImmunityReport
from emodpy.utils import bamboo_api_login, download_from_url

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "..", "inputs", "generic-ongoing", "malaria")
ASSETS_PATH = os.path.join(current_directory, "..", "inputs", "malaria_on_going", "Assets")

EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name


if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # login to bamboo with your company email as username and password
    # This will only need do once
    bamboo_api_login()

    # base bamboo url for downloading eradication and reporter_plugins
    base_bamboo_url = "http://idm-bamboo:8085/artifact/DTKGENCI-SCONSWINALL/shared/build-19/"

    # Eradication.exe url
    eradication_url = base_bamboo_url + "Eradication.exe/build/x64/Release/Eradication/Eradication.exe"

    # download Eradication.exe from bamboo to local, here we saved to INPUT_PATH/bin dir
    local_eradication_path = download_from_url(eradication_url, os.path.join(INPUT_PATH, "bin", "Eradication.exe"))

    # Create EMODTask with the set of provided files
    # The climate files will automatically get loaded from the asset_path with what is in the config.json
    task = EMODTask.from_files(eradication_path=local_eradication_path,
                               config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               custom_reports_path=os.path.join(INPUT_PATH, "custom_reports.json"),
                               asset_path=os.path.join(ASSETS_PATH, "Namawala"))

    # list of demographics files in local
    demo_files = [os.path.join(INPUT_PATH, "Namawala_single_node_demographics.json"),
                  os.path.join(INPUT_PATH, "Namawala_single_node_demographics_initial_prevalence_genomes.json"),
                  os.path.join(INPUT_PATH, "Namawala_single_node_demographics_complex_mortality.json"),
                  os.path.join(INPUT_PATH, "Namawala_single_node_demographics.immunity.json")]

    # add list of demographics files to task
    for demog in demo_files:
        task.demographics.add_demographics_from_file(demog)

    # base url to download
    dll_base_url = base_bamboo_url + "Reporter-Plugins/build/x64/Release/reporter_plugins/"
    dll_list = ["libreporteventcounter.dll", "libmalariasummary_report_plugin.dll",
                "libmalariasurveyJSON_analyzer_plugin.dll", "libReportMalariaTransmissions.dll",
                "libmalariaimmunity_report_plugin.dll"]

    # save dll files to local dir which named as filename prefix
    local_dll_dir = (os.path.split(sys.argv[0])[1]).split(".")[0]

    # download dlls
    [download_from_url(dll_base_url + dll_list[i], os.path.join(local_dll_dir, dll_list[i])) for i in
     range(len(dll_list))]

    # load local dll folder to task
    task.reporters.add_dll_folder(local_dll_dir)

    # create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
