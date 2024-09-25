"""
    This example demonstrates how to create serialization simulations
    then create simulations by loading a serialized population from the previous simulation
"""
import os
import sys
from functools import partial

from idmtools.assets import Asset
from idmtools.builders import SweepArm, ArmType, ArmSimulationBuilder, SimulationBuilder
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_test.utils.comps import sims_from_experiment, get_simulation_path

from emodpy.defaults import EMODSir
from emodpy.emod_campaign import EMODCampaign
from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps, load_serialized_population
from examples.config_update_parameters import config_update_params

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "emod_demographics", "inputs")

sim_duration = 10  # in years
num_seeds = 5


def create_task():
    # Create EMODTask with default EMODSir config/campaign/demographic values, and load Eradication.exe from local dir
    task = EMODTask.from_default(default=EMODSir(),
                                 eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # Replace the default campaign
    task.campaign = EMODCampaign.load_from_file(os.path.join(INPUT_PATH, "campaign.json"))

    # Remove default demographic files from EMODSir's config Demographics_Filenames
    task.demographics.clear()
    demo_file = os.path.join(INPUT_PATH, "demographics.json")

    # Add new demographic file from local to experiment level(Assets dir in comps's)
    task.demographics.add_demographics_from_file(demo_file)
    return task


if __name__ == "__main__":
    platform = Platform('COMPS2')

    task = create_task()

    # Update bunch of config parameters
    config_update_params(task)
    task.set_parameter("Config_Name", "create sterilize config")
    task.set_parameter("Enable_Susceptibility_Scaling", 0)
    timesteps = [sim_duration * 365]
    add_serialization_timesteps(task=task, timesteps=timesteps,
                                end_at_final=True, use_absolute_times=False)
    # Sweep parameters
    # Define a SweepArm type which doing a*b
    arm = SweepArm(type=ArmType.cross)
    # Now add our sweep on a list using EMODTask's partial function
    arm.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(num_seeds))
    # Add another our sweep on a list using EMODTask's partial function
    arm.add_sweep_definition(EMODTask.set_parameter_partial("x_Temporary_Larval_Habitat"), [0.1, 0.2])
    builder = ArmSimulationBuilder()
    # Add arm to builder
    builder.add_arm(arm)

    # Now we can create Experiment from_builder()
    expname = 'create_serialization_experiment'
    experiment = Experiment.from_builder(builder, base_task=task, name=expname)
    # The last step is to call run() on the ExperimentManager to run the simulations.
    platform.run_items(experiment)
    platform.wait_till_done(experiment)

    # Step2: Create new experiment and simulations by reload Serialized_Population_Path from previous simulation
    # First get previous serialized file path
    # get comps experiment
    comps_exp = platform.get_item(item_id=experiment.id, item_type=ItemType.EXPERIMENT)
    # get comps simulations with hpc_jobs configuration block
    comps_sims = sims_from_experiment(comps_exp)
    # get serialization file path from previous simulation
    serialized_file_path = [get_simulation_path(sim) for sim in comps_sims][0]

    # create new experiment
    expname2 = 'reload_serialization_experiment'
    task = create_task()

    config_update_params(task)
    task.set_parameter("Config_Name", "reload config")
    timesteps = [sim_duration * 365]
    add_serialization_timesteps(task=task, timesteps=timesteps,
                                end_at_final=False, use_absolute_times=False)
    # set bunch of configs
    task.set_parameter("Enable_Immunity", 0)
    task.set_parameter("Config_Name", "reloading sim")
    task.set_parameter("Simulation_Duration", sim_duration * 365)
    task.set_parameter("Serialization_Time_Steps", [])  # this will control not to generate serialized file

    # load a serialized population from the previous simulation's output/state-03650.dtk file path
    load_serialized_population(task=task, population_path=os.path.join(serialized_file_path, 'output'),
                               population_filenames=['state-0' + str(sim_duration * 365) + '.dtk'])


    def update_param(simulation, param, value):
        simulation.task.config[param] = value
        return {param: value}

    # sweep parameters
    builder = SimulationBuilder()
    # Now add our sweep on a list
    set_run_number = partial(update_param, param="Run_Number")
    builder.add_sweep_definition(set_run_number, range(0, 2))

    # Now we can create our Experiment with from_builder()
    experiment2 = Experiment.from_builder(builder, base_task=task, name=expname2)
    platform.run_items(experiment2)
    platform.wait_till_done(experiment2)
    sys.exit(0 if (experiment.succeeded and experiment2.succeeded) else -1)
