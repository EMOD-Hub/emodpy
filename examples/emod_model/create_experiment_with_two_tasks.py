"""
    This example demonstrates how to create experiment with 2 different tasks, steps are:
    1) create one task with simulations with set of config, campaign,tag, sweep parameters
    2) create second task with another set of simulations with different parameters
    3) add each task to TemplatedSimulations
    4) add each TemplatedSimulations to a list
    5) add the list to experiment.simulations
    5) run experiment with platform
"""
import os
import sys
from functools import partial
from typing import Any, Dict

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "..", "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "inputs")

expname = os.path.split(sys.argv[0])[1]  # expname will be file name

platform=Platform('COMPS2')


def build_task():
    t = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                            campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                            eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    t.demographics.add_demographics_from_file(
        os.path.join(INPUT_PATH, "demo.json"))

    return t


def param_update(simulation: Simulation, param: str, value: Any) -> Dict[str, Any]:
    return simulation.task.set_parameter(param, value)


task = build_task()
ts1 = TemplatedSimulations(base_task=task)
builder = SimulationBuilder()

set_tag = partial(param_update, param="tag")
builder.add_sweep_definition(set_tag, "abc")

set_run_number = partial(param_update, param="Run_Number")
builder.add_sweep_definition(set_run_number, range(3))
ts1.add_builder(builder)

task2 = EMODTask.from_default(default=EMODSir(), eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))
ts2 = TemplatedSimulations(base_task=task2)
builder2 = SimulationBuilder()
builder2.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(4))
ts2.add_builder(builder2)

experiment = Experiment(name=expname)
# create mixed experiment from two templates
experiment.simulations = list(ts1) + list(ts2)

platform.run_items(experiment)
platform.wait_till_done(experiment)
# use system status as the exit code
sys.exit(0 if experiment.succeeded else -1)
