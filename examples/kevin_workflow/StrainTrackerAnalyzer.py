import os
import pickle
import sys

import pandas as pd
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.ianalyzer import BaseAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class StrainTrackerAnalyzer(BaseAnalyzer):
    def __init__(self, output_path):
        super().__init__(filenames=['output\\ReportStrainTracking.csv'])
        self.output_path = output_path

    def map(self, data, simulation):
        # Apply is called for every simulations included into the experiment
        # We are simply storing the population data in the pop_data dictionary
        df = pd.DataFrame(columns=simulation.tags.keys())  # Create a dataframe with the simulation tag keys
        df.loc[str(simulation.uid)] = list(simulation.tags.values())  # Get a list of the sim tag values
        df = df.drop(['task_type'], axis=1)  # don't need this tag
        return df

    def reduce(self, all_data):
        results = pd.concat(list(all_data.values()), axis=0)  # Combine a list of all the sims tag values
        results.reset_index(drop=True, inplace=True)
        results.to_feather(os.path.join(self.output_path, 'metadata.ftr'))
        # with open(os.path.join(self.output_path, 'metadata.pkl'), 'wb') as pklfile:
        #    pickle.dump(all_data, pklfile)
        # results.to_csv(os.path.join(self.output_path, 'metadata.csv'))


# This code will analyze the latest experiment ran with the PopulationAnalyzer
if __name__ == "__main__":
    with Platform('COMPS2') as platform:

        output_path = os.path.join('outputs', 'wide_grid_calibration_iter2fixed_idmtools')
        os.makedirs(output_path, exist_ok=True)
        exp = [('6f6ed858-d8d5-ea11-a2c0-f0921c167862', ItemType.EXPERIMENT)] # experiment from RunPolioScenario.py
        analyzers = [StrainTrackerAnalyzer(output_path=output_path)]
        am = AnalyzeManager(platform=platform, ids=exp, analyzers=analyzers, partial_analyze_ok=True)
        am.analyze()
