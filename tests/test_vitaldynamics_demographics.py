# This test to test demographics new method SetEquilibriumVitalDynamicsFromWorldBank for birth_rate/morality_rate and
# age_distribution from simulation output(reporter) and compare with original worldbank data and generated demogphics.json
import json
import os
import unittest
from glob import glob

import pandas as pd
from idmtools.core import ItemType  # noqa: F401

from emodpy.emod_task import EMODTask
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from tests import manifest


class VitalDynamicDemographicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self):
        self.platform = Platform("SLURMStage")
        self.schema_path = manifest.schema_path_linux
        self.eradication = manifest.eradication_path_linux
        self.wb_births_df = pd.read_csv(manifest.wb)
        self.places = ["Bulgaria", "Canada", "Burkina Faso", "Burundi", "Austria", "Greenland", "Ukraine",
                       "Russian Federation", "Ethiopia", "Turkey"]
        self.year = 2000
        self.total_sim_year = 5
        self.nSims = 10
        self.n_replica = 1
        self.base_infectivity = 1.0
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName

    def update_sim_bic(self, simulation, value):
        simulation.task.config.parameters.Base_Infectivity_Constant = value * 0.1
        return {"Base_Infectivity": value}

    def update_sim_random_seed(self, simulation, value):
        simulation.task.config.parameters.Run_Number = value
        return {"Run_Number": value}

    def print_params(self):
        """
        Just a useful convenience function for the user.
        """
        # Display exp_name and nSims
        print("exp_name: ", self.case_name)
        print("nSims: ", self.nSims)

    def set_param_fn(self, config):
        config.parameters.Simulation_Duration = 365.0 * self.total_sim_year
        config.parameters.Enable_Demographics_Reporting = 0
        config.parameters.Report_Event_Recorder_Events = ["Births", "NonDiseaseDeaths", "HappyBirthday"]
        config.parameters.Spatial_Output_Channels = ["Population", "Births"]

        return config

    def build_camp(self):
        """
        Build a campaign input file for the DTK using emod_api.
        """
        import emod_api.campaign as camp
        print(f"Telling emod-api to use {manifest.schema_file} as schema.")
        camp.set_schema(manifest.schema_file)
        return camp

    def build_demog(self):
        """
        Build a demographics input file for the DTK using emod_api.
        """
        import emod_api.demographics.Demographics as Demographics

        demog = Demographics.from_csv(manifest.ten_nodes)
        for idx in range(len(self.places)):
            demog.SetEquilibriumVitalDynamicsFromWorldBank(wb_births_df=self.wb_births_df, country=self.places[idx],
                                                           year=self.year,
                                                           node_ids=[idx + 1])
        return demog

    def skip_test_vitaldynamics_demog_from_worldbank(self):
        self.print_params()
        EMODTask.dev_mode = True
        task = EMODTask.from_default2(config_path="config.json", eradication_path=self.eradication,
                                      campaign_builder=self.build_camp, demog_builder=self.build_demog,
                                      schema_path=self.schema_path, param_custom_cb=self.set_param_fn,
                                      ep4_custom_cb=None)
        print("Adding asset dir...")
        task.common_assets.add_asset(os.path.join(manifest.plugins_folder, "libreporteventcounter.so"), relative_path="reporter_plugins")

        task.set_sif(manifest.sft_id_file)

        # Create simulation sweep with builder
        builder = SimulationBuilder()
        builder.add_sweep_definition(self.update_sim_random_seed, range(self.nSims * self.n_replica))

        # create experiment from builder
        experiment = Experiment.from_builder(builder, task, name=self.case_name)
        experiment.run(wait_until_done=True, platform=self.platform)
        # exp_id = '9caf85cb-9f22-ed11-92ed-f0921c167864'
        # experiment = self.platform.get_item(exp_id, item_type=ItemType.EXPERIMENT)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        task.handle_experiment_completion(experiment)
        task.get_file_from_comps(experiment.uid, ["ReportEventRecorder.csv", "SpatialReport_Population.bin",
                                                  "SpatialReport_Births.bin"])
        # Get downloaded local ReportEventRecorder.csv file path for all simulations
        reporteventrecorder_downloaded = list(
            glob(os.path.join(experiment.id, "**/ReportEventRecorder.csv"), recursive=True))

        # ---------------------------------------------
        # Test birth rate and death rate to match world bank birth rate: (should be same as birth_rate)
        birth_count_df = pd.DataFrame()
        death_count_df = pd.DataFrame()
        for i in range(len(reporteventrecorder_downloaded)):
            # read ReportEventRecorder.csv from each sim
            df = pd.read_csv(reporteventrecorder_downloaded[i])
            # Get birth count for each sim. Birth count is total birth row count by Node_ID
            # Note, replace function to replace each 'Births' to 1 to make aggregate easier for groupby and sum
            birth_count_df[i] = df[df['Event_Name'] == "Births"][["Node_ID", "Event_Name"]].replace(
                {'Event_Name': 'Births'}, {'Event_Name': 1}).groupby("Node_ID").sum()
            # Get death count for each sim. Death count is total NonDiseaseDeaths row count by Node_ID
            death_count_df[i] = df[df['Event_Name'] == "NonDiseaseDeaths"][["Node_ID", "Event_Name"]].replace(
                {'Event_Name': 'NonDiseaseDeaths'}, {'Event_Name': 1}).groupby("Node_ID").sum()

        # birth_count_df is for total simulation duration, in this test, total_sim_year=10, so we need to divide 10 to
        # get birth_count per year.
        # Since our initial population is 10000, we want to get birth_rate for every 1000 population,
        # so we need to divide birth_count by another 10=10000/1000 (i.e second 10 in following statement)
        actual_birth_rate = birth_count_df.mean(axis=1) / self.total_sim_year / 10 / self.n_replica
        actual_death_rate = death_count_df.mean(axis=1) / self.total_sim_year / 10 / self.n_replica

        # Get world bank birth rate
        expected_birth_rate = {}
        for idx in range(len(self.places)):
            expected_birth_rate[idx + 1] = \
                self.wb_births_df[self.wb_births_df['Country Name'] == self.places[idx]][str(self.year)].tolist()[0]
        # Verify birth rate and death rate roughly equal to world bank birth rate
        for node_id, birth_rate in expected_birth_rate.items():
            # print("birth_rate diff: " + str(birth_rate - actual_birth_rate[node_id]))  # birth_rate difference
            # print("death_rate_diff: " + str(birth_rate - actual_death_rate[node_id]))  # death_rate difference
            # Assert birth_rate. We allow 1 point different. For example if real birth_rate>44.5, we consider actual
            # birth_rate within range 43.5 to 45.5 is acceptable value giving stochastic feature for simulation
            delta = 1
            self.assertAlmostEqual(birth_rate, actual_birth_rate[node_id], delta=delta)
            # Assert death_rate, We allow 1 point different
            self.assertAlmostEqual(birth_rate, actual_death_rate[node_id], delta=delta)

        # ---------------------------------------------
        # Test age distribution
        # We are listening to 'HappyBirthday' event, since each person will have birthday in a year, so we can get  all person's
        # age in a year. We use age for calculate age distribution over time and compare with demographics age distribution
        f = open(os.path.join(os.getcwd(), "demographics.json"))
        demog_data = json.load(f)
        age_dist = {}
        # Save age_distribution info to age_dist from demographics.json
        for i in range(len(demog_data['Nodes'])):
            age_dist[demog_data['Nodes'][i]['NodeID']] = demog_data['Nodes'][i]['IndividualAttributes'][
                'AgeDistribution']
        # Go through each simulation's ReportEventRecorder file
        for file in reporteventrecorder_downloaded:
            df = pd.read_csv(file)  # read ReportEventRecorder.csv from each sim to dateframe
            # Select only rows with 'HappyBirthday' in 'Event_Name' column which contains 'Age' info. then groupby Node_ID
            df_by_node = df[df['Event_Name'] == "HappyBirthday"].groupby("Node_ID")
            # For each node_id
            for node_id, happy_birthday_df in df_by_node:
                # Convert Age from day to year and cast to integer
                happy_birthday_df['Age'] = (happy_birthday_df['Age'] / 365).astype(int)
                # Convert Age > 90 to 90 to get to correct  bin bucket
                happy_birthday_df.loc[happy_birthday_df["Age"] > 90]['Age'] = 90
                # Convert happy_birthday_df['Age"] column to demographics.json's age bins and add to 'bins' columns
                # i.e if Age = 71, it will assign to (70. 75] 'bins' bucket
                happy_birthday_df['bins'] = pd.cut(x=happy_birthday_df['Age'], bins=age_dist[node_id]['ResultValues'])
                # Get total count for each age bins
                happy_birthday_bin_df = happy_birthday_df[['Event_Name', "bins"]].replace(
                    {"Event_Name": "HappyBirthday"},
                    {"Event_Name": 1}).groupby("bins").sum()
                # Rename Event_Name column to proper name 'count'
                happy_birthday_bin_df.rename(columns={'Event_Name': 'count'}, inplace=True)
                age_percent_list = []
                for index, row in happy_birthday_bin_df.iterrows():
                    # Get percentage for each bucket
                    age_percent_list.append(row['count'] / sum(happy_birthday_bin_df['count']))
                happy_birthday_bin_df['percent'] = age_percent_list
                # Get cumulated percentage for each bucket
                happy_birthday_bin_df['cum_percent'] = happy_birthday_bin_df['percent'].cumsum()
                real_age_distribition_cum_percent_values = happy_birthday_bin_df['cum_percent'].tolist()

                # Verify each age bin from each node and each sim have produce  correct distribution comparing with
                # demographics.json's age distribution in each node for each simulation
                for age_bucket in range(len(real_age_distribition_cum_percent_values)):
                    # Print difference of age distribution between each simulation each node with one from demographics.json
                    # print(age_dist[node_id]['DistributionValues'][1:][age_bucket] -
                    #       real_age_distribition_cum_percent_values[age_bucket])
                    expected_age_distribution_at_bucket = age_dist[node_id]['DistributionValues'][1:][age_bucket]
                    # Verify they are almost the same with 0.02 tolerant
                    # for example in demographics.json, 0.97548758 for age bin (85, 90], the real one maybe 0.985487
                    # for same age bin, we consider this is good enough value
                    self.assertAlmostEqual(expected_age_distribution_at_bucket,
                                           real_age_distribition_cum_percent_values[age_bucket], delta=0.02)
