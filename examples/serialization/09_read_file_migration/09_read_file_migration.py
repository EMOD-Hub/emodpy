import sys
import os
from functools import partial

from idmtools.assets import Asset
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps, load_serialized_population
from idmtools.utils.filters.asset_filters import file_name_is
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from emodpy.emod_file import MigrationTypes, MigrationPattern
from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, SIMULATION_DURATION, del_folder, DTK_LOCAL_MIGRATION_FILENAME, X_LOCAL_MIGRATION, \
    DTK_REGIONAL_MIGRATION_FILENAME, X_REGIONAL_MIGRATION, current_directory, PRE_SERIALIZATION_DAY, \
    get_seed_experiment_builder

analyzers_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, analyzers_path)
from analyzers import TimeseriesAnalyzer, NodeDemographicsAnalyzer

MIGRATION_SERIALIZATION_PATH = os.path.abspath(os.path.join(current_directory, "08_write_file_migration", "outputs"))
try:
    migration_random_sim_id = os.listdir(MIGRATION_SERIALIZATION_PATH)[-1]
    MIGRATION_SERIALIZATION_PATH = os.path.join(MIGRATION_SERIALIZATION_PATH, migration_random_sim_id)
except Exception:
    raise FileNotFoundError("Can't find serialization file from previous run, please make sure 08_write_file_migration"
                            " succeeded.")

EXPERIMENT_NAME = 'Generic serialization 09 read files migration'
DTK_SERIALIZATION_FILENAME = "state-00050.dtk"
DTK_MIGRATION_FILENAME = "LocalMigration_3_Nodes.bin"

CHANNELS_TOLERANCE = {'Statistical Population': 1,
                      'Infectious Population': 0.05,
                      'Waning Population': 0.05,
                      'New Infections': 50,
                      'Symptomatic Population': 100}

NODE_COLUMNS_TOLERANCE = {'NumIndividuals': 30,
                          'NumInfected': 40}

if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # Create the experiment from input files
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication.exe"),
                               config_path=os.path.join(INPUT_PATH, 'config.json'),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=os.path.join(INPUT_PATH, "3nodes_demographics.json"))

    # Add the serialization files to the collection
    filter_name_s = partial(file_name_is, filenames=[DTK_SERIALIZATION_FILENAME])
    task.common_assets.add_directory(assets_directory=MIGRATION_SERIALIZATION_PATH, filters=[filter_name_s])

    # Enable migration and Add the migration files
    task.migrations.update_migration_pattern(MigrationPattern.RANDOM_WALK_DIFFUSION, Enable_Migration_Heterogeneity=1)
    task.migrations.add_migration_from_file(MigrationTypes.LOCAL,
                                            os.path.join(INPUT_PATH, DTK_LOCAL_MIGRATION_FILENAME),
                                            X_LOCAL_MIGRATION)
    task.migrations.add_migration_from_file(MigrationTypes.REGIONAL,
                                            os.path.join(INPUT_PATH, DTK_REGIONAL_MIGRATION_FILENAME),
                                            X_REGIONAL_MIGRATION)

    # Add the DLLs to the collection
    task.reporters.add_dll_folder(os.path.join("..", "custom_reports", "reporter_plugins", "Windows"))
    task.reporters.read_custom_reports_file(os.path.join("..", "custom_reports", "custom_reports.json"))

    # Update parameters and setup serialization
    config_update_params(task)

    add_serialization_timesteps(task, timesteps=[LAST_SERIALIZATION_DAY],
                                end_at_final=False, use_absolute_times=True)
    load_serialized_population(task, population_path="Assets",
                               population_filenames=[DTK_SERIALIZATION_FILENAME])
    task.update_parameters({
        "Start_Time": PRE_SERIALIZATION_DAY,
        "Simulation_Duration": SIMULATION_DURATION - PRE_SERIALIZATION_DAY,
        "Custom_Reports_Filename": "custom_reports.json"
    })

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
    pre_exp = platform.get_parent(migration_random_sim_id, ItemType.SIMULATION)

    # Run the timeseries analyzer
    print(f"Running TimeseriesAnalyzer with experiment id: {experiment.id} and {pre_exp.id}:\n")

    analyzers_nd = NodeDemographicsAnalyzer()
    am_nd = AnalyzeManager(platform=platform)
    am_nd.add_analyzer(analyzers_nd)
    am_nd.add_item(experiment)
    am_nd.add_item(pre_exp)
    am_nd.analyze()

    analyzers_nd.interpret_results(NODE_COLUMNS_TOLERANCE)

    analyzers_ts = TimeseriesAnalyzer()
    am_ts = AnalyzeManager(platform=platform)
    am_ts.add_analyzer(analyzers_ts)
    am_ts.add_item(experiment)
    am_ts.add_item(pre_exp)
    am_ts.analyze()

    analyzers_ts.interpret_results(CHANNELS_TOLERANCE)

    print("Downloading dtk serialization files from Comps:\n")

    filenames = ['output/InsetChart.json',
                 'output/ReportHumanMigrationTracking.csv',
                 'output/ReportNodeDemographics.csv',
                 f"output/state-{str(LAST_SERIALIZATION_DAY - PRE_SERIALIZATION_DAY).zfill(5)}.dtk"]

    # Cleanup the outptus if already present
    output_path = 'outputs'
    del_folder(output_path)

    analyzers_download = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am_download = AnalyzeManager(platform=platform)
    am_download.add_analyzer(analyzers_download)
    am_download.add_item(experiment)
    am_download.analyze()
