##
"""
Measles Ward Simulations: Sample demographic
"""
#
import os
import sys
from functools import partial

import numpy as np
import math

from idmtools.assets import Asset
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

import random

from examples.kevin_workflow.globals import create_task, get_os_type

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# config and campaign file path
CAMPAIGN_PATH = os.path.join('inputs', 'full_campaign.json')
CONFIG_PATH = os.path.join('inputs', 'config_1.json')

asset_for_large_file = Asset(
    r'\\internal.idm.ctr\IDM-Test\home\shchen\shared_files\Africa_district_overlay_10group_lowconnectivity_HINT_demographics.json')

# if you are on linux machine:
# asset_for_large_file = Asset(
#      '/mnt/idm/home/shchen/shared_files/Africa_district_overlay_10group_lowconnectivity_HINT_demographics.json')


# set a random seed for reproducibility
random.seed(83082)

exp_name = 'Type 2 polio Africa district-level model'

def sample_point_fn(simulation, param, value):
    tags ={}

    # Setup some baseline parameters, but allow them to be overwritten afterwards by inputs to this function
    if param.startswith('META'):
        tags=meta_parameter_handler(simulation.task, param, value)
    else:
        simulation.task.set_parameter(param, value)
        tags[param] = value
    return tags


def meta_parameter_handler(task, param, value):
    tags = {}
    if param == 'META_susceptibility_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[1] = 'Africa_singlenode_test_overlayS'+value+'_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
    elif param == 'META_HINT_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[2] = 'Africa_singlenode_test_overlay'+value+'HINT_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags['META_HINT_overlay'] = value
    elif param == 'META_Base_Infectivity_LNMean_CoeffVar':
        task.set_parameter('Base_Infectivity_Log_Normal_Mu', math.log(value[0])-1/2*math.log(1+value[1]**2))
        task.set_parameter('Base_Infectivity_Log_Normal_Sigma', math.sqrt(math.log(1+value[1]**2)))
        task.set_parameter("Base_Infectivity_Distribution", "LOG_NORMAL_DISTRIBUTION")
        tags['META_Base_Infectivity_LNMean_CoeffVar'] = [value[0], value[1]]
        #tags['Base_Infectivity_CoeffVar'] = value[1]
    return tags

if __name__ == "__main__":
    # sweep parameters
    builder = SimulationBuilder()
    # Add sweep parameter to builder
    builder.add_sweep_definition(partial(sample_point_fn, param='Air_Migration_Filename'), [v for v in ['Africa_district_gravity_air_migration.bin','Africa_district_Stouffervariant_air_migration.bin']])
    builder.add_sweep_definition(partial(sample_point_fn, param='x_Air_Migration'), [v for v in list(np.logspace(-5, -3, 51))])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_LNRisk_overlay'), [v for v in [1]])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_Base_Infectivity_LNMean_CoeffVar'), [(10*v/32, 1.0) for v in [20, 40, 70, 100]])
    builder.add_sweep_definition(partial(sample_point_fn, param='Run_Number'), [v for v in range(1, 2)])

    with Platform('SLURM', num_cores=8, num_retries=3) as platform:
        # with Platform('COMPS2', num_cores=8, num_retries=3) as platform:
        env = platform.environment
        os_type = get_os_type(env)
        task = create_task(os_type, CONFIG_PATH, CAMPAIGN_PATH, env, platform)

        task.common_assets.add_asset(asset_for_large_file)
        task.set_parameter("logLevel_default", 'ERROR')
        task.set_parameter("Start_Time", 1)
        task.set_parameter("Memory_Usage_Warning_Threshold_Working_Set_MB", 14000)
        task.set_parameter("Memory_Usage_Halting_Threshold_Working_Set_MB", 15000)
        task.set_parameter('Simulation_Duration', 7)

        # Now we can create our Experiment with from_builder()
        experiment = Experiment.from_builder(builder, base_task=task, name=exp_name)
        experiment.run()
