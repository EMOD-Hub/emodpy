##
"""
Measles Ward Simulations: Sample demographic
"""
#
import os
import sys
from dataclasses import dataclass, field
from functools import partial

from emodpy.emod_task import EMODTask
from emodpy.reporters.custom import ReportPluginAgeAtInfectionHistogram
from idmtools.assets import AssetCollection
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

import random

import math

from examples.kevin_workflow.globals import get_os_type, create_task

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# need to override ReportPluginAgeAtInfectionHistogram class to contain add_report method
# we should add this to emodpy
@dataclass
class MyReportPluginAgeAtInfectionHistogram(ReportPluginAgeAtInfectionHistogram):
    def add_report(self, age_bins=None, interval_years=1):
        if age_bins is None:
            age_bins = []
        self._add_report({
            "Age_At_Infection_Histogram_Report_Age_Bin_Upper_Edges_In_Years": age_bins,
            "Age_At_Infection_Histogram_Report_Reporting_Interval_In_Years": interval_years
        })


# config and campaign file path
CAMPAIGN_PATH = os.path.join('inputs', 'campaign_multioutbreak_test.json')
CONFIG_PATH = os.path.join('inputs', 'config_multioutbreak_test.json')
REPORT_PATH = os.path.join('inputs', 'custom_reports.json')

exp_name = 'Testing multi-outbreak behavior in single pop with risk heterogeneity'

report = MyReportPluginAgeAtInfectionHistogram()
report.add_report(age_bins=[x/12 for x in range(1, 61)]+[x/2 for x in range(11, 21)]+[x for x in range(11, 31)] + [100], interval_years=1)

random.seed(83082)


def sample_point_fn(simulation, param, value):
    tags ={}

    # Setup some baseline parameters, but allow them to be overwritten afterwards by inputs to this function
    if param.startswith('META'):
        tags = meta_parameter_handler(simulation.task, param, value)
    else:
        simulation.task.set_parameter(param, value)
        tags[param] = value
    return tags


def meta_parameter_handler(task, param, value):
    tags = {}
    if param == 'META_HINT_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[2] = 'Africa_singlenode_test_overlaymaxconn'+value+'HINT_demographics.json'
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
        demos[1] = 'Africa_singlenode_test_overlayrisk_LN_CV'+str(value).replace('.', 'p')+'_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags['Risk_CV'] = value
    elif param == 'META_GammaRisk_overlay':
        demos = task.get_parameter('Demographics_Filenames')
        demos[1] = 'Africa_singlenode_test_overlayrisk_gamma_CV'+str(value).replace('.', 'p')+'_demographics.json'
        task.set_parameter('Demographics_Filenames', demos)
        tags['Risk_CV'] = value
    return tags


if __name__ == "__main__":

    builder = SimulationBuilder()
    # Add sweep parameter to builder
    builder.add_sweep_definition(partial(sample_point_fn, param='META_LNRisk_overlay'), [v for v in [0.01, 0.1, 0.3]])
    builder.add_sweep_definition(partial(sample_point_fn, param='META_Base_Infectivity_LNMean_CoeffVar'),
                                 [(10 * v / 32, w) for v in [2, 4, 8, 12, 16] for w in
                                  [0.01, 1.0]]),  # 0.1, 0.3, 0.5, 1, 1.5, 2, 3, 5, 10]])
    builder.add_sweep_definition(partial(sample_point_fn, param='Run_Number'), [v for v in range(1, 2)])

    with Platform('COMPS2') as platform:
    # platform = Platform('SLURM')
        env = platform.environment
        os_type = get_os_type(env)

        task = create_task(os_type, CONFIG_PATH, CAMPAIGN_PATH, env, platform)

        task.reporters.add_reporter(report)

        # common assets which contains all files generated from create_asset_collection.py
        with open(os.path.join('inputs', 'DTKInputFiles', env + '_asset_collection.txt')) as fn:
            ac_id = fn.readline()

        task.set_parameter("Infection_Rate_Overdispersion", 1.0)
        task.set_parameter('Simulation_Duration', 7)

        # Now we can create our Experiment with from_builder()
        experiment = Experiment.from_builder(builder, base_task=task, name=exp_name)
        experiment.run()
