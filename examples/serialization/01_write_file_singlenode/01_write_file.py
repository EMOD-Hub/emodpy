import os

from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask
from idmtools.core.platform_factory import Platform
from emodpy.defaults import EMODSir
from emodpy.emod_campaign import EMODCampaign
from emodpy.generic.serialization import add_serialization_timesteps
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, START_DAY, SIMULATION_DURATION, del_folder

EXPERIMENT_NAME = 'Generic serialization 01 write files'


def download_serialized_files(experiment):
    # Cleanup the output path
    output_path = 'outputs'
    del_folder(output_path)
    # We want to download all the dtk state files and the InsetChart.json
    filenames = []
    for serialization_timestep in serialization_timesteps:
        filenames.append("output/state-" + str(serialization_timestep).zfill(5) + ".dtk")
    filenames.append('output/InsetChart.json')
    # Create the analyze manager
    am = AnalyzeManager()
    am.add_item(experiment)
    am.add_analyzer(DownloadAnalyzer(filenames=filenames, output_path=output_path))
    # Analyze
    am.analyze()


if __name__ == "__main__":
    # Create the platform
    with Platform('COMPS2') as platform:

        # create EMODTask from default
        task = EMODTask.from_default(default=EMODSir(),
                                     eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

        # Replace default campaign
        task.campaign = EMODCampaign.load_from_file(os.path.join(INPUT_PATH, "campaign.json"))

        # Replace default demographics from defaults with our own file
        task.demographics.clear()
        task.demographics.add_demographics_from_file(os.path.join(INPUT_PATH, "demographics.json"))

        # Update bunch of config parameters
        config_update_params(task)

        # Create the serialization timesteps
        serialization_timesteps = list(range(10, LAST_SERIALIZATION_DAY + 20, 20))
        add_serialization_timesteps(
            task=task, timesteps=serialization_timesteps, end_at_final=True, use_absolute_times=False
        )

        # Handle start day and duration
        task.set_parameter("Start_Time", START_DAY)
        task.set_parameter("Simulation_Duration", SIMULATION_DURATION)

        # Create the experiment from task and run
        experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
        experiment.run(wait_until_done=True)

        if not experiment.succeeded:
            experiment.print()
            exit()

        print(f"Experiment {experiment.uid} succeeded.\nDownloading dtk serialization files from Comps:\n")

        download_serialized_files(experiment)
