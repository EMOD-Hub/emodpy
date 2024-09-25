"""
        This file demonstrates how to create experiment/simulations with Eradication.exe from github url
"""
import os
import sys

from idmtools.entities.experiment import Experiment

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from emodpy.utils import get_github_eradication_url, EradicationPlatformExtension
from examples.config_update_parameters import config_update_params

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "emod_demographics", "inputs")

sim_duration = 10  # in years
num_seeds = 5

expname = os.path.split(sys.argv[0])[1]  # expname will be file name

if __name__ == "__main__":
    with Platform('COMPS2') as platform:
        task = EMODTask.from_files(
            config_path=os.path.join(INPUT_PATH, "config.json"),
            campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
            demographics_paths=os.path.join(INPUT_PATH, "demographics.json"),
            # set eradication to github exe url
            # bamboo can be used here as well
            eradication_path=get_github_eradication_url("2.20.0", EradicationPlatformExtension.Windows))

        # Update bunch of config parameters
        config_update_params(task)
        task.set_parameter("Config_Name", "test config")
        task.set_parameter("Enable_Susceptibility_Scaling", 1)
        task.set_parameter("Susceptibility_Scaling_Type", "LOG_LINEAR_FUNCTION_OF_TIME")
        task.set_parameter("Number_Basestrains", 1)
        task.set_parameter("Number_Substrains", 256)
        task.set_parameter("Susceptibility_Scaling_Rate", 1.58)

        # Add serialization parameters
        timesteps = [sim_duration * 365]
        add_serialization_timesteps(task=task, timesteps=timesteps,
                                    end_at_final=False, use_absolute_times=False)

        # Create SimulationBuilder
        builder = SimulationBuilder()
        # Add sweep parameter to builder
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
        # Add another sweep parameter to builder
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Base_Infectivity"), [0.6, 1.0, 1.5, 2.0])

        # Create experiment from template
        experiment = Experiment.from_builder(builder, base_task=task, name=expname)
        # run and wait to finish
        experiment.run(wait_until_done=True)
        experiment.print()

        # use system status as the exit code
        sys.exit(0 if experiment.succeeded else -1)
