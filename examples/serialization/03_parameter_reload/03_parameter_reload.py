import os
import sys
from functools import partial
from idmtools.assets import Asset
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from idmtools.entities.experiment import Experiment
from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from emodpy.emod_campaign import EMODCampaign
from emodpy.generic.serialization import add_serialization_timesteps, load_serialized_population
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    SIMULATION_DURATION, del_folder, current_directory, PRE_SERIALIZATION_DAY, get_seed_experiment_builder, update_param

analyzers_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, analyzers_path)
from analyzers import TimeseriesAnalyzer  # noqa

SERIALIZATION_PATH = os.path.abspath(os.path.join(current_directory, "01_write_file_singlenode", "outputs"))

try:
    random_sim_id = os.listdir(SERIALIZATION_PATH)[-1]
    SERIALIZATION_PATH = os.path.join(SERIALIZATION_PATH, random_sim_id)
except Exception:
    raise FileNotFoundError("Can't find serialization file from previous run, please make sure 01_write_file_singlenode"
                            " succeeded.")

EXPERIMENT_NAME = 'Generic serialization 03 parameter reload'
SERIALIZATION_FILENAME = "state-00050.dtk"
CHANNELS_TOLERANCE = {'Statistical Population': 1,
                      'Infectious Population': 0.05,
                      'Waning Population': 0.05,
                      'New Infections': 20,
                      'Symptomatic Population': 40}

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # Create task from files
    task = EMODTask.from_default(default=EMODSir(), eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # Replace default campaign
    task.campaign = EMODCampaign.load_from_file(os.path.join(INPUT_PATH, "campaign.json"))

    # Add the dtk_file to the asset collection
    dtk_file = Asset(absolute_path=os.path.join(SERIALIZATION_PATH, SERIALIZATION_FILENAME))
    task.common_assets.add_asset(dtk_file)

    # Change the campaign and various parameters
    # add it to simulation by asset transient_assets. ie. simulation's current dir
    task.set_parameter("Start_Time", PRE_SERIALIZATION_DAY)
    task.set_parameter("Simulation_Duration", SIMULATION_DURATION - PRE_SERIALIZATION_DAY)

    # Enable the serialization and reload the population from the dtk file stored in the assets
    add_serialization_timesteps(task, timesteps=[LAST_SERIALIZATION_DAY],
                                end_at_final=False, use_absolute_times=True)
    load_serialized_population(task, population_path="Assets",
                               population_filenames=[SERIALIZATION_FILENAME])

    # Create the sweep for the repetitions and for the sweep on Base_Infectivity
    builder = get_seed_experiment_builder()
    set_Base_Infectivity = partial(update_param, param="Base_Infectivity")
    builder.add_sweep_definition(set_Base_Infectivity, [0.2, 1])

    experiment = Experiment.from_builder(builder, task, name=EXPERIMENT_NAME)

    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.id} failed.\n")
        exit()

    # Retrieve the parent experiment (The one used to generate the serialized population)
    pre_exp = platform.get_parent(random_sim_id, ItemType.SIMULATION)

    # Analyze
    print(f"Running TimeseriesAnalyzer with experiment id: {experiment.id} and {pre_exp.id}:\n")
    analyzers_timeseries = TimeseriesAnalyzer()
    am_timeseries = AnalyzeManager(platform=platform)
    am_timeseries.add_analyzer(analyzers_timeseries)
    am_timeseries.add_item(experiment)
    am_timeseries.add_item(pre_exp)
    am_timeseries.analyze()
    analyzers_timeseries.interpret_results(CHANNELS_TOLERANCE)

    # Download the serialization files
    print("Downloading dtk serialization files from Comps:\n")
    filenames = ['output/InsetChart.json', "output/state-" +
                 str(LAST_SERIALIZATION_DAY - PRE_SERIALIZATION_DAY).zfill(5) + ".dtk"]

    # Clean up output path if present
    output_path = 'outputs'
    del_folder(output_path)

    # Download
    analyzers_download = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am_download = AnalyzeManager(platform=platform)
    am_download.add_analyzer(analyzers_download)
    am_download.add_item(experiment)
    am_download.analyze()
