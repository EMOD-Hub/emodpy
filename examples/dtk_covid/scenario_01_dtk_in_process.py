"""
    This example demonstrates how to use dtk_in_process to create transmission blocking
    vaccines at runtime in the DTK. This uses the following new DTK features
    * dtk_in_process
    * Enable_Event_DB enables the DTK to write simulation events to a sqlite file at every timestep
    * TargetDemographic:ExplicitID allows interventions to target individuals by their SUID
"""
# TODO: use an analyzer to confirm that new infections channel is the same as campaign cost channel


# Common python imports
import os

# Code under test imports
from idmtools.assets import Asset
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask

# Constants
from examples.dtk_covid.globals import ERADICATION_PATH, SIM_CONFIG_PATH, PYTHON_PROCESS_FOLDER

if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:
        in_process_vaccine_task = EMODTask.from_files(
            eradication_path=ERADICATION_PATH,
            config_path=os.path.join(SIM_CONFIG_PATH, "config_explicitid_targetsone.json"),
            campaign_path=os.path.join(SIM_CONFIG_PATH, "campaign_seed_infection.json"),
            demographics_paths=[
                os.path.join(SIM_CONFIG_PATH, "demographics.json"),
                os.path.join(SIM_CONFIG_PATH, "demographics_1000_overlay.json")
            ],
            use_embedded_python=True
        )
        # enable the event db
        in_process_vaccine_task.set_parameter("Enable_Event_DB", 1)

        # add our in process python script
        in_process_vaccine_task.common_assets.add_asset(
            os.path.join(PYTHON_PROCESS_FOLDER, "dtk_in_process.py"),
            relative_path='python'
        )

        # add the preprocess script
        in_process_vaccine_task.common_assets.add_asset(
            os.path.join(PYTHON_PROCESS_FOLDER, "do_nothing", "dtk_pre_process.py"),
            relative_path='python'
        )

        # create the experiment from the task
        experiment = Experiment.from_task(task=in_process_vaccine_task,
                                          name="DTK-COVID examples 01 dtk_in_process contact tracing")
        # and run it and wait until it is done
        experiment.run(wait_until_done=True)
        experiment.print()
