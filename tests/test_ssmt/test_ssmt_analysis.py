import json
import os
import pytest

from idmtools.analysis.platform_anaylsis import PlatformAnalysis
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform

from emodpy.analyzers.adult_vectors_analyzer import AdultVectorsAnalyzer
from emodpy.analyzers.population_analyzer import PopulationAnalyzer


@pytest.mark.comps
@pytest.mark.ssmt
class TestSSMTAnalysis():

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.case_name = os.path.basename(__file__) + "--" + request.node.name
        self.platform = Platform('COMPS2')

    # test using SSMTAnalysis to run PopulationAnalyzer in comps's SSMT DockerWorker
    @pytest.mark.skip
    def test_ssmt_analysis_PopulationAnalyzer(self):
        experiment_id = "8bb8ae8f-793c-ea11-a2be-f0921c167861"  # comps2
        analysis = PlatformAnalysis(platform=self.platform,
                                    experiment_ids=[experiment_id],
                                    analyzers=[PopulationAnalyzer],
                                    analyzers_args=[{'name': 'anything'}],
                                    analysis_name=self.case_name,
                                    tags={'idmtools': self._testMethodName, 'WorkItem type': 'Docker'})

        analysis.analyze(check_status=True)
        wi = analysis.get_work_item()

        # validate output files
        local_output_path = "output"
        helpers.delete_existing_folder(local_output_path)
        out_filenames = ["output/population.png", "output/population.json", "WorkOrder.json"]
        self.platform.get_files_by_id(wi.uid, ItemType.WORKFLOW_ITEM, out_filenames, local_output_path)

        file_path = os.path.join(local_output_path, str(wi.uid))
        self.assertTrue(os.path.exists(os.path.join(file_path, "output", "population.png")))
        self.assertTrue(os.path.exists(os.path.join(file_path, "output", "population.json")))
        self.assertTrue(os.path.exists(os.path.join(file_path, "WorkOrder.json")))
        with open(os.path.join(file_path, "WorkOrder.json"), 'r') as f:
            worker_order = json.load(f)
            print(worker_order)
            self.assertEqual(worker_order['WorkItem_Type'], "DockerWorker")
            execution = worker_order['Execution']
            self.assertEqual(
                execution['Command'],
                f"python platform_analysis_bootstrap.py {experiment_id} "
                f"population_analyzer.PopulationAnalyzer comps2"
            )

    # test using SSMTAnalysis to run multiple analyzers in comps's SSMT DockerWorker
    # this test will be skip until further evaluation.
    @pytest.mark.skip
    def test_ssmt_analysis_multiple_analyzers(self):
        experiment_id = "8bb8ae8f-793c-ea11-a2be-f0921c167861"  # comps2
        analysis = PlatformAnalysis(platform=self.platform,
                                    experiment_ids=[experiment_id],
                                    analyzers=[PopulationAnalyzer, AdultVectorsAnalyzer],
                                    analyzers_args=[{'name': 'anything'}, {'name': "adult test"}],
                                    analysis_name=self.case_name,
                                    tags={'idmtools': self._testMethodName, 'WorkItem type': 'Docker'})

        analysis.analyze(check_status=True)
        wi = analysis.get_work_item()

        # validate output files
        local_output_path = "output"
        helpers.delete_existing_folder(local_output_path)
        out_filenames = ["output/population.png", "output/population.json",
                         "output/adult_vectors.json", "output/adult_vectors.png", "WorkOrder.json"]
        self.platform.get_files_by_id(wi.uid, ItemType.WORKFLOW_ITEM, out_filenames,
                                      local_output_path)

        file_path = os.path.join(local_output_path, str(wi.uid))
        assert(os.path.exists(os.path.join(file_path, "output", "population.png")))
        assert(os.path.exists(os.path.join(file_path, "output", "population.json")))
        assert(os.path.exists(os.path.join(file_path, "output", "adult_vectors.png")))
        assert(os.path.exists(os.path.join(file_path, "output", "adult_vectors.json")))
        assert(os.path.exists(os.path.join(file_path, "WorkOrder.json")))
        with open(os.path.join(file_path, "WorkOrder.json"), 'r') as f:
            worker_order = json.load(f)
            print(worker_order)
            assert(worker_order['WorkItem_Type']=="DockerWorker")
            execution = worker_order['Execution']
            cmd_str = f"python platform_analysis_bootstrap.py {experiment_id} population_analyzer.PopulationAnalyzer,adult_vectors_analyzer.AdultVectorsAnalyzer comps2"
            assert(execution['Command']==cmd_str)

    # test using SSMTAnalysis to run multiple experiments in comps's SSMT DockerWorker
    @pytest.mark.skip
    def test_ssmt_analysis_multiple_experiments(self):
        exp_id1 = "8bb8ae8f-793c-ea11-a2be-f0921c167861"  # comps2
        exp_id2 = "4ea96af7-1549-ea11-a2be-f0921c167861"  # comps2
        experiment_id = [exp_id1, exp_id2]
        analysis = PlatformAnalysis(platform=self.platform,
                                    experiment_ids=experiment_id,
                                    analyzers=[PopulationAnalyzer],
                                    analyzers_args=[{'name': 'anything'}],
                                    analysis_name=self.case_name,
                                    tags={'idmtools': self._testMethodName, 'WorkItem type': 'Docker'})

        analysis.analyze(check_status=True)
        wi = analysis.get_work_item()

        # validate output files
        local_output_path = "output"
        helpers.delete_existing_folder(local_output_path)
        out_filenames = ["output/population.png", "output/population.json", "WorkOrder.json"]
        self.platform.get_files_by_id(wi.uid, ItemType.WORKFLOW_ITEM, out_filenames, local_output_path)

        file_path = os.path.join(local_output_path, str(wi.uid))
        assert(os.path.exists(os.path.join(file_path, "output", "population.png")))
        assert(os.path.exists(os.path.join(file_path, "output", "population.json")))
        assert(os.path.exists(os.path.join(file_path, "WorkOrder.json")))
        with open(os.path.join(file_path, "WorkOrder.json"), 'r') as f:
            worker_order = json.load(f)
            print(worker_order)
            assert(worker_order['WorkItem_Type']=="DockerWorker")
            execution = worker_order['Execution']
            cmd_str = f"python platform_analysis_bootstrap.py {exp_id1},{exp_id2} population_analyzer.PopulationAnalyzer comps2"
            assert(execution['Command']==cmd_str)
