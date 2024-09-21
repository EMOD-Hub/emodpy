import math
import os
import sys
import pickle
import time
import numpy as np
import pandas as pd
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.ianalyzer import BaseAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class InsetChartPlusPropertyReportAnalyzer(BaseAnalyzer):
    def __init__(self, outputfile):
        super().__init__(filenames=['output\\InsetChart.json',
                                    'output\\PropertyReport.json'])
        self.outputfile = outputfile

    def map(self, data, simulation):
        # Apply is called for every simulations included into the experiment
        # We are simply storing the population data in the pop_data dictionary
        selected_data = {}
        selected_data['BI_Mean'] = simulation.tags['Base_Infectivity_Mean']
        selected_data['hint_connection'] = float(simulation.tags['META_HINT_overlay'].replace('p', '.'))
        selected_data['run_number'] = simulation.tags['Run_Number']
        selected_data['init_susc'] = float(simulation.tags['META_susceptibility_overlay'].replace('p', '.'))
        selected_data['total_infections'] = np.sum(data[self.filenames[0]]["Channels"]["New Infections"]["Data"])
        for i in range(10):
            selected_data['total_infections_group_'+str(i)] = np.sum(data[self.filenames[1]]["Channels"]
                                                              ["New Infections:Geographic:geo_"+str(i)]["Data"])
        selected_data['outbreak_duration'] = np.max(np.nonzero(data[self.filenames[0]]["Channels"]["Infected"]["Data"]))
        selected_data['final_susc'] = data[self.filenames[0]]["Channels"]["Susceptible Population"]["Data"][-1]
        return selected_data

    def reduce(self, all_data):

        with open(self.outputfile, 'wb') as pklfile:
            #pickle.dump(pd.DataFrame(all_data), ftrfile)
            pickle.dump(all_data, pklfile)
        return None


class InsetChartAnalyzer(BaseAnalyzer):
    def __init__(self, outputfile):
        super().__init__(filenames=['output\\InsetChart.json'])
        self.outputfile = outputfile

    def map(self, data, simulation):
        # Apply is called for every simulations included into the experiment
        # We are simply storing the population data in the pop_data dictionary
        selected_data = {}
        selected_data['BI_Mean'] = simulation.tags['Base_Infectivity_Mean']
        selected_data['BI_CV'] = simulation.tags['Base_Infectivity_CoeffVar']
        selected_data['risk_CV'] = simulation.tags['Risk_CV']
        selected_data['run_number'] = simulation.tags['Run_Number']
        selected_data['init_susc'] = float(simulation.tags['META_susceptibility_overlay'].replace('p', '.'))
        selected_data['total_infections'] = np.sum(data[self.filenames[0]]["Channels"]["New Infections"]["Data"])
        selected_data['outbreak_duration'] = np.max(np.nonzero(data[self.filenames[0]]["Channels"]["Infected"]["Data"]))
        selected_data['final_susc'] = data[self.filenames[0]]["Channels"]["Susceptible Population"]["Data"][-1]
        return selected_data

    def reduce(self, all_data):
        with open(self.outputfile, 'wb') as pklfile:
            #pickle.dump(pd.DataFrame(all_data), ftrfile)
            pickle.dump(all_data, pklfile)
        return None

class InsetChartPlusAgeReportAnalyzer(BaseAnalyzer):
    def __init__(self, outputfile):
        super().__init__(filenames=['output\\InsetChart.json',
                                    'output\\AgeAtInfectionHistogramReport.json'])
        self.outputfile = outputfile

    def map(self, data, simulation):
        # Apply is called for every simulations included into the experiment
        # We are simply storing the population data in the pop_data dictionary
        selected_data = {}
        selected_data['BI_Mean'] = simulation.tags['Base_Infectivity_Mean']
        selected_data['BI_CV'] = simulation.tags['Base_Infectivity_CoeffVar']
        selected_data['risk_CV'] = simulation.tags['Risk_CV']
        selected_data['run_number'] = simulation.tags['Run_Number']
        selected_data['agebins'] = data['output\\AgeAtInfectionHistogramReport.json']['Channels']['Age_Bin_Upper_Edges']['Data']
        selected_data['agecounts'] = data['output\\AgeAtInfectionHistogramReport.json']['Channels']['Accumulated_Binned_Infection_Counts']['Data']
        accumlen = 10
        datalen = len(data[self.filenames[0]]["Channels"]["New Infections"]["Data"])
        tmplen = math.ceil(datalen/accumlen)
        inds = [math.floor(i/accumlen) for i in range(datalen)]
        channels = ["New Infections", "Susceptible Population", "Infectious Population", "Statistical Population"]
        norms = [1, accumlen, accumlen, accumlen]
        for channel, norm in zip(channels, norms):
            tmp = np.zeros(tmplen)
            np.add.at(tmp, inds, np.array(data[self.filenames[0]]["Channels"][channel]["Data"])/norm)
            selected_data[channel] = tmp

        return selected_data

    def reduce(self, all_data):

        with open(self.outputfile, 'wb') as pklfile:
            pickle.dump(all_data, pklfile)
        return None


# This code will analyze the latest experiment ran with the PopulationAnalyzer
if __name__ == "__main__":
    with Platform('COMPS2') as platform:

        outout_path = os.path.join('outputs', 'singlenodetest_sims')
        outfile_name = os.path.join(outout_path, 'results_HINTgroups_fixed_idmtools.pkl')
        os.makedirs(outout_path, exist_ok=True)
        exp = [('53589591-d6d5-ea11-a2c0-f0921c167862', ItemType.EXPERIMENT)] # experiment from RunSinglenodeTests.py
        analyzers = [InsetChartPlusPropertyReportAnalyzer(outputfile=outfile_name)]
        am = AnalyzeManager(platform=platform, ids=exp, analyzers=analyzers)
        am.analyze()
