"""
    This example consumes the serialized population file from scenario_00 and uses
    python pre-processing to do the following:
    * add individual properties to the individuals in the population
    * add a demographic overlay file that allows the model to recognize the new IPs
"""
# Common python imports
import os

# Code under test imports
from idmtools.assets import Asset
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask

# Constants
from examples.dtk_covid.globals import ERADICATION_PATH, SIM_CONFIG_PATH, SPOPS_ROOT, PYTHON_PROCESS_FOLDER

PYTHON_PROCESS_FOLDER = os.path.join(PYTHON_PROCESS_FOLDER, "manipulate_population")

try:
    random_sim_id = [x for x in os.listdir(SPOPS_ROOT) if x not in ["README.txt"]][0]
    SPOP_FOLDER = os.path.join(SPOPS_ROOT, random_sim_id)
except Exception:
    raise FileNotFoundError(f"Couldn't find a folder under {SPOPS_ROOT},"
                            f" try running scenario_00 first.")

if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:

        manipulate_population_task = EMODTask.from_files(
            eradication_path=ERADICATION_PATH,
            config_path=os.path.join(SIM_CONFIG_PATH, "config_env_manipulate_population.json"),
            campaign_path=os.path.join(SIM_CONFIG_PATH, "campaign_seed_infection.json"),
            demographics_paths=[
                os.path.join(SIM_CONFIG_PATH, "demographics.json"),
                os.path.join(SIM_CONFIG_PATH, "demographics_1000_overlay.json")
            ],
            use_embedded_python=True
        )

        # Add the serialized population file to the experiment
        manipulate_population_task.common_assets.add_asset(os.path.join(SPOP_FOLDER, "state-00050.dtk"))

        manipulate_population_task.common_assets.add_asset(
            os.path.join(PYTHON_PROCESS_FOLDER, "dtk_pre_process.py"), relative_path='python')

        # dtk_FileTools
        manipulate_population_task.common_assets.add_asset(
            os.path.join(PYTHON_PROCESS_FOLDER, "dtk_FileTools.py"), relative_path='python')

        # dtk_FileSupport
        manipulate_population_task.common_assets.add_asset(
            os.path.join(PYTHON_PROCESS_FOLDER, "dtk_FileSupport.py"), relative_path='python'
        )

        # dtk_serialization_support
        # dtk_serialization_support_asset = Asset(os.path.join(PYTHON_PROCESS_FOLDER,
        #                                                      "dtk_serialization_support.py"),
        #                                         relative_path='python')
        # manipulate_population_task.common_assets.add_asset(dtk_serialization_support_asset)

        experiment = Experiment.from_task(
            task=manipulate_population_task,
            name="DTK-COVID examples 02 manipulate serialized population in pre-processing")

        experiment.run(wait_until_done=True)
