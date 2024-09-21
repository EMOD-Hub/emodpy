import os
import sys

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
INPUT_PATH = os.path.join(CURRENT_DIRECTORY, "inputs")
BIN_PATH = os.path.join("..", "inputs", "bin")

sim_duration = 10  # in years
num_seeds = 5

demo_files = [os.path.join(INPUT_PATH, "demographics.json"),
              os.path.join(INPUT_PATH, "PFA_rates_overlay.json"),
              os.path.join(INPUT_PATH, "pfa_simple.json"),
              os.path.join(INPUT_PATH, "uniform_demographics.json")]


def set_simulation_seed(simulation, value):
    return simulation.task.set_parameter("Run_Number", value)


def experiment_from_files() -> 'EMODTask':
    """
        This function demonstrates the creation of an experiment from EMODTask with a set of file.
        - Eradication_Path: The path to the executable to run
        - config_path/campaign_path: the paths for config and campaign files,
        automatically loaded to the experiment's base simulation
        - demographics_paths: The demographics files loaded to the experiment demographics

        Notes:
            Because the demographics files are loaded in the experiment, they will be put in the experiment's
            asset collection. All simulations created from this experiment will automatically include those demographics.
            User is free to remove/edit/add new demographics but the ones set in the asset collection are immutable and
            can only be removed.
    """
    task = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               demographics_paths=os.path.join(INPUT_PATH, "demographics.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # set task name
    task.__setattr__('name', 'experiment_from_files')

    return task


def demographics_on_experiment() -> 'EMODTask':
    """
        This function demonstrates the creation of an Experiment from EMODTask from files.
        We are then adding the demographics files to the experiment demographics.

        Notes:
            Because the demographics files are loaded in the experiment, they will be put in the experiment's
            asset collection. All simulations created from this experiment will automatically include those demographics.
            User is free to remove/edit/add new demographics but the ones set in the asset collection are immutable and
            can only be removed.
    """

    task = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                               campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                               eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    for demog in demo_files:
        task.demographics.add_demographics_from_file(demog)

    # set task name
    task.__setattr__('name', 'demographics_on_experiment')

    return task


def demographics_on_simulation() -> 'EMODTask':
    """
        This function demonstrates the creation of an EMODTask from defaults.
        then override config and campaign files from local
        We are then adding the demographics files to the simulation demographics.

        Notes:
            Because the demographics files are loaded in the simulation, they will not be part of the experiment's
            asset collection but will be dumped in the simulation working directory.
            Because they are attached directly to the simulation, the user can modify them freely.
        """

    # Case: load demographics from experiment
    task = EMODTask.from_default(default=EMODSir(),
                                 eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))

    # remove default demographics from task
    task.demographics.clear()

    # load custom config.json and campaign.json to override default one
    task.load_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                    campaign_path=os.path.join(INPUT_PATH, "campaign.json"))

    # add custom demographics files to simulation
    for demog in demo_files:
        task.simulation_demographics.add_demographics_from_file(demog)

    # set task name
    task.__setattr__('name', 'demographics_on_simulation')

    return task



if __name__ == "__main__":
    platform = Platform('COMPS2')

    # Gather all the functions available for experiment creation
    available_funcs = (experiment_from_files, demographics_on_experiment, demographics_on_simulation)
    # For each of them create a sweep on the seed and run
    for experiment_func in available_funcs:
        t = experiment_func()
        builder = SimulationBuilder()
        builder.add_sweep_definition(set_simulation_seed, range(num_seeds))
        # Create the experiment form builder and run
        experiment = Experiment.from_builder(builder, base_task=t, name=os.path.split(sys.argv[0])[1] + "-" + t.name)
        platform.run_items(experiment)
        platform.wait_till_done(experiment)
