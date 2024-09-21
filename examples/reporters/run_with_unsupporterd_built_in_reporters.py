"""
This file demonstrates how to create experiment/simulations using a built-in reporter that is not yet supported
 by the system.
 
 Please note that the built-in reporters are an EXPERIMENTAL feature currently only on recent ongoing branches.
 This example will generate the correct `custom_reports.json` to work with those but the executable provided 
 may not output any results for now.
 
"""
import os
import sys

from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_file import MigrationTypes
from emodpy.emod_task import EMODTask
from emodpy.reporters import BuiltInReporter, dataclass

current_directory = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(current_directory, "inputs")
EXPERIMENT_NAME = os.path.split(sys.argv[0])[1]  # expname will be file name
ERADICATION_PATH = os.path.join(current_directory, "..", "inputs", "bin", "Eradication.exe")


@dataclass
class MyUnsuportedBuiltInReporter(BuiltInReporter):
    """
    This class will add support for the ReportHumanMigrationTracking built-in reporter without relying on
    emodpy to provide implementation.
    You need to only modify 2 fields to implement a BuiltInReporter:
    - `class_name`: The reporter class name
    - `parameters`: parameters to add when creating the `custom_reports.json`
    """
    class_name: str = "ReportHumanMigrationTracking"
    # This particular reporting works without parameters, so we will not override the default parameters@dataclass


@dataclass
class ReportPluginAgeAtInfection(BuiltInReporter):
    """
    This class will add support for the ReportHumanMigrationTracking built-in reporter without relying on
    emodpy to provide implementation.
    You need to only modify 2 fields to implement a BuiltInReporter:
    - `class_name`: The reporter class name
    - `parameters`: parameters to add when creating the `custom_reports.json`
    """
    class_name: str = "ReportPluginAgeAtInfection"
    # This particular reporting works without parameters, so we will not override the default parameters


if __name__ == "__main__":
    # Create the platform
    platform = Platform('COMPS2')

    # Create EMODTask with the set of provided files
    task = EMODTask.from_default(default=EMODSir(), eradication_path=ERADICATION_PATH)

    # Add new demographics
    task.demographics.clear()
    task.demographics.add_demographics_from_file(os.path.join(INPUT_PATH, "3x3_demographics.json"))

    # Add some migrations
    task.migrations.add_migration_from_file(MigrationTypes.LOCAL, os.path.join(INPUT_PATH, "3x3_Age_Gender_Local.bin"))

    # Create a reporter
    reporter = MyUnsuportedBuiltInReporter()
    task.reporters.add_reporter(reporter)

    reporter = ReportPluginAgeAtInfection()
    task.reporters.add_reporter(reporter)

    print(task.reporters.json)

    # Create the experiment from task and run
    experiment = Experiment.from_task(task, name=EXPERIMENT_NAME)
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
