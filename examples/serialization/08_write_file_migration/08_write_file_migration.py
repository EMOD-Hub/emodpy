import sys
import os

from idmtools.assets import Asset
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from emodpy.emod_file import MigrationTypes, MigrationPattern

from examples.serialization.globals import BIN_PATH, INPUT_PATH, LAST_SERIALIZATION_DAY, \
    config_update_params, SIMULATION_DURATION, del_folder, DTK_LOCAL_MIGRATION_FILENAME, X_LOCAL_MIGRATION, \
    DTK_REGIONAL_MIGRATION_FILENAME, X_REGIONAL_MIGRATION, START_DAY

EXPERIMENT_NAME = 'Generic serialization 08 writes files migration'
DTK_MIGRATION_FILENAME = "LocalMigration_3_Nodes.bin"

if __name__ == "__main__":

    # Create the platform
    platform = Platform('COMPS2')

    # Create an experiment based on input files
    task = EMODTask.from_files(eradication_path=os.path.join(BIN_PATH, "Eradication.exe"),
                               config_path=os.path.join(INPUT_PATH, 'config.json'),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=os.path.join(INPUT_PATH, "3nodes_demographics.json"))

    # Enable migration and Add the migration files
    task.migrations.add_migration_from_file(MigrationTypes.LOCAL,
                                         os.path.join(INPUT_PATH, DTK_LOCAL_MIGRATION_FILENAME),
                                         X_LOCAL_MIGRATION)
    task.migrations.add_migration_from_file(MigrationTypes.REGIONAL,
                                         os.path.join(INPUT_PATH, DTK_REGIONAL_MIGRATION_FILENAME),
                                         X_REGIONAL_MIGRATION)
    task.migrations.update_migration_pattern(MigrationPattern.RANDOM_WALK_DIFFUSION, Enable_Migration_Heterogeneity=1)

    # Add the DLLs to the collection
    task.reporters.add_dll_folder(os.path.join("..", "custom_reports", "reporter_plugins", "Windows"))
    task.reporters.read_custom_reports_file(os.path.join("..", "custom_reports", "custom_reports.json"))

    # Update parameters (adding migration) and setup serialization
    config_update_params(task)
    serialization_timesteps = list(range(10, LAST_SERIALIZATION_DAY + 20, 20))
    add_serialization_timesteps(task, timesteps=serialization_timesteps,
                                end_at_final=False, use_absolute_times=False)
    task.update_parameters({
        "Start_Time": START_DAY,
        "Simulation_Duration": SIMULATION_DURATION
        # "Custom_Reports_Filename": "custom_reports.json",
        # "Enable_Local_Migration": 1,
        # "Enable_Regional_Migration": 1
    })

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    if not experiment.succeeded:
        print(f"Experiment {experiment.id} failed.\n")
        exit()
    print(f"Experiment {experiment.id} succeeded.\nDownloading dtk serialization files from Comps:\n")


    # Create the filenames
    filenames = ['output/InsetChart.json',
                 'output/ReportHumanMigrationTracking.csv',
                 'output/ReportNodeDemographics.csv']
    for serialization_timestep in serialization_timesteps:
        filenames.append("output/state-" + str(serialization_timestep).zfill(5) + ".dtk")

    # Remove the outputs if already present
    output_path = 'outputs'
    del_folder(output_path)

    download_analyzer = DownloadAnalyzer(filenames=filenames, output_path=output_path)
    am = AnalyzeManager(platform=platform)
    am.add_analyzer(download_analyzer)
    am.add_item(experiment)
    am.analyze()
