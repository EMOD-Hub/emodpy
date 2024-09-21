import os
import json
from functools import partial
from idmtools.assets import Asset, AssetCollection
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from emodpy.emod_task import EMODTask
from emodpy.defaults import EMODSir
from examples.serialization.globals import BIN_PATH
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import \
    RequirementsToAssetCollection
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

INPUT_PATH = os.path.join('..', 'emod_model', 'inputs')
PARAM_PATH = os.path.abspath('param_dict.json')


# Function used to set config parameter and also add file to simulation
def param_update(simulation, param, value):
    simulation.task.transient_assets.add_asset(Asset(filename="idxStrFile.txt", content='{:05d}'.format(value)))
    return simulation.task.set_parameter(param, value)


# Function specially set parameter Run_Number
set_Run_Number = partial(param_update, param="Run_Number")

# Get experiment parameters from json file
with open(PARAM_PATH) as f:
    param_dict = json.load(f)
exp_name = param_dict['expName']
nSims = param_dict['nSims']

# Display exp_name and nSims
print('exp_name: ', exp_name)
print('nSims: ', nSims)
# Create a platform
# Show how to dynamically set priority and node_group
platform = Platform('SLURM')
pl = RequirementsToAssetCollection(platform, requirements_path='./requirements.txt')


# create EMODTask from default
task = EMODTask.from_default(default=EMODSir(),
                             eradication_path=os.path.join(BIN_PATH, "Eradication"))
# Add the parameters dictionary as an asset
param_asset = Asset(absolute_path=PARAM_PATH)
task.common_assets.add_asset(param_asset)

# Add more asset from a directory
assets_dir = 'Assets'
task.common_assets.add_directory(assets_directory=assets_dir)
task.is_linux = True
# set campaign to None to not sending any campaign to comps since we are going to override it later with
# dtk-pre-process, This is import step in COMPS2
task.campaign = None

# Need set this flag to add python_script_path to command argument by EMODTask
# Set to True to make dtk_pre_process.py to run as pre-process
task.use_embedded_python = True

# Load dtk_pre_process.py to COMPS Assets/python folder
dtk_pre_process_asset = Asset(os.path.join(INPUT_PATH, "dtk_pre_process.py"), relative_path='python')
task.common_assets.add_asset(dtk_pre_process_asset)

# Load campaign_template.json to simulation which used by dtk_pre_process.py
campaign_template_asset = Asset(os.path.join(INPUT_PATH, "campaign_template.json"))
task.transient_assets.add_asset(campaign_template_asset)

# Create simulation sweep with builder
builder = SimulationBuilder()
builder.add_sweep_definition(set_Run_Number, range(nSims))

# Create an experiment from builder
experiment = Experiment.from_builder(builder, task, name=exp_name)
other_assets = AssetCollection.from_id(pl.run())
experiment.assets.add_assets(other_assets)
# Run experiment
platform.run_items(experiment)

# Wait experiment to finish
platform.wait_till_done(experiment)

# Check result
if not experiment.succeeded:
    print(f"Experiment {experiment.uid} failed.\n")
    exit()

print(f"Experiment {experiment.uid} succeeded.")

# Save experiment id to file
with open('COMPS_ID', 'w') as fd:
    fd.write(experiment.uid.hex)
print()
print(experiment.uid.hex)
