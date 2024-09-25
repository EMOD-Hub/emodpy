import os
import sys

from idmtools.assets import Asset
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps, load_serialized_population

from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, SIMULATION_DURATION, del_folder, PRE_SERIALIZATION_DAY, get_seed_experiment_builder, \
    current_directory

analyzers_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, analyzers_path)
from analyzers import TimeseriesAnalyzer

MULTINODE_SERIALIZATION_PATH = os.path.abspath(os.path.join(current_directory, "04_write_file_multinode", "outputs"))
try:
    multinode_random_sim_id = os.listdir(MULTINODE_SERIALIZATION_PATH)[-1]
    MULTINODE_SERIALIZATION_PATH = os.path.join(MULTINODE_SERIALIZATION_PATH, multinode_random_sim_id)
except Exception:
    raise FileNotFoundError("Can't find serialization file from previous run, please make sure 04_write_file_multinode"
                            " succeeded.")

EXPERIMENT_NAME = 'Generic serialization 05 read files multinode'
DTK_SERIALIZATION_FILENAME = "state-00050.dtk"
CHANNELS_TOLERANCE = {'Statistical Population': 1,
                      'Infectious Population': 0.05,
                      'Waning Population': 0.05,
                      'New Infections': 100,
                      'Symptomatic Population': 200}

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # Create an experiment based on input files
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication.exe"),
                               config_path=os.path.join(INPUT_PATH, 'config.json'),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=os.path.join(INPUT_PATH, "9nodes_demographics.json"))

    # Add the serialized population to the experiment's assets
    dtk_file = Asset(absolute_path=os.path.join(MULTINODE_SERIALIZATION_PATH, DTK_SERIALIZATION_FILENAME))
    task.common_assets.add_asset(dtk_file)

    # UUpdate config parameters and configure serialization
    config_update_params(task)
    task.update_parameters({
        "Start_Time": PRE_SERIALIZATION_DAY,
        "Simulation_Duration": SIMULATION_DURATION - PRE_SERIALIZATION_DAY})
        #"Enable_Random_Generator_From_Serialized_Population": 1,
        #"Random_Number_Generator_Policy": "ONE_PER_NODE",
        #"Random_Number_Generator_Type": "USE_PSEUDO_DES"})

    add_serialization_timesteps(task, timesteps=[LAST_SERIALIZATION_DAY],
                                end_at_final=False, use_absolute_times=True)
    load_serialized_population(task, population_path="Assets",
                               population_filenames=[DTK_SERIALIZATION_FILENAME])

    # Add the seeds builder
    builder = get_seed_experiment_builder()

    # Create the experiment and run
    experiment = Experiment.from_builder(builder, task, name=EXPERIMENT_NAME)

    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.id} failed.\n")
        exit()

    # Get the parent experiment (used to generate the serialized population)
    pre_exp = platform.get_parent(multinode_random_sim_id, ItemType.SIMULATION)

    print(f"Running TimeseriesAnalyzer with experiment id: {experiment.id} and {pre_exp.id}:\n")

    analyzers_timeseries = TimeseriesAnalyzer()
    am_timeseries = AnalyzeManager(platform=platform)
    am_timeseries.add_analyzer(analyzers_timeseries)
    am_timeseries.add_item(experiment)
    am_timeseries.add_item(pre_exp)
    am_timeseries.analyze()

    analyzers_timeseries.interpret_results(CHANNELS_TOLERANCE)

    # Download the dtk serialization files
    print("Downloading dtk serialization files from Comps:\n")
    filenames = ['output/InsetChart.json', "output/state-" +
                 str(LAST_SERIALIZATION_DAY - PRE_SERIALIZATION_DAY).zfill(5) + ".dtk"]

    # Cleanup if the outputs already exist
    output_path = 'outputs'
    del_folder(output_path)

    analyzers_download = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am_download = AnalyzeManager(platform=platform)
    am_download.add_analyzer(analyzers_download)
    am_download.add_item(experiment)
    am_download.analyze()
