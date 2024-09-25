import os  # a lot of os.path.join-ing
import json  # for when we do config building locally
from functools import partial  # for setting Run_Number. In Jonathan Future World, Run_Number is set by dtk_pre_proc based on generic param_sweep_value...
import shutil

# idmtools ...
from idmtools.assets import Asset, AssetCollection  #
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import RequirementsToAssetCollection

# emodpy
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds, download_latest_bamboo, bamboo_api_login, download_from_url
from emodpy import bamboo

# emodapi
import emod_api.schema.get_schema as get_schema
import emod_api.config.default_from_schema as default

from emod_api.schema_to_class import ReadOnlyDict

import params
import manifest

# ****************************************************************
# Features to support:
#
#  Read experiment info from a json file
#  Add Eradication.exe as an asset (Experiment level)
#  Add Custom file as an asset (Simulation level)
#  Add the local asset directory to the task
#  Use builder to sweep simulations
#  How to run dtk_pre_process.py as pre-process
#  Save experiment info to file
# ****************************************************************


# Function used to set config parameter and also add file to simulation
def param_update(simulation, param, value):
    simulation.task.transient_assets.add_asset(Asset(filename="idxStrFile.txt", content="{:05d}".format(value)))
    return simulation.task.set_parameter(param, value)

def print_params():
    # Display exp_name and nSims
    # TBD: Just loop through them
    print("exp_name: ", params.exp_name)
    print("nSims: ", params.nSims)

def general_sim(erad_path, ep4_scripts):
    """
    do_the_things -- which will be renamed -- is designed to be a parameterized version of the sequence of things we do 
    every time we run an emod experiment. 
    """
    print_params()

    # Create a platform
    # Show how to dynamically set priority and node_group
    platform = Platform("SLURM") 
    pl = RequirementsToAssetCollection(platform, requirements_path=manifest.requirements)

    # create EMODTask 
    # demog_path = os.path.join(input_path, demog_file)  # use existing file for now
    print("Creating EMODTask (from files)...")
    task = EMODTask.from_files(config_path=None, eradication_path=erad_path, ep4_path=manifest.ep4_path, demographics_paths=manifest.demog_path)

    print("Adding asset dir...")
    task.common_assets.add_directory(assets_directory=manifest.assets_input_dir)

    # Set task.campaign to None to not send any campaign to comps since we are going to override it later with
    # dtk-pre-process.
    print("Adding local assets (py scripts mainly)...")

    for asset in ep4_scripts:
        pathed_asset = Asset(os.path.join(manifest.ep4_path, asset), relative_path="python")
        task.common_assets.add_asset(pathed_asset)

    # task.common_assets.add_asset(manifest.demog_path)  # prefer to get from symlinked MyAssets grumble grumble

    # Create simulation sweep with builder
    builder = SimulationBuilder()
    # Function specially set parameter Run_Number
    set_Run_Number = partial(param_update, param="Run_Number")
    builder.add_sweep_definition(set_Run_Number, range(params.nSims))

    # Create an experiment from builder
    experiment = Experiment.from_builder(builder, task, name=params.exp_name)
    other_assets = AssetCollection.from_id(pl.run())
    experiment.assets.add_assets(other_assets)

    print("Run experiment...")
    platform.run_items(experiment)

    print("Wait experiment to finish...")
    platform.wait_till_done(experiment)

    # Check result
    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")

    # Save experiment id to file
    with open("COMPS_ID", "w") as fd:
        fd.write(experiment.uid.hex)
    print()
    print(experiment.uid.hex)

    """
    for sim in filter(lambda x: x.id == "Hello Calculon", experiment.simulations):
        po = sim.get_platform_object()
        simdb = po.retrieve_output_files(paths=["simulation_events.db"])
    """

def run_test(erad_path):
    general_sim(erad_path, manifest.my_ep4_assets)

if __name__ == "__main__":
    # TBD: user should be allowed to specify (override default) erad_path and input_path from command line
    files = bamboo.get_bamboo_files(os.name)
    print(files)
    erad_path = files[0]
    # on windows copy the downloaded schema.json to the MyAssets coz this particular OS has never been updated to support symlinks properly
    if os.name == "nt":
        if os.path.exists(manifest.schema_asset_path):
            os.remove(manifest.schema_asset_path)
        shutil.copy(files[1], manifest.schema_asset_path)

    run_test(erad_path)
