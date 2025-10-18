import copy
import json
import os
import pytest
import unittest
import time

from idmtools.assets import Asset, AssetCollection
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools_platform_comps.utils.singularity_build import SingularityBuildWorkItem
from emodpy.emod_task import EMODTask, logger
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
# add custom_reports to all the tests?
# especially sweeps


class TestEMODExperiment(unittest.TestCase):
    """
    This tests GENERIC_SIM from emod-common package
    """
    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self.__class__.__name__ + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.setup_custom_params()
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.platform = Platform(manifest.container_platform_name, num_retries=0)
        self.test_folder = helpers.make_test_directory(case_name=self.case_name)

    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if self.experiment:
                    f.write(f"The failed experiment can be viewed at {self.platform.endpoint}/#explore/"
                            f"Simulations?filters=ExperimentId={self.experiment.uid}")
                else:
                    f.write("The experiment was not created.")
            os.chdir(self.original_working_dir)
            helpers.close_logger(logger.parent)
        else:
            helpers.close_logger(logger.parent)
            if os.name == "nt":
                time.sleep(1)  # only needed for windows
            os.chdir(self.original_working_dir)
            helpers.delete_existing_folder(self.test_folder)

    @pytest.mark.container
    def test_experiment_from_task_with_task_from_default_simple(self):
        # https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/287
        """
            Test idmtools.entities.experiment.Experiment.from_task() with EMODTask.from_defaults()(all default values)
            with minimal config builder needed to run the sim, including Enable_Demographics_Builtin = 1
        """
        base_task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                           schema_path=self.builders.schema_path,
                                           config_builder=self.builders.config_builder,
                                           campaign_builder=self.builders.campaign_builder,
                                           report_builder=self.builders.reports_builder,
                                           demographics_builder=self.builders.demographics_builder)

        self.experiment = Experiment.from_task(task=base_task,
                                               name=self.case_name)

        # The last step is to call run() on the ExperimentManager to run the simulations.
        self.experiment.run(wait_until_done=True, platform=self.platform)
        self.assertTrue(self.experiment.succeeded)

        sim = self.experiment.simulations[0]
        files = self.platform.get_files(sim, ["config.json"])
        config_parameters = json.loads(files["config.json"])['parameters']

    def singularity_test(self, my_sif_path, embedded_python_scripts_path=None):
        """
        Helper function for various singularity tests
        """
        base_task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                           schema_path=self.builders.schema_path,
                                           config_builder=self.builders.config_builder,
                                           demographics_builder=self.builders.demographics_builder,
                                           embedded_python_scripts_path=embedded_python_scripts_path,
                                           report_builder=self.builders.reports_builder)
        # to add demographics file this way, you'd have to manually set the Demographics_Filenames
        # in the base_task.config.parameters
        # demographics_asset = Asset(self.builders.demographics_file)
        # base_task.common_assets.add_asset(demographics_asset)
        # base_task.config.parameters.Demographics_Filenames = [Path(self.builders.demographics_file).name]
        base_task.set_sif(my_sif_path, platform=self.platform)

        self.experiment = Experiment.from_task(base_task,
                                               self.case_name)

        self.experiment.run(wait_until_done=True,
                            platform=self.platform)

        self.assertTrue(self.experiment.succeeded)
        sim = self.experiment.simulations[0]
        files = self.platform.get_files(sim, ["stdout.txt"])
        stdout = files["stdout.txt"].decode("utf-8")
        self.assertIn("EMOD Disease Transmission Kernel", stdout)

    def download_singularity_ac(self, asset_collection_id, out_filename, output_path):
        # download sif from comps, currently not working, see issue:
        # https://github.com/InstituteforDiseaseModeling/idmtools/issues/1574
        #
        # self.platform.get_files_by_id(asset_collection_id, ItemType.ASSETCOLLECTION, out_filenames, output_path)
        # this is a workaround
        assets = AssetCollection.from_id(asset_collection_id, platform=self.platform).assets
        for asset in assets:
            if asset.filename == out_filename:
                asset.save_as(os.path.join(output_path, out_filename))
                break

    @pytest.mark.comps
    def test_experiment_from_task_with_singularity_from_local_file(self):
        """
        This checks that if you have a singularity image on your local machine,
        you can use it to run the simulation
        """
        self.platform = Platform(manifest.comps_platform_name)
        asset_collection_id = "bcf11390-75df-ef11-930c-f0921c167860"  # please update to the latest one
        out_filename = "dtk_run_rocky_py39.sif"
        self.download_singularity_ac(asset_collection_id, out_filename, self.test_folder)
        self.singularity_test(my_sif_path=os.path.join(self.test_folder, out_filename))

    @pytest.mark.comps
    def test_experiment_from_task_with_singularity(self):
        """
        This test checks that you can create a singularity image on Comps and use it to run the simulation
        """

        def make_sif(my_sif_path):
            """
            Creating a singularity image on Comps, only run when the image is not available on Comps.
            After creating the image, please use the Asset Collection ID of this image in the simulation.
            """
            sbi = SingularityBuildWorkItem(name="Creating dtk_run_rocky_py39.sif with def file",
                                           definition_file=os.path.join(self.builders.input_folder,
                                                                        "dtk_run_rocky_py39.def"),
                                           image_name="dtk_run_rocky_py39.sif")
            sbi.tags = dict(os="rockylinux", python=3.9)
            sbi.run(wait_until_done=True, platform=self.platform)
            self.assertTrue(sbi.succeeded)
            # Write asset id to file (needs to be *.id)
            sbi.asset_collection.to_id_file(my_sif_path)

        self.platform = Platform(manifest.comps_platform_name)
        this_sif_path = os.path.join(self.test_folder, "assets.id")
        # use the commented line to create a singularity image on Comps for the first time.
        make_sif(this_sif_path)
        self.singularity_test(this_sif_path)

    @pytest.mark.container
    def test_experiment_from_task_with_task_from_default_param_custom_cb(self):
        # https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/288
        """
            Test idmtools.entities.experiment.Experiment.from_task() with EMODTask.from_defaults() (set_param_fn=None)
        """

        def config_setting(config):
            if self.builders.config_builder: # when running emod-generic there is no config_builder
                config = self.builders.config_builder(config)
            config.parameters.Simulation_Duration = 7
            config.parameters.Enable_Demographics_Builtin = 1
            return config

        base_task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                           schema_path=self.builders.schema_path,
                                           config_builder=config_setting)

        self.experiment = Experiment.from_task(base_task,
                                               self.case_name)
        self.experiment.run(wait_until_done=True, platform=self.platform)

        self.assertTrue(self.experiment.succeeded)
        sim = self.experiment.simulations[0]
        files = self.platform.get_files(sim, ["config.json"])
        config_parameters = json.loads(files["config.json"])['parameters']
        self.assertEqual(config_parameters["Simulation_Duration"], 7)

    @pytest.mark.container
    def test_experiment_from_builder_with_task_from_default(self):
        """
            Test creating task from defaults and then creating an experiment from a builder
            and sweeping over the parameter "Run_Number"
            Test idmtools.entities.experiment.Experiment.from_builder() with EMODTask.from_defaults()
        """
        base_task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                           campaign_builder=self.builders.campaign_builder,
                                           schema_path=self.builders.schema_path,
                                           config_builder=self.builders.config_builder,
                                           demographics_builder=self.builders.demographics_builder,
                                           embedded_python_scripts_path=manifest.embedded_python_folder)

        builder = SimulationBuilder()
        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, self.num_sim))
        self.experiment = Experiment.from_builder(builder,
                                                  base_task,
                                                  name=self.case_name)
        self.experiment.run(wait_until_done=True, platform=self.platform)
        self.assertTrue(self.experiment.succeeded)
        for sim in self.experiment.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            self.assertEqual(config_parameters["Run_Number"], sim.tags["Run_Number"])

    @pytest.mark.container
    def test_simulations_manual_builder_with_task_from_file(self):
        """
            This test "passes" because I expect it to fail because of a known issue
            with initializing task with demographics file
            see: https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/843
            Test idmtools.entities.experiment.Experiment.simulations.append(sim) with EMODTask.from_files()
        """
        from idmtools.assets.errors import DuplicatedAssetError
        base_task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                        config_path=self.builders.config_file,
                                        campaign_path=self.builders.campaign_file,
                                        demographics_paths=self.builders.demographics_file,
                                        custom_reports_path=self.builders.custom_reports_file,
                                        embedded_python_scripts_path=manifest.embedded_python_folder)

        self.experiment = Experiment(name=self.case_name)

        base_sim = Simulation(task=base_task)
        for i in range(self.num_sim_long):
            sim = copy.deepcopy(base_sim)
            sim.task.config["Run_Number"] = i
            self.experiment.simulations.append(sim)

        with self.assertRaises(DuplicatedAssetError) as context:
            self.experiment.run(wait_until_done=True, platform=self.platform)
        self.assertTrue("demographics.json" in str(context.exception))

        #  uncomment when fixed
        # self.assertTrue(self.experiment.succeeded)
        #
        # for i, sim in enumerate(self.experiment.simulations):
        #     files = self.platform.get_files(sim, ["config.json"])
        #     config_parameters = json.loads(files["config.json"])['parameters']
        #     self.assertEqual(config_parameters["Run_Number"], i)

    @pytest.mark.container
    def test_simulations_manual_builder_with_task_from_file_workaround(self):
        """
            Workaround for the issue
            see: https://github.com/InstituteforDiseaseModeling/emodpy-old/issues/843
            Test idmtools.entities.experiment.Experiment.simulations.append(sim) with EMODTask.from_files()
        """
        # removing custom_reports from the config file
        with open(self.builders.config_file, "r") as f:
            config = json.load(f)
            config["parameters"]["Custom_Reports_Filename"] = ""
            with open("config.json", "w") as out:
                json.dump(config, out, indent=4)

        base_task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                        campaign_path=self.builders.campaign_file,
                                        config_path="config.json",
                                        embedded_python_scripts_path=manifest.embedded_python_folder)

        self.experiment = Experiment(name=self.case_name)
        base_sim = Simulation(task=base_task)
        for i in range(self.num_sim_long):
            sim = copy.deepcopy(base_sim)
            sim.task.config["Run_Number"] = i
            self.experiment.simulations.append(sim)

        self.experiment.simulations[0].task.common_assets.add_asset(Asset(self.builders.demographics_file))
        self.experiment.run(wait_until_done=True, platform=self.platform)

        self.assertTrue(self.experiment.succeeded)

        run_numbers = []
        for sim in self.experiment.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            run_numbers.append(config_parameters["Run_Number"])

        self.assertEqual(set(run_numbers), set(list(range(self.num_sim_long))))

    @pytest.mark.container
    def test_experiment_from_builder_with_task_from_file(self):
        """
            Test idmtools.entities.experiment.Experiment.from_builder() with EMODTask.from_files()
        """
        base_task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                        config_path=self.builders.config_file,
                                        custom_reports_path=self.builders.custom_reports_file,
                                        demographics_paths=self.builders.demographics_file)
        base_task.set_parameter("Enable_Interventions", 0)
        builder = SimulationBuilder()
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, self.num_sim_long))
        self.experiment = Experiment.from_builder(builder,
                                                  base_task,
                                                  name=self.case_name)
        self.experiment.run(wait_until_done=True, platform=self.platform)

        self.assertTrue(self.experiment.succeeded)
        for sim in self.experiment.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            self.assertEqual(config_parameters["Run_Number"], sim.tags["Run_Number"])


class TestEMODExperimentGeneric(TestEMODExperiment):
    """
    This tests GENERIC_SIM from emod-generic package
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon


if __name__ == "__main__":
    import unittest

    unittest.main()
