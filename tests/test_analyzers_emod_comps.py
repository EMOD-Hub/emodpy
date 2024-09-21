import json
import os

import pandas as pd
import pytest
from idmtools.analysis.add_analyzer import AddAnalyzer
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.analysis.csv_analyzer import CSVAnalyzer
from idmtools.analysis.download_analyzer import DownloadAnalyzer
from idmtools.analysis.tags_analyzer import TagsAnalyzer
from idmtools.builders import SimulationBuilder
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence
from idmtools_test.utils.utils import del_file, del_folder

from emodpy.analyzers.population_analyzer import PopulationAnalyzer
from emodpy.analyzers.timeseries_analyzer import TimeseriesAnalyzer
from emodpy.defaults import EMODSir
from emodpy.emod_task import EMODTask

current_directory = os.path.dirname(os.path.realpath(__file__))
BIN_PATH = os.path.join(current_directory, "..", "examples", "inputs", "bin")
INPUT_PATH = os.path.join(current_directory, "..", "examples", "serialization", "inputs")


@pytest.mark.comps
@pytest.mark.analysis
class TestAnalyzeManagerEmodComps(ITestWithPersistence):

    def generate_experiment(self) -> Experiment:
        base_task = EMODTask.from_default(default=EMODSir(), eradication_path=os.path.join(BIN_PATH, "Eradication.exe"))
        base_task.set_parameter("Enable_Immunity", 0)
        # User builder to create simulations
        num_sims = 3
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sims))
        experiment = Experiment.from_builder(
            builder,
            base_task,
            tags={"idmtools": "idmtools-automation", "string_tag": "test", "number_tag": 123}
        )
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment)
        self.exp_id = experiment.uid

    @classmethod
    def setUpClass(cls):
        cls.platform = Platform('COMPS2')
        cls.generate_experiment(cls)

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)

    @pytest.mark.long
    def test_add_analyzer(self):
        filenames = ['StdOut.txt']
        analyzers = [AddAnalyzer(filenames=filenames)]
        # self.generate_experiment()
        am = AnalyzeManager(platform=self.platform, ids=[(self.exp_id, ItemType.EXPERIMENT)], analyzers=analyzers)
        am.analyze()

    @pytest.mark.long
    def test_download_analyzer(self):
        # delete output from previous run
        del_folder("output")

        # create a new empty 'output' dir
        os.mkdir("output")

        # self.exp_id = "8a7ff62a-fe7f-ea11-a2bf-f0921c167862"
        filenames = ['output/InsetChart.json', 'config.json']
        analyzers = [DownloadAnalyzer(filenames=filenames, output_path='output')]

        am = AnalyzeManager(platform=self.platform, ids=[(self.exp_id, ItemType.EXPERIMENT)], analyzers=analyzers)
        am.analyze()

        exp = self.platform.get_item(item_id=self.exp_id, item_type=ItemType.EXPERIMENT)
        sims = self.platform.get_children_by_object(exp)
        for sim in sims:
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "config.json")))
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "InsetChart.json")))

    def test_analyzer_multiple_experiments(self):
        # delete output from previous run
        del_folder("output")

        # create a new empty 'output' dir
        os.mkdir("output")

        filenames = ['output/InsetChart.json', 'config.json']
        analyzers = [DownloadAnalyzer(filenames=filenames, output_path='output')]

        exp_ids = ['6f693627-6de5-e911-a2be-f0921c167861', '1991ec0d-6ce5-e911-a2be-f0921c167861']
        exp_list = [(exp_ids[0], ItemType.EXPERIMENT),
                    (exp_ids[1], ItemType.EXPERIMENT)]  # comps2 staging
        am = AnalyzeManager(platform=self.platform, ids=exp_list, analyzers=analyzers)
        am.analyze()

        # validate downloaded files
        # first get simulations by experiment ids
        simulations = []
        exp = self.platform.get_item(item_id=exp_ids[0], item_type=ItemType.EXPERIMENT)
        sims = self.platform.get_children_by_object(exp)
        for sim in sims:
            simulations.append(sim)

        exp1 = self.platform.get_item(item_id=exp_ids[1], item_type=ItemType.EXPERIMENT)
        sims1 = self.platform.get_children_by_object(exp1)
        for sim in sims1:
            simulations.append(sim)
        # iterator through all simulations and check all files get downloaded
        for sim in simulations:
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "config.json")))
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "InsetChart.json")))

    @pytest.mark.long
    def test_population_analyzer(self):
        del_file('output', 'population.json')
        del_file('output', 'population.png')

        # self.exp_id = "8a7ff62a-fe7f-ea11-a2bf-f0921c167862"
        filenames = ['output/InsetChart.json']

        analyzers = [PopulationAnalyzer(filenames)]

        am = AnalyzeManager(platform=self.platform, ids=[(self.exp_id, ItemType.EXPERIMENT)], analyzers=analyzers)
        am.analyze()

        # validate "Statistical Population" values in PopulationAnalyzer's output file: 'population.json'
        # are same as in output/InsetChart.json which downloaded to local
        # first read population.json content
        with open(os.path.join('output', 'population.json'), 'r') as read_file:
            population_json = json.load(read_file)

        # compare above value with each simulation's 'Statistical Population' data in insetChart.json
        exp = self.platform.get_item(item_id=self.exp_id, item_type=ItemType.EXPERIMENT)
        sims = self.platform.get_children_by_object(exp)
        for simulation in sims:
            output_file = 'output/InsetChart.json'
            self.platform.get_files(simulation, files=[output_file], output='output')
            output_file_path = os.path.join('output', simulation.id)
            with open(os.path.join(output_file_path, output_file), 'r') as read_file:
                inset_chart_dict = json.load(read_file)
            population_channel_data = inset_chart_dict['Channels']['Statistical Population']['Data']
            self.assertEqual(population_json.get(simulation.id), population_channel_data)

    @pytest.mark.long
    def test_timeseries_analyzer_with_filter(self):
        # delete output from previous run
        del_folder("output")

        # create a new empty 'output' dir
        os.mkdir("output")
        # self.generate_experiment()

        filenames = ['output/InsetChart.json']
        analyzers = [TimeseriesAnalyzer(filenames=filenames)]

        # self.exp_id = "299d39f2-01b5-ea11-a2c0-f0921c167862"
        am = AnalyzeManager(platform=self.platform, ids=[(self.exp_id, ItemType.EXPERIMENT)], analyzers=analyzers)
        am.analyze()

        # compare 'Infected' channel in timeseries.csv and output/InsetChart.json file's 'Infected' data for each sim
        # first, read infected data from timeseries.csv file
        df = pd.read_csv(os.path.join('output', 'timeseries.csv'), usecols=['Infected', 'Infected.1'], skiprows=[1])

        exp = self.platform.get_item(item_id=self.exp_id, item_type=ItemType.EXPERIMENT)
        sims = self.platform.get_children_by_object(exp)
        for simulation in sims:
            output_file = 'output/InsetChart.json'
            self.platform.get_files(simulation, files=[output_file], output='output')
            output_file_path = os.path.join('output', simulation.id)
            with open(os.path.join(output_file_path, output_file), 'r') as read_file:
                inset_chart_dict = json.load(read_file)
            infected_channel_data = inset_chart_dict['Channels']['Infected']['Data']
            if df.at[0, 'Infected'] == simulation.id:
                self.assertEqual(df.loc[1:, 'Infected'].astype('float').tolist(), infected_channel_data)
            if df.at[0, 'Infected.1'] == simulation.id:
                self.assertEqual(df.loc[1:, 'Infected.1'].astype('float').tolist(), infected_channel_data)

    def test_analyzer_preidmtools_exp(self):
        # delete output from previous run
        del_folder("output")

        # create a new empty 'output' dir
        os.mkdir("output")

        filenames = ['output/InsetChart.json', 'config.json']
        analyzers = [DownloadAnalyzer(filenames=filenames, output_path='output')]

        exp_id = 'f48e09d4-acd9-e911-a2be-f0921c167861'
        exp_tup = (exp_id, ItemType.EXPERIMENT)  # comps2

        am = AnalyzeManager(platform=self.platform, ids=[exp_tup], analyzers=analyzers)
        am.analyze()

        exp = self.platform.get_item(item_id=exp_id, item_type=ItemType.EXPERIMENT)
        sims = self.platform.get_children_by_object(exp)
        for sim in sims:
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "config.json")))
            self.assertTrue(os.path.exists(os.path.join('output', sim.id, "InsetChart.json")))

    def test_download_analyzer_suite(self):
        # delete output from previous run
        del_folder("output")

        # create a new empty 'output' dir
        os.mkdir("output")

        filenames = ['output/InsetChart.json']
        analyzers = [DownloadAnalyzer(filenames=filenames, output_path='output')]

        suite_id = 'e00296a6-0200-ea11-a2be-f0921c167861'
        suite_list = [(suite_id, ItemType.SUITE)]  # comps2 staging
        am = AnalyzeManager(platform=self.platform, ids=suite_list, analyzers=analyzers)
        am.analyze()

        # verify results:
        # retrieve suite object
        suite = self.platform.get_item(item_id=suite_id, item_type=ItemType.SUITE)
        # retrieve experiment from suite
        exp_list = self.platform.get_children_by_object(suite)
        experiment = self.platform.get_item(item_id=exp_list[0].uid, item_type=ItemType.EXPERIMENT)
        # retrieve idmtools simulation list
        sims = self.platform.get_children_by_object(experiment)
        for simulation in sims:
            self.assertTrue(os.path.exists(os.path.join('output', str(simulation.uid), "InsetChart.json")))

    @pytest.mark.long
    def test_tags_analyzer_emod_exp(self):
        experiment_id = '36d8bfdc-83f6-e911-a2be-f0921c167861'  # staging exp id JSuresh's Magude exp

        # delete output from previous run
        output_dir = "output_tag"
        del_folder(output_dir)
        analyzers = [TagsAnalyzer()]

        manager = AnalyzeManager(platform=self.platform, partial_analyze_ok=True,
                                 ids=[(experiment_id, ItemType.EXPERIMENT)],
                                 analyzers=analyzers)
        manager.analyze()

        # verify results
        self.assertTrue(os.path.exists(os.path.join(output_dir, "tags.csv")))

    def test_csv_analyzer_emod_exp(self):
        experiment_id = '9311af40-1337-ea11-a2be-f0921c167861'  # staging exp id with csv from config
        # delete output from previous run
        output_dir = "output_csv"
        del_folder(output_dir)
        filenames = ['output/c.csv']
        analyzers = [CSVAnalyzer(filenames=filenames)]

        manager = AnalyzeManager(platform=self.platform, partial_analyze_ok=True,
                                 ids=[(experiment_id, ItemType.EXPERIMENT)],
                                 analyzers=analyzers)
        manager.analyze()

        # verify results
        self.assertTrue(os.path.exists(os.path.join(output_dir, "CSVAnalyzer.csv")))

    def test_csv_analyzer_emod_exp_non_csv_error(self):
        experiment_id = '36d8bfdc-83f6-e911-a2be-f0921c167861'  # staging exp id JSuresh's Magude exp

        # delete output from previous run
        output_dir = "output_csv"
        del_folder(output_dir)
        filenames = ['output/MalariaPatientReport.json']
        with self.assertRaises(Exception) as context:
            analyzers = [CSVAnalyzer(filenames=filenames)]
            manager = AnalyzeManager(platform=self.platform, partial_analyze_ok=True,
                                     ids=[(experiment_id, ItemType.EXPERIMENT)],
                                     analyzers=analyzers)
            manager.analyze()

        self.assertIn('Please ensure all filenames provided to CSVAnalyzer have a csv extension.',
                      context.exception.args[0])

    def test_multi_csv_analyzer_emod_exp(self):
        experiment_id = '1bddce22-0c37-ea11-a2be-f0921c167861'  # staging exp id PythonExperiment with 2 csv outputs

        # delete output from previous run
        output_dir = "output_csv"
        del_folder(output_dir)

        filenames = ['output/a.csv', 'output/b.csv']
        analyzers = [CSVAnalyzer(filenames=filenames)]

        manager = AnalyzeManager(platform=self.platform, partial_analyze_ok=True,
                                 ids=[(experiment_id, ItemType.EXPERIMENT)],
                                 analyzers=analyzers)
        manager.analyze()

        # verify results
        self.assertTrue(os.path.exists(os.path.join(output_dir, "CSVAnalyzer.csv")))
