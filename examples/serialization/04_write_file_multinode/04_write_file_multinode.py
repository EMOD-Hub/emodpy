import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer

from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, START_DAY, SIMULATION_DURATION, del_folder

EXPERIMENT_NAME = 'Generic serialization 04 writes files multinode'

if __name__ == "__main__":
    # Create the platform
    platform = Platform('Slurm')

    # Create the experiment from input files
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication"),
                                  config_path=os.path.join(INPUT_PATH, 'config.json'),
                                  campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                                  demographics_paths=os.path.join(INPUT_PATH, "9nodes_demographics.json"))

    # Update the configuration parameters and enable serialization
    config_update_params(task)
    serialization_timesteps = list(range(10, LAST_SERIALIZATION_DAY + 20, 20))
    add_serialization_timesteps(task=task, timesteps=serialization_timesteps,
                                end_at_final=False, use_absolute_times=False)
    task.update_parameters({
        "Start_Time": START_DAY,
        "Simulation_Duration": SIMULATION_DURATION
        # "Random_Number_Generator_Policy": "ONE_PER_NODE",
        # "Random_Number_Generator_Type": "USE_PSEUDO_DES"
    })

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.id} failed.\n")
        exit()

    # Create the filename list
    filenames = []
    for serialization_timestep in serialization_timesteps:
        filenames.append("output/state-" + str(serialization_timestep).zfill(5) + ".dtk")
    filenames.append('output/InsetChart.json')

    # Delete the outputs if existed already
    output_path = 'outputs'
    del_folder(output_path)

    # Download the files
    am = AnalyzeManager(platform=platform)
    download_analyzer = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am.add_analyzer(download_analyzer)
    am.add_item(experiment)
    am.analyze()
