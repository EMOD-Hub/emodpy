"""
    This example creates a serialized population file from the DTK's ENVIRONMENTAL_SIM
    and downloads the serialized population files to the client.  This is prerequisite
    for doing COVID19 modeling in the DTK
"""
# Common python imports
import os

# Code under test imports
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer

# Constants
from examples.dtk_covid.globals import ERADICATION_PATH, SIM_CONFIG_PATH

if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2'):

        # create the resources task
        make_resources_task = EMODTask.from_files(
            eradication_path=ERADICATION_PATH,
            config_path=os.path.join(SIM_CONFIG_PATH, "config_env_write_spop.json"),
            campaign_path=os.path.join(SIM_CONFIG_PATH, "campaign_seed_infection.json"),
            demographics_paths=[
                os.path.join(SIM_CONFIG_PATH, "demographics.json"),
                os.path.join(SIM_CONFIG_PATH, "demographics_1000_overlay.json")
            ]
        )

        serialization_timesteps = [20, 30, 50]
        add_serialization_timesteps(
            task=make_resources_task,
            timesteps=serialization_timesteps,
            end_at_final=False,
            use_absolute_times=False
        )

        # create an experiment using the task(one simulation)
        experiment = Experiment.from_task(task=make_resources_task,
                                          name="DTK-COVID examples 00 generate environmental sim statefile")
        # run and wait
        experiment.run(wait_until_done=True)

        # if we failed, exit and alert user
        if not experiment.succeeded:
            print(f"Experiment {experiment.uid} failed.\n")
            exit()

        print(f"Experiment {experiment.uid} succeeded.\nDownloading dtk serialization files from Comps:\n")

        # Cleanup the output path
        output_path = 'spop_files'

        # We want to download all the dtk state files and the InsetChart.json
        filenames = []
        for serialization_timestep in serialization_timesteps:
            filenames.append(f"output/state-{serialization_timestep:05}.dtk")
        filenames.append('output/InsetChart.json')

        # remove the files if they already exist
        for f in filenames:
            filepath = os.path.join(output_path, f)
            if os.path.isfile(filepath):
                os.unlink(filepath)

        # Create the analyze manager
        am = AnalyzeManager()
        am.add_item(experiment)
        am.add_analyzer(DownloadAnalyzer(filenames=filenames, output_path=output_path))

        # Analyze
        am.analyze()
