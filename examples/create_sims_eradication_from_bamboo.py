"""
    This file demonstrates how to create experiment/simulations with Eradication.exe from bamboo url
"""
import os
import sys

from idmtools.entities.experiment import Experiment

from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.templated_simulation import TemplatedSimulations

from emodpy.emod_task import EMODTask
from emodpy.generic.serialization import add_serialization_timesteps
from emodpy.utils import EradicationBambooBuilds, download_latest_bamboo, bamboo_api_login, download_from_url
from examples.config_update_parameters import config_update_params

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "emod_demographics", "inputs")

sim_duration = 2  # in years
num_seeds = 2

expname = os.path.split(sys.argv[0])[1]  # expname will be file name


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


# case1: download Eradication.exe to current local dir with default filename Eradication.exe
def win_output_path1():
    local_eradication_path = download_latest_bamboo(EradicationBambooBuilds.GENERIC_WIN)
    return local_eradication_path


# case2: download Eradication.exr to current local dir with file name given
def win_output_path2():
    local_eradication_path = download_latest_bamboo(EradicationBambooBuilds.GENERIC_WIN, "Eradication.exe")
    return local_eradication_path


# case3: download Eradication.exe to relative path - "outputs" dir with delimiter '/'
def win_output_path3():
    local_eradication_path = download_latest_bamboo(EradicationBambooBuilds.GENERIC_WIN, "outputs/Eradication.exe")
    return local_eradication_path


# case4: download Eradication.exe to relative path - "outputs" dir with delimiter '\'
def win_output_path4():
    local_eradication_path = download_latest_bamboo(EradicationBambooBuilds.GENERIC_WIN, r"outputs\Eradication.exe")
    return local_eradication_path


# case5: download Eradication.exe to absolutely path
def win_output_path5():
    local_eradication_path = download_latest_bamboo(EradicationBambooBuilds.GENERIC_WIN,
                                                    "C:\github\emodpy\examples\outputs\Eradication.exe")
    return local_eradication_path


# case 6: download Eradication.exe directly from url
def win_output_path6():
    # example bamboo url for Eradication.exe
    url = "http://idm-bamboo:8085/artifact/DTKGENCI-SCONSWINGEN/shared/build-21/Eradication.exe/build/x64/Release/Eradication/Eradication.exe"
    local_eradication_path = download_from_url(url, "outputs/Eradication.exe")
    return local_eradication_path


# case7: download Linux Eradication directly from url
def win_output_path7():
    # example bamboo url for Eradication
    url = "http://idm-bamboo:8085/artifact/DTKGENCI-SCONSRELLNX/shared/build-19/Eradication.exe/build/x64/Release/Eradication/Eradication"
    local_eradication_path = download_from_url(url, "outputs/Eradication")
    return local_eradication_path


if __name__ == "__main__":

    platform = Platform('COMPS2')

    bamboo_api_login()
    # get eradication.exe from github
    available_funcs = (win_output_path1, win_output_path2, win_output_path3, win_output_path4, win_output_path5,
                       win_output_path6)

    # try different paths to save Eradication.exe to local path
    for eradication_path_func in available_funcs:
        # For linux, uncomment following line, CI_DTK
        # eradication_path = download_latest_bamboo(EradicationBambooBuilds.CI_GENERICLINUX, "outputs/Eradication")
        eradication_path = eradication_path_func()
        task = EMODTask.from_files(config_path=os.path.join(INPUT_PATH, "config.json"),
                                   campaign_path=os.path.join(INPUT_PATH, "campaign.json"),
                                   demographics_paths=os.path.join(INPUT_PATH, "demographics.json"),
                                   eradication_path=eradication_path)

        # Update bunch of config parameters
        config_update_params(task)
        task.set_parameter("Base_Infectivity_Distribution", "CONSTANT_DISTRIBUTION")
        task.set_parameter("Base_Infectivity_Constant", 0.2)

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
        # Add builder to templated simulations
        ts.add_builder(builder)

        # Create experiment from template
        experiment = Experiment.from_template(ts, name=expname)

        # The last step is to call run() on the ExperimentManager to run the simulations.
        platform.run_items(experiment)
        platform.wait_till_done(experiment)

        # use system status as the exit code
        if not experiment.succeeded:
            sys.exit(-1)
