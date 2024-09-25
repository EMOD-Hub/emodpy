"""
    This example demonstrates how to use CommandTask to do dtk_post_process which directly
    add --python-script-path to CommandTask's command parameter
"""

import json
import os
import sys
from functools import partial
from idmtools.assets import Asset
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.command_task import CommandTask
from idmtools.entities.experiment import Experiment

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "..", "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "inputs")

DEFAULT_CONFIG_PATH = os.path.join(INPUT_PATH, "config.json")
DEFAULT_CAMPAIGN_PATH = os.path.join(INPUT_PATH, "campaign.json")
DEFAULT_DEMO_PATH = os.path.join(INPUT_PATH, "demographics.json")

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def generate_experiment():
    # command to run in comps
    command = "Assets/Eradication.exe --config config.json --input-path ./Assets --python-script-path Assets/python"

    # create commandtask
    task = CommandTask(command=command)

    # update some config parameter values from original config file
    with open(DEFAULT_CONFIG_PATH, 'r') as cin:
        task.config = json.load(cin)
        # Need to update Campaign_Filename value to a new location from default value
        task.config["parameters"]["Campaign_Filename"] = "Assets/" + task.config["parameters"]["Campaign_Filename"]
        # we can also update any value in config.json
        task.config["parameters"]["Enable_Immunity"] = 1

    # call back function to actually doing update the config which is called by below asset_hooks
    def save_config(task):
        return Asset(filename='config.json', content=json.dumps(task.config))

    # add config to simulation assets with gather_transient_asset_hooks call back function
    task.gather_transient_asset_hooks.append(save_config)
    # If you want to add config to current sim dir instead of assets dir, doing following
    # task.transient_assets.add_asset(save_config(task))

    def update_param(simulation, param, value):
        simulation.task.config[param] = value
        return {param: value}

    # add Eradication.exe as experiment asset ie.to simulations's Asset dir
    eradication_asset = Asset(absolute_path=os.path.join(BIN_PATH, "Eradication.exe"))
    task.common_assets.add_asset(eradication_asset)

    # add campaign.json files to experiment level ie. to simulations's Asset dir
    campaign_asset = Asset(absolute_path=DEFAULT_CAMPAIGN_PATH)
    task.common_assets.add_asset(campaign_asset)

    # add demographic.json files to experiment level ie. to simulations's Asset dir
    demo_asset = Asset(absolute_path=DEFAULT_DEMO_PATH)
    task.common_assets.add_asset(demo_asset)

    emod_post_process_asset = Asset(os.path.join(INPUT_PATH, "dtk_post_process.py"), relative_path="python")
    task.common_assets.add_asset(emod_post_process_asset)

    # sweep Run_Number parameter
    builder = SimulationBuilder()
    set_run_number = partial(update_param, param="Run_Number")
    builder.add_sweep_definition(set_run_number, range(0, 2))
    # create experiment from builder
    exp = Experiment.from_builder(builder, task, name=expname)

    platform.run_items(exp)
    platform.wait_till_done(exp)
    return exp


if __name__ == "__main__":
    platform = Platform('COMPS2')
    experiment = generate_experiment()
    sys.exit(0 if experiment.succeeded else -1)
