# flake8: noqa W605,F821
import json
import os
import time
import pytest
import unittest
from unittest.mock import Mock
from idmtools.core import ItemType
from idmtools.assets import Asset, AssetCollection
from emodpy.emod_task import EMODTask, logger
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform

from pathlib import Path
import sys

parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers


class TestEMODTask(unittest.TestCase):
    """
        Tests for EMODTask
    """

    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.embedded_python_folder = manifest.embedded_python_folder
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.platform = Platform(manifest.container_platform_name, num_retries=0)
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()

    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if hasattr(self, "experiment") and hasattr(self.experiment, "uid"):
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


    @pytest.mark.container
    def test_from_files(self):
        """
        Test EMODTask.from_files
        These files were originally created with from_defaults and then saved to the inputs folder.

        """
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file,
                                   campaign_path=self.builders.campaign_file,
                                   demographics_paths=self.builders.demographics_file,
                                   custom_reports_path=self.builders.custom_reports_file,
                                   embedded_python_scripts_path=manifest.embedded_python_folder)

        experiment = Experiment.from_task(task, name=self.case_name)

        # Open all the files for comparison
        with open(self.builders.config_file, 'r') as fp:
            config = json.load(fp)["parameters"]
        with open(self.builders.campaign_file, 'r') as fp:
            campaign = json.load(fp)
        with open(self.builders.demographics_file, 'r') as fp:
            demographics = json.load(fp)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 5)
        # 3 dtk_*.py scripts, eradication and demographics
        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        if self.__class__.__name__ == "TestEMODTask":
            self.assertEqual(len(sim.assets), 3)
        else:  # Generic-Ongoing
            self.assertEqual(len(sim.assets), 2)
        self.assertIn('config.json', [a.filename for a in sim.assets])
        self.assertIn('campaign.json', [a.filename for a in sim.assets])

        # Assert No change for campaigns
        self.assertEqual(campaign['Events'], sim.task.campaign.events)

        # Assert No change for config except several parameters that are set implicitly
        self.assertEqual(sim.task.config["parameters"]['Campaign_Filename'], 'campaign.json')
        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 1)

        # config parameters that are expected to be updated to non-default values.
        self.assertEqual(sim.task.config["parameters"]["Demographics_Filenames"],
                         [os.path.basename(self.builders.demographics_file)])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 0)
        if self.__class__.__name__ == "TestEMODTask":
            self.assertEqual(sim.task.config["parameters"]["Age_Initialization_Distribution_Type"], 'DISTRIBUTION_SIMPLE')
        else:  # Generic-Ongoing
            self.assertEqual(sim.task.config["parameters"]["Age_Initialization_Distribution_Type"], 'DISTRIBUTION_COMPLEX')
        # assert two required parameters when demographics builtin is disabled.
        self.assertIn('Enable_Initial_Prevalence', sim.task.config["parameters"])

        if self.__class__.__name__ == "TestEMODTask":
            self.assertEqual(config, sim.task.config["parameters"])
        else:   # Generic-Ongoing basic doesn't have campaign, but it's added to the file when you have campaign from_file
            # Assert No change for config except several parameters that are set implicitly
            self.assertEqual(sim.task.config["parameters"]['Campaign_Filename'], 'campaign.json')
            self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 1)
            sim.task.config["parameters"].pop("Campaign_Filename")
            sim.task.config["parameters"]["Enable_Interventions"] = 0
            self.assertEqual(config, sim.task.config["parameters"])

        self.assertEqual(self.builders.demographics_file, experiment.assets[4].absolute_path)

    @pytest.mark.container
    def test_from_files_config_only(self):
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file_basic)

        with open(self.builders.config_file_basic, 'r') as fp:
            config = json.load(fp)["parameters"]

        self.assertDictEqual(config, task.config)

    @pytest.mark.container
    def test_from_files_valid_custom_report(self):
        """
        Test EMODTask.from_files with valid custom_reports.json
        We do not validate custom_reports.json when we use from_files
        just add it to the assets and set Custom_Reports_Filename in the config.
        """

        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file,
                                   campaign_path=self.builders.campaign_file,
                                   demographics_paths=self.builders.demographics_file,
                                   custom_reports_path=self.builders.custom_reports_file)

        self.experiment = Experiment.from_task(task, name=self.case_name)
        self.experiment.run(wait_until_done=True)
        self.assertTrue(self.experiment.succeeded)
        sim = self.experiment.simulations[0]
        file = self.platform.get_files(sim, ["output/ReportNodeDemographics.csv"])
        report = file["output/ReportNodeDemographics.csv"].decode("utf-8")
        self.assertIn("NodeID", report)

    @pytest.mark.container
    def test_from_default(self):
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      campaign_builder=self.builders.campaign_builder,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder,
                                      report_builder=self.builders.reports_builder)
        self.experiment = Experiment.from_task(task, name=self.case_name)

        # Open all the files for comparison
        with open(self.builders.config_file, 'r') as fp:
            config = json.load(fp)
        with open(self.builders.campaign_file, 'r') as fp:
            campaign = json.load(fp)
        with open(self.builders.demographics_file, 'r') as fp:
            demographics = json.load(fp)

        # check experiment common assets are as expected
        self.experiment.pre_creation(self.platform)
        assets_exp = 2 if manifest.container_platform_name == "ContainerPlatform" else 3
        self.assertEqual(len(self.experiment.assets), assets_exp)

        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in self.experiment.assets])
        self.assertIn("demographics.json", [a.filename for a in self.experiment.assets])

        sim = self.experiment.simulations[0]
        sim.pre_creation(self.platform)
        if self.__class__.__name__ == "TestEMODTask":
            self.assertEqual(len(sim.assets), 3)
            self.assertIn("campaign.json", [a.filename for a in sim.assets])
            self.assertIn("custom_reports.json", [a.filename for a in sim.assets])
            # Assert No change for campaigns
            self.assertEqual(campaign['Events'], sim.task.campaign.events)
            self.assertEqual(sim.task.config["parameters"]['Campaign_Filename'], "campaign.json")
            self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 1)
            mismatch = []
            for key, value in config["parameters"].items():
                if sim.task.config["parameters"][key] != value:
                    mismatch.append(f"{key} : {value} != {sim.task.config['parameters'][key]}")
            print(mismatch)
        else:  # Generic-Ongoing doesn't have campaign or custom reports
            self.assertEqual(len(sim.assets), 1)
        self.assertIn('config.json', [a.filename for a in sim.assets])

        # Assert No change for config except several parameters that are set implicitly
        self.assertEqual(sim.task.config["parameters"]["Demographics_Filenames"], ["demographics.json"])
        self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 0)


    @pytest.mark.container
    def test_from_default_schema_and_eradication_only(self):
        """
        Test EMODTask.from_defaults with schema and eradication only
        """
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        experiment = Experiment.from_task(task, name=self.case_name)

        task.gather_common_assets()

        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 1)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 1)
        self.assertIn('config.json', [a.filename for a in sim.assets])

        self.assertNotIn('Campaign_Filename', sim.task.config["parameters"])
        self.assertEqual(sim.task.config["parameters"]['Enable_Interventions'], 0)
        # self.assertNotIn("Demographics_Filenames", sim.task.config["parameters"]) this is in for emod-common
        if self.__class__.__name__ == "TestEMODTask":
            self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 0)
        else:  # Generic-Ongoing has Enable_Demographics_Builtin set to 1 by default
            self.assertEqual(sim.task.config["parameters"]["Enable_Demographics_Builtin"], 1)

    @pytest.mark.container
    def test_from_default_with_default_builder(self):
        """
        Test EMODTask.from_defaults with "default"/emdpty builder is not valid because EMOD's defaults do not create a
        valid config. There are several parameters that need to be set:
            config.parameters.Incubation_Period_Distribution = emod_enum.DistributionType.CONSTANT_DISTRIBUTION
            config.parameters.Incubation_Period_Constant = 5
            config.parameters.Infectious_Period_Distribution = emod_enum.DistributionType.CONSTANT_DISTRIBUTION
            config.parameters.Infectious_Period_Constant = 5
            config.parameters.Enable_Demographics_Builtin = 1
        """

        def config_builder(config):
            config = self.builders.config_builder(config)
            config.parameters.Enable_Demographics_Builtin = 1
            return config

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=config_builder)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()
        experiment = Experiment.from_task(task, name=self.case_name)
        self.assertEqual(task.eradication_path, self.builders.eradication_path)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        self.assertEqual(len(experiment.assets), 1)
        self.assertIn(self.builders.eradication_path, [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        self.assertEqual(len(sim.assets), 1)
        self.assertIn('config.json', [a.filename for a in sim.assets])

        self.assertNotIn('Campaign_Filename', sim.assets[0].content)
        #   self.assertNotIn("Demographics_Filenames", sim.assets[0].content) will be in here until cleanup is done when
        #   experiment is run
        config = json.loads(sim.assets[0].content)["parameters"]
        self.assertEqual(config['Enable_Interventions'], 0)
        self.assertEqual(config["Enable_Demographics_Builtin"], 1)

    @pytest.mark.container
    def test_eradication_file_as_asset(self):
        # testing from file
        task = EMODTask.from_files(eradication_path=None,
                                   config_path=self.builders.config_file_basic)
        task.common_assets.add_asset(self.builders.eradication_path)
        experiment = Experiment.from_task(task, name=self.case_name)

        # Run experiment
        self.platform.run_items(experiment)
        self.platform.wait_till_done(experiment, refresh_interval=1)
        self.assertTrue(experiment.succeeded, msg=f"{self.case_name} failed")

    @pytest.mark.container
    def test_existing_eradication_default(self):
        task2 = EMODTask.from_defaults(eradication_path=None,
                                       schema_path=self.builders.schema_path,
                                       config_builder=self.builders.config_builder,
                                       demographics_builder=self.builders.demographics_builder)
        task2.common_assets.add_asset(self.builders.eradication_path)

        experiment2 = Experiment.from_task(task2, name="Existing_Eradication_Default")
        self.platform.run_items(experiment2)
        self.platform.wait_till_done(experiment2, refresh_interval=1)
        assert experiment2.succeeded, "Eradication=None in from_default failed"

    @pytest.mark.container
    def test_error_builders_dont_return_right_objects(self):
        """
        Test that demographics object is not returned when demographics is not enabled
        """
        from emodpy.campaign.individual_intervention import BroadcastEvent

        with self.assertRaises(ValueError) as context:
            def demographics_builder():
                demographics = self.builders.demographics_builder()

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=demographics_builder)
        self.assertTrue("Something went wrong with demographics_builder, please make sure that the"
                        " demographics_builder function returns a Demographics object" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def demographics_builder2():
                from emod_api import campaign
                campaign.set_schema(self.builders.schema_path)
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=demographics_builder2)
        self.assertTrue("Something went wrong with demographics_builder, please make sure that "
                        "the demographics_builder function returns a Demographics object" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def config_builder(config):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=config_builder,
                                   demographics_builder=self.builders.demographics_builder)
        self.assertTrue("Something went wrong with config_builder, please make sure the config_builder"
                        " function returns a config object" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def config_builder2(config):
                from emod_api import campaign
                campaign.set_schema(self.builders.schema_path)
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=config_builder2,
                                   demographics_builder=self.builders.demographics_builder)
        self.assertTrue("Something went wrong with config_builder, please make sure the config_builder "
                        "function returns a config object" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def campaign_builder(campaign):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   campaign_builder=campaign_builder)
        self.assertTrue("Something went wrong with campaign_builder, please make sure that the campaign_builder "
                        "function returns the campaign module" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def campaign_builder2(campaign):
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   campaign_builder=campaign_builder2)
        self.assertTrue("Something went wrong with campaign_builder, please make sure that the "
                        "campaign_builder function returns the campaign module" in str(context.exception),
                        msg=str(context.exception))

        with self.assertRaises(ValueError) as context:
            def reporters_builder(reporters):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   report_builder=reporters_builder)
        self.assertTrue("Something went wrong with report_builder, please make sure the report_builder "
                        "function returns a Reporters object" in str(context.exception),
                        msg=str(context.exception))

    def skip_test_config_deepcopy(self):
        """
            Test copy.deepcopy(EMODTask.config) is working.
        """
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file,
                                   demographics_paths=self.builders.demographics_file,
                                   campaign_path=self.builders.campaign_file)
        import copy
        config = copy.deepcopy(task.config)

        with open(self.builders.config_file, 'r') as config_file:
            config_json = json.load(config_file)['parameters']
        self.assertEqual(config, config_json)

    @pytest.mark.comps
    def test_set_sif_function_with_sif_file(self):
        self.platform = Platform(manifest.comps_platform_name)
        asset_collection_id = "bcf11390-75df-ef11-930c-f0921c167860"  # please update to the latest one
        sif_name = "dtk_run_rocky_py39.sif"
        self.download_singularity_ac(asset_collection_id, sif_name, self.test_folder)
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder,
                                      embedded_python_scripts_path=self.embedded_python_folder)
        task.set_sif(os.path.join(self.test_folder, sif_name), self.platform)
        experiment = Experiment.from_task(task, name=self.case_name)
        experiment.run(platform=self.platform, wait_until_done=True)
        experiment_from_comps = self.platform.get_item(experiment.id, item_type=ItemType.EXPERIMENT, raw=True)
        comps_ac = self.platform.get_item(experiment_from_comps.configuration.asset_collection_id,
                                          item_type=ItemType.ASSETCOLLECTION)
        comps_sif_asset = [ac for ac in comps_ac if ac.filename == sif_name]
        self.assertTrue(len(comps_sif_asset), 1)

    @pytest.mark.comps
    def test_set_sif_function_with_sif_id(self):
        self.platform = Platform(manifest.comps_platform_name, num_retries=0)
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        experiment = Experiment.from_task(task, name=self.case_name)
        experiment.run(platform=self.platform, wait_until_done=True)
        experiment_from_comps = self.platform.get_item(experiment.id, item_type=ItemType.EXPERIMENT, raw=True)
        comps_ac = self.platform.get_item(experiment_from_comps.configuration.asset_collection_id,
                                          item_type=ItemType.ASSETCOLLECTION)
        comps_sif_asset = [ac for ac in comps_ac if ac.filename == "dtk_run_rocky_py39.sif"]
        self.assertTrue(len(comps_sif_asset), 1)

    @pytest.mark.comps
    def test_set_sif_function_with_comps_with_bad_filename(self):
        self.platform = Platform(manifest.comps_platform_name)
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        self.assertRaises(ValueError, task.set_sif, path_to_sif="my_id.txt", platform=self.platform)

    @pytest.mark.container
    def test_set_sif_function_with_slurm_file_process_platform(self):
        class FilePlatform:
            pass

        class SlurmPlatform:
            pass

        class ProcessPlatform:
            pass

        # successful cases
        for platform in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                          schema_path=self.builders.schema_path,
                                          config_builder=self.builders.config_builder,
                                          demographics_builder=self.builders.demographics_builder)
            fake_platform = Mock(spec=platform)
            task.set_sif(path_to_sif="my_sif.sif", platform=fake_platform)
            experiment = Experiment.from_task(task, name=self.case_name)
            experiment.post_creation(fake_platform)
            self.assertEqual(str(task.sif_path), "my_sif.sif")

        # used a .id file, error!
        for platform in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                          schema_path=self.builders.schema_path)
            fake_platform = Mock(spec=platform)
            self.assertRaises(ValueError, task.set_sif, path_to_sif="my_id.id", platform=fake_platform)

        # used a file with an odd suffix. Error!
        for platform in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                          schema_path=self.builders.schema_path)
            fake_platform = Mock(spec=platform)
            self.assertRaises(ValueError, task.set_sif, path_to_sif="my_id.txt", platform=fake_platform)

    @pytest.mark.container
    def test_set_sif_with_unknown_platforms(self):
        # This is an error! We have no idea how to handle sifs with new platforms without new logic.
        class DoesNotExistPlatform:
            pass

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        fake_platform = Mock(spec=DoesNotExistPlatform)
        self.assertRaises(ValueError, task.set_sif, path_to_sif="my_sif.sif", platform=fake_platform)

    @pytest.mark.container
    def test_set_sif_with_container_platform(self):
        # Nothing happens in this case, just a warning
        class ContainerPlatform:
            pass

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        fake_platform = Mock(spec=ContainerPlatform)
        self.assertWarns(RuntimeWarning, task.set_sif, path_to_sif="my_sif.sif", platform=fake_platform)
        self.assertEqual(task.sif_filename, None)
        self.assertEqual(task.sif_path, None)

    @pytest.mark.container
    def test_add_py_path(self):
        """
        Test add_py_path, verifies that the path is added to the command string.
        """
        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        task.add_embedded_python_scripts_from_path(self.embedded_python_folder)
        virtual_path = 'venv/lib/python3.9/site-packages/'
        task.add_py_path(virtual_path)

        task.pre_creation(Simulation(), self.platform)
        task.gather_common_assets()

        self.assertTrue(task.use_embedded_python)
        self.assertIn(f"--python-script-path './Assets/python;{virtual_path}'", str(task.command))


class TestEMODTaskGeneric(TestEMODTask):
    """
    Testing using Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric

    @pytest.mark.skip("emodpy does not support reporters for Generic-Ongoing yet.")
    def test_from_files_valid_custom_report(self):
        pass


if __name__ == "__main__":
    unittest.main()
