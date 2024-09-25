##
"""
Measles Ward Simulations: Sample demographic
"""
#
import os
import sys
from functools import partial
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform

import random
import numpy as np
import math

from idmtools.entities.experiment import Experiment

from examples.kevin_workflow.globals import create_task, get_os_type

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# config and campaign file path
CAMPAIGN_PATH = os.path.join('inputs', 'campaign_test.json')
CONFIG_PATH = os.path.join('inputs', 'config.json')

# set a random seed for reproducibility
random.seed(83082)


def sample_point_fn(simulation, param, value):
    tags = {}
    # Setup some baseline parameters, but allow them to be overwritten afterwards by inputs to this function
    if param.startswith('META'):
        tags = meta_parameter_handler(simulation.task, param, value)
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
        tags[param] = value

    elif param == 'META_HINT_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        if value == '':
            demos = demos[0:3]
            task.set_parameter('Enable_Heterogeneous_Intranode_Transmission', 0)
        else:
            demos[3] = 'Africa_singlenode_test_overlaymaxconn'+value+'HINT_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags[param] = value

    elif param == 'META_Base_Infectivity_GammaMean_CoeffVar':
        task.set_parameter('Base_Infectivity_Scale', value[0]*value[1]**2)
        task.set_parameter('Base_Infectivity_Shape', (1/value[1])**2)
        task.set_parameter("Base_Infectivity_Distribution", "GAMMA_DISTRIBUTION")

        tags['Base_Infectivity_Mean'] = value[0]
        tags['Base_Infectivity_CoeffVar'] = value[1]

    elif param == 'META_Base_Infectivity_LNMean_CoeffVar':
        task.set_parameter('Base_Infectivity_Log_Normal_Mu', math.log(value[0])-1/2*math.log(1+value[1]**2))
        task.set_parameter('Base_Infectivity_Log_Normal_Sigma', math.sqrt(math.log(1+value[1]**2)))
        task.set_parameter("Base_Infectivity_Distribution", "LOG_NORMAL_DISTRIBUTION")

        tags['Base_Infectivity_Mean'] = value[0]
        tags['Base_Infectivity_CoeffVar'] = value[1]

    elif param == 'META_LNRisk_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[2] = 'Africa_singlenode_test_overlayrisk_LN_CV'+str(value).replace('.', 'p')+'_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags['Risk_CV'] = value

    elif param == 'META_GammaRisk_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[2] = 'Africa_singlenode_test_overlayrisk_gamma_CV'+str(value).replace('.', 'p')+'_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags['Risk_CV'] = value
    return tags


if __name__ == "__main__":
    init_susc = [x / 50 for x in range(1, 2)]
    svals = [str(x).replace('.', 'p') for x in init_susc]
    rvals = [str(x/4).replace('.', 'p') for x in range(3)]
    exp_name = 'Re-testing point importation behavior with risk heterogeneity'

    # sweep parameters
    builder = SimulationBuilder()
    # Add sweep parameter to builder
    builder.add_sweep_definition(partial(sample_point_fn, param='META_susceptibility_overlay'), [v for v in svals])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_HINT_overlay'), [f'{v:.2e}'.replace('.', 'p') for v in list(np.logspace(-6, -4, 21))])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_LNRisk_overlay'), [v for v in [1]])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_Base_Infectivity_LNMean_CoeffVar'), [(10*v/32, 1.0) for v in [2, 4, 7, 10, 13, 16, 20]])
    builder.add_sweep_definition(partial(sample_point_fn, param='Run_Number'), [v for v in range(1, 2)])

    with Platform("SLURM") as platform:
        env = platform.environment
        os_type = get_os_type(env)

        # create task
        task = create_task(os_type, CONFIG_PATH, CAMPAIGN_PATH, env, platform)

        # update parameters
        task.set_parameter("Infection_Rate_Overdispersion", 1.0)
        task.set_parameter("Enable_Property_Output", 1)

        # Now we can create our Experiment with from_builder()
        experiment = Experiment.from_builder(builder, base_task=task, name=exp_name)
        experiment.run()


