#*******************************************************************************
#
# Python 3.6.0
#
#*******************************************************************************

import os, sys, json

from idmtools.assets                  import Asset, AssetCollection
from idmtools.builders                import SimulationBuilder
from idmtools.core.platform_factory   import Platform
from idmtools.entities.experiment     import Experiment
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection \
                                      import RequirementsToAssetCollection

from kf_emod_task import KF_EMODTask as EMODTask

# Constants
from examples.kurt_workflow.KF_Example.globals import ERADICATION_PATH, ASSETS_FOLDER

# ******************************************************************************

PATH_ASSET = os.path.abspath(ASSETS_FOLDER)
PATH_BIN   = os.path.abspath(ERADICATION_PATH)
PATH_PARAM = os.path.abspath('param_dict.json')



# Function for use in sweep builder
def sweep_func(simulation, simIdxVal):
  simIdxStr = '{:05d}'.format(simIdxVal)
  simulation.task.transient_assets.add_asset(Asset(filename = 'idxStrFile.txt',
                                                   content  = simIdxStr))

  return None



# Get experiment parameters from json file
with open(PATH_PARAM) as fid01:
  param_dict = json.load(fid01)
exp_name  = param_dict['expName']
nSims     = param_dict['nSims']
simIdxVec = param_dict['simIdx']



# Prepare the platform
sim_root_dir = os.path.join('$COMPS_PATH(USER)',exp_name)
plat_obj = Platform('COMPS',
                    endpoint        = 'https://comps2.idmod.org',
                    environment     = 'Bayesian',
                    priority        = 'Normal',
                    simulation_root = sim_root_dir,
                    node_group      = 'emod_abcd',
                    num_cores       = '1',
                    num_retries     = '0',
                    exclusive       = 'False',
                    max_threads     = 16,
                    sims_per_thread = 20,
                    max_local_sims  = 1)



# Build asset collection with python requirements
asset_builder = RequirementsToAssetCollection(plat_obj, pkg_list=['numpy==1.18.3'])
asset_id        = asset_builder.run()
commons       = AssetCollection.from_id(asset_id, platform=plat_obj)


# Create EMODTask
task_obj = EMODTask.from_files(eradication_path=PATH_BIN)
task_obj.use_embedded_python = True
task_obj.legacy_exe          = False
task_obj.campaign            = None
task_obj.common_assets       = commons

# Add the parameters dictionary to assets
param_asset = Asset(absolute_path=PATH_PARAM)
task_obj.common_assets.add_asset(param_asset)

# Add everything in the assets directory as assets
assets_dir = 'Assets'
task_obj.common_assets.add_directory(assets_directory=PATH_ASSET)



# Create simulation sweep with builder
build_obj = SimulationBuilder()
build_obj.add_sweep_definition(sweep_func, simIdxVec)

# Create an experiment from builder
exp_obj = Experiment.from_builder(build_obj, task_obj, name=exp_name)



# Run experiment
plat_obj.run_items(exp_obj)



# Save experiment id to file
with open('COMPS_ID', 'w') as fid01:
  fid01.write(exp_obj.uid.hex)
print()
print(exp_obj.uid.hex)
