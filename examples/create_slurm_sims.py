"""
        This file demonstrates how to create experiment/simulations in COMPS platform's SlurmStage environment
        Also demonstrates using TemplatedSimulations and SimulationBuilder to create simulations
"""
import os
import sys

from idmtools.entities.experiment import Experiment

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from examples.config_update_parameters import config_update_params

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "emod_demographics", "inputs")

sim_duration = 10   # in years
num_seeds = 5

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


if __name__ == "__main__":
    # Define SLURM platform
    platform = Platform('SLURM')

    # Create EMODTask with default EMODSir config/campaign/demographic values , and Eradication file from local dir
    task = EMODTask.from_default(default=EMODSir(), eradication_path=os.path.join(BIN_PATH, "Eradication"))

    # Remove default demographic files from EMODSir's config Demographics_Filenames
    task.demographics.clear()
    demo_file = os.path.join(INPUT_PATH, "demographics.json")

    # Add new demographic file from local to experiment level(Assets dir in comps's)
    task.demographics.add_demographics_from_file(demo_file)

    # Update bunch of config parameters
    config_update_params(task)
    task.set_parameter("Config_Name", "test slurm sim")
    task.set_parameter("Enable_Susceptibility_Scaling", 2)

    # Add serialization parameters
    timesteps = [sim_duration * 365]
    add_serialization_timesteps(task=task, timesteps=timesteps,
                                end_at_final=False, use_absolute_times=False)

    # Create TemplatedSimulations with task
    ts = TemplatedSimulations(base_task=task)

    # Create SimulationBuilder
    builder = SimulationBuilder()
    # Add sweep parameter to builder
    builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
    # Add another sweep parameter to builder
    builder.add_sweep_definition(EMODTask.set_parameter_partial("x_Temporary_Larval_Habitat"), [0.1, 0.2])

    # Add builder to templated simulations
    ts.add_builder(builder)

    # Create experiment from template
    experiment = Experiment.from_template(ts, name=expname)

    # The last step is to call run() on the ExperimentManager to run the simulations.
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # use system status as the exit code
    sys.exit(0 if experiment.succeeded else -1)
