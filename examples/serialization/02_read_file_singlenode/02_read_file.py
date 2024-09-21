import os
import sys

from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask

from idmtools.assets import Asset
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from emodpy.generic.serialization import load_serialized_population, add_serialization_timesteps
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, SIMULATION_DURATION, del_folder, PRE_SERIALIZATION_DAY, get_seed_experiment_builder, \
    current_directory

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

EXPERIMENT_NAME = 'Generic serialization 02 read files'
DTK_SERIALIZATION_FILENAME = "state-00050.dtk"
CHANNELS_TOLERANCE = {'Statistical Population': 1,
                      'Infectious Population': 0.05,
                      'Waning Population': 0.05,
                      'New Infections': 100,
                      'Symptomatic Population': 200}


def analyze_inset_chart(exp: Experiment, pre_experiment: Experiment) -> TimeseriesAnalyzer:
    """
    Running timeseries with both experiment and pre-experiment

    Args:
        exp: Experiment
        pre_experiment: PreExperiment

    Returns:
        TimeseriesAnalyzer
    """
    # Configure the analyzer to work on the InsetChart.json
    analyzers_timeseries = TimeseriesAnalyzer()
    # Create the analyze manager and analyze
    print(f"Running TimeseriesAnalyzer with experiment id: {exp.id} and {pre_experiment.id}:\n")
    am_timeseries = AnalyzeManager()
    am_timeseries.add_item(exp)
    am_timeseries.add_item(pre_experiment)
    am_timeseries.add_analyzer(analyzers_timeseries)
    am_timeseries.analyze()

    # Interpret results
    analyzers_timeseries.interpret_results(tolerances=CHANNELS_TOLERANCE)
    return analyzers_timeseries


def download_serialized_files(exp: Experiment):
    """
    Download Serialized files from experiment

    Args:
        exp: Experiment to download

    Returns:
        None
    """
    # Download the serialization files from COMPS
    print("Downloading dtk serialization files from Comps:\n")
    filenames = ['output/InsetChart.json',
                 "output/state-" + str(LAST_SERIALIZATION_DAY - PRE_SERIALIZATION_DAY).zfill(5) + ".dtk"]
    # Clean up previously ran analyzers if any
    output_path = 'outputs'
    del_folder(output_path)
    # Run the analysis
    analyzer_download = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am_download = AnalyzeManager()
    am_download.add_item(exp)
    am_download.add_analyzer(analyzer_download)
    am_download.analyze()


if __name__ == "__main__":
    # Create the platform
    with Platform('Slurm') as platform:

        # Create the experiment by providing the input files
        task = EMODTask.from_files(
            eradication_path=os.path.join(BIN_PATH, "Eradication"),
            config_path=os.path.join(INPUT_PATH, 'config.json'),
            campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
            demographics_paths=os.path.join(INPUT_PATH, "demographics.json")
        )
        # Add the serialized population file to the experiment
        task.common_assets.add_asset(os.path.join(SERIALIZATION_PATH, DTK_SERIALIZATION_FILENAME))

        # Serialization parameters: Enable serialization and reload the population
        add_serialization_timesteps(task, timesteps=[LAST_SERIALIZATION_DAY],
                                    end_at_final=False, use_absolute_times=True)
        load_serialized_population(task, population_path="Assets",
                                   population_filenames=[DTK_SERIALIZATION_FILENAME])
        # Configuration parameters
        config_update_params(task)
        task.set_parameter("Start_Time", PRE_SERIALIZATION_DAY)
        task.set_parameter("Simulation_Duration", SIMULATION_DURATION - PRE_SERIALIZATION_DAY)

        # Create the sweep on seed
        builder = get_seed_experiment_builder()

        # Create the experiment from builder
        experiment = Experiment.from_builder(builder, task, name=EXPERIMENT_NAME)
        experiment.run(wait_until_done=True)

        if not experiment.succeeded:
            experiment.print()
            exit()

        # Retrieve the experiment that was used to create the serialization
        pre_exp = platform.get_parent(random_sim_id, ItemType.SIMULATION)
        analyze_inset_chart(experiment, pre_exp)
        download_serialized_files(experiment)
