"""
    This example demonstrates how to do dtk_post_process through EMODTask
"""
import os
import sys

from idmtools.assets import Asset
from idmtools.entities.experiment import Experiment

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.emod_task import EMODTask
from examples.config_update_parameters import config_update_params

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "..", "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "inputs")

sim_duration = 10   # in years
num_seeds = 1

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


if __name__ == "__main__":
    # Define COMPS platform
    platform = Platform('COMPS2')
    task = EMODTask.from_files(config_path=os.path.join("inputs", "config.json"),
                               campaign_path=os.path.join("inputs", "campaign.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    task.demographics.add_demographics_from_file(
        os.path.join("inputs", "demo.json"))

    # Load dtk_post_process.py to COMPS Assets/python folder
    dtk_post_process_asset = Asset(os.path.join("inputs", "dtk_post_process.py"), relative_path='python')
    task.common_assets.add_asset(dtk_post_process_asset)

    # Update bunch of config parameters
    config_update_params(task)
    task.set_parameter("Config_Name", "test config")
    task.set_parameter("Enable_Susceptibility_Scaling", 1)

    # Create TemplatedSimulations with task
    ts = TemplatedSimulations(base_task=task)
    # Create SimulationBuilder
    builder = SimulationBuilder()
    # Add sweep parameter to builder
    builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
    # Add another sweep parameter to builder
    builder.add_sweep_definition(EMODTask.set_parameter_partial("Base_Infectivity"), [0.6, 1.0, 1.5, 2.0])
    # Add builder to simulations
    ts.add_builder(builder)

    # Create experiment from template
    experiment = Experiment.from_template(ts, name=expname)

    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
