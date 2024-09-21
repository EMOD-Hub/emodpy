"""
        This file demonstrates how to create experiment/simulations in COMPS platform's SlurmStage environment
        Also demonstrates using TemplatedSimulations and SimulationBuilder to create simulations
        TODO: Need a Linux version of Kevin's Eradication version
        TODO: issue 97 custom_report class does not work for linux
"""
import os
import sys

from idmtools.entities.experiment import Experiment 
from idmtools.assets import Asset 
from idmtools.core.platform_factory import Platform 
from emodpy.emod_task import EMODTask 
from examples.dtk_generic_slurm.globals import ERADICATION_PATH, INPUT_PATH, MIGRATION_FILE_PATH, DTK_LOCAL_MIGRATION_FILENAME, X_LOCAL_MIGRATION, DTK_AIR_MIGRATION_FILENAME, X_AIR_MIGRATION, DLL_PATH 
from emodpy.emod_file import MigrationTypes, MigrationPattern

current_directory = os.path.dirname(os.path.realpath(__file__))

sim_duration = 10   # in years
num_seeds = 5

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


if __name__ == "__main__":
    # Define SLURM platform
    platform = Platform('SLURM', num_cores=6, node_group='idm_abcd')

    # Create EMODTask from files, cutom_reports.json and so files also loaded in this method
    task = EMODTask.from_files(
        eradication_path=ERADICATION_PATH,
        config_path=os.path.join(INPUT_PATH, "config.json"),
        campaign_path=os.path.join(INPUT_PATH, "baseline_campaign.json"),
        demographics_paths=[
            os.path.join(INPUT_PATH, "Nigeria_sample49_LGA_more_agegroups_uniform_demographics.json")
        ],
        custom_reports_path=os.path.join(INPUT_PATH, "custom_reports.json"),
        asset_path=INPUT_PATH
    )
    task.is_linux = True

    # add some common assets
    loadbalance_cores = Asset(absolute_path=os.path.join(INPUT_PATH, "loadbalance_6Cores.json"))
    task.common_assets.add_asset(loadbalance_cores)

    # load migration files, set migration pattern, and migration_heterogeneity
    task.migrations.update_migration_pattern(MigrationPattern.SINGLE_ROUND_TRIPS, Enable_Migration_Heterogeneity=0)
    task.migrations.add_migration_from_file(MigrationTypes.LOCAL,
                                            os.path.join(MIGRATION_FILE_PATH, DTK_LOCAL_MIGRATION_FILENAME),
                                            X_LOCAL_MIGRATION)
    task.migrations.add_migration_from_file(MigrationTypes.AIR,
                                            os.path.join(MIGRATION_FILE_PATH, DTK_AIR_MIGRATION_FILENAME),
                                            X_AIR_MIGRATION)

    # load local dll folder to task
    task.reporters.add_dll_folder(DLL_PATH)

    # if you want to create different report then what in custom_reports.json
    # Create a ReportAgeAtInfectionHistogram
    # report = ReportPluginAgeAtInfectionHistogram()
    # task.reporters.add_reporter(report)

    # Set parameters
    task.set_parameter("Base_Infectivity_Distribution", "CONSTANT_DISTRIBUTION")
    task.set_parameter("Base_Infectivity_Constant", 0.1)
    # task.set_parameter("Birth_Rate_Time_Dependence", "None")

    # Create experiment from task
    experiment = Experiment.from_task(task, name=expname)

    # The last step is to call run() on the ExperimentManager to run the simulations.
    platform.run_items(experiment)
    platform.wait_till_done(experiment)
