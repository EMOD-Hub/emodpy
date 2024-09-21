import sys
import os
from functools import partial

from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps, load_serialized_population
from idmtools.utils.filters.asset_filters import file_name_is
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, SIMULATION_DURATION, del_folder, NUM_CORES, current_directory, PRE_SERIALIZATION_DAY, \
    get_seed_experiment_builder

analyzers_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, analyzers_path)
from analyzers import TimeseriesAnalyzer

MULTICORE_SERIALIZATION_PATH = os.path.abspath(os.path.join(current_directory, "06_write_file_multicore", "outputs"))
try:
    multicore_random_sim_id = os.listdir(MULTICORE_SERIALIZATION_PATH)[-1]
    MULTICORE_SERIALIZATION_PATH = os.path.join(MULTICORE_SERIALIZATION_PATH, multicore_random_sim_id)
except Exception:
    raise FileNotFoundError("Can't find serialization file from previous run, please make sure 06_write_file_multicore"
                            " succeeded.")

EXPERIMENT_NAME = 'Generic serialization 07 read files multicore'
DTK_SERIALIZATION_FILENAMES = [f"state-00050-{str(i).zfill(3)}.dtk" for i in range(NUM_CORES)]
CHANNELS_TOLERANCE = {'Statistical Population': 1,
                      'Infectious Population': 0.05,
                      'Waning Population': 0.05,
                      'New Infections': 100,
                      'Symptomatic Population': 200}

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS-Multicore')

    # Create an experiment with input files
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication.exe"),
                                  config_path=os.path.join(INPUT_PATH, 'config.json'),
                                  campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                                  demographics_paths=os.path.join(INPUT_PATH, "9nodes_demographics.json"))

    # Add the serialization filenames to the experiment collection
    filter_name = partial(file_name_is, filenames=DTK_SERIALIZATION_FILENAMES)
    task.common_assets.add_directory(assets_directory=MULTICORE_SERIALIZATION_PATH, filters=[filter_name])

    # Update parameters and setup serialization
    config_update_params(task)
    add_serialization_timesteps(task, timesteps=[LAST_SERIALIZATION_DAY],
                                end_at_final=False, use_absolute_times=True)
    load_serialized_population(task, population_path="Assets",
                               population_filenames=DTK_SERIALIZATION_FILENAMES)
    task.update_parameters({
        "Start_Time": PRE_SERIALIZATION_DAY,
        "Simulation_Duration": SIMULATION_DURATION - PRE_SERIALIZATION_DAY,
        "Num_Cores": NUM_CORES})

    # Retrieve the sweep on seed
    builder = get_seed_experiment_builder()

    # Create the experiment and run
    experiment = Experiment.from_builder(builder, task, name=EXPERIMENT_NAME)

    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.id} failed.\n")
        exit()

    # Retrieve the experiment used to generate the serialized population
    pre_exp = platform.get_parent(multicore_random_sim_id, ItemType.SIMULATION)

    # Run the timeseries analyzer
    print(f"Running TimeseriesAnalyzer with experiment id: {experiment.id} and {pre_exp.id}:\n")
    analyzers_timeseries = TimeseriesAnalyzer()
    am_timeseries = AnalyzeManager(platform=platform)
    am_timeseries.add_analyzer(analyzers_timeseries)
    am_timeseries.add_item(experiment)
    am_timeseries.add_item(pre_exp)
    am_timeseries.analyze()

    analyzers_timeseries.interpret_results(CHANNELS_TOLERANCE)

    # Download the  serialization files
    print("Downloading dtk serialization files from Comps:\n")
    filenames = ['output/InsetChart.json']
    for i in range(4):
        filenames.append(
            f"output/state-{str(LAST_SERIALIZATION_DAY - PRE_SERIALIZATION_DAY).zfill(5)}-{str(i).zfill(3)}.dtk")

    # Delete outputs if present
    output_path = 'outputs'
    del_folder(output_path)

    # Download
    analyzers_download = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am_download = AnalyzeManager(platform=platform)
    am_download.add_analyzer(analyzers_download)
    am_download.add_item(experiment)
    am_download.analyze()
