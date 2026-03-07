import json
import os
import pytest

from emodpy.emod_task import EMODTask, logger
from idmtools.entities.experiment import Experiment
from idmtools.entities.simulation import Simulation
from idmtools.core.platform_factory import Platform

from tests import manifest
from tests import helpers


class TestEMODTask():
    """
        Tests for EMODTask
    """
    def setup_custom_params(self):
        self.builders = helpers.BuildersCommon

    @pytest.fixture(autouse=True)
    def run_every_test(self, request) -> None:
        # Pre-test
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + request.node.name
        self.embedded_python_folder = manifest.embedded_python_folder
        self.original_working_dir = os.getcwd()
        self.task: EMODTask
        self.experiment: Experiment
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.platform = Platform(manifest.container_platform_name, job_directory=self.test_folder,
                                 docker_image=manifest.container_platform_image, num_retries=0)
        self.setup_custom_params()

        # Run test
        yield

        # Post-test
        os.chdir(self.original_working_dir)
        helpers.close_logger(logger.parent)


class TestEMODTaskContainerPlatform(TestEMODTask):

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
            json.load(fp)

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        assert (len(experiment.assets) == 5)
        # 3 dtk_*.py scripts, eradication and demographics
        assert (task.eradication_path == self.builders.eradication_path)
        assert (self.builders.eradication_path in [a.absolute_path for a in task.common_assets.assets])
        assert (self.builders.eradication_path in [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        assert (len(sim.assets) == 3)
        assert ('config.json' in [a.filename for a in sim.assets])
        assert ('campaign.json' in [a.filename for a in sim.assets])

        # Assert No change for campaigns
        assert (campaign['Events'] == sim.task.campaign.events)

        # Assert No change for config except several parameters that are set implicitly
        assert (sim.task.config["parameters"]['Campaign_Filename'] == 'campaign.json')
        assert (sim.task.config["parameters"]['Enable_Interventions'] == 1)

        # config parameters that are expected to be updated to non-default values.
        assert (sim.task.config["parameters"]["Demographics_Filenames"] == [os.path.basename(self.builders.demographics_file)])
        assert (sim.task.config["parameters"]["Enable_Demographics_Builtin"] == 0)
        assert (sim.task.config["parameters"]["Age_Initialization_Distribution_Type"] == 'DISTRIBUTION_SIMPLE')
        assert ('Enable_Initial_Prevalence' in sim.task.config["parameters"])

        assert (config == sim.task.config["parameters"])
        assert (self.builders.demographics_file == experiment.assets[4].absolute_path)

    @pytest.mark.container
    def test_from_files_config_only(self):
        task = EMODTask.from_files(eradication_path=self.builders.eradication_path,
                                   config_path=self.builders.config_file_basic)

        with open(self.builders.config_file_basic, 'r') as fp:
            config = json.load(fp)["parameters"]

        assert (config == task.config)

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
        self.experiment.pre_creation(self.platform)
        self.experiment.run(wait_until_done=True)
        assert (self.experiment.succeeded)
        sim = self.experiment.simulations[0]
        file = self.platform.get_files(sim, ["output/ReportNodeDemographics.csv"])
        report = file["output/ReportNodeDemographics.csv"].decode("utf-8")
        assert ("NodeID" in report)

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
            json.load(fp)

        # check experiment common assets are as expected
        self.experiment.pre_creation(self.platform)
        assets_exp = 2 if manifest.container_platform_name == manifest.container_platform_name else 3
        assert (len(self.experiment.assets) == assets_exp)
        assert (task.eradication_path == self.builders.eradication_path)
        assert (self.builders.eradication_path in [a.absolute_path for a in task.common_assets.assets])
        assert (self.builders.eradication_path in [a.absolute_path for a in self.experiment.assets])
        assert ("demographics.json" in [a.filename for a in self.experiment.assets])

        sim = self.experiment.simulations[0]
        sim.pre_creation(self.platform)
        assert (len(sim.assets) == 3)
        assert ("campaign.json" in [a.filename for a in sim.assets])
        assert ("custom_reports.json" in [a.filename for a in sim.assets])
        assert (campaign['Events'] == sim.task.campaign.events)
        assert (sim.task.config["parameters"]['Campaign_Filename'] == "campaign.json")
        assert (sim.task.config["parameters"]['Enable_Interventions'] == 1)
        mismatch = []
        for key, value in config["parameters"].items():
            if sim.task.config["parameters"][key] != value:
                mismatch.append(f"{key} : {value} != {sim.task.config['parameters'][key]}")
        print(mismatch)
        assert ('config.json' in [a.filename for a in sim.assets])

        # Assert No change for config except several parameters that are set implicitly
        assert (sim.task.config["parameters"]["Demographics_Filenames"] == ["demographics.json"])
        assert (sim.task.config["parameters"]["Enable_Demographics_Builtin"] == 0)

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

        assert (task.eradication_path == self.builders.eradication_path)
        assert (self.builders.eradication_path in [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        assert (len(experiment.assets) == 1)
        assert (self.builders.eradication_path in [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        assert (len(sim.assets) == 1)
        assert ('config.json' in [a.filename for a in sim.assets])
        assert ('Campaign_Filename' not in sim.task.config["parameters"])
        assert (sim.task.config["parameters"]['Enable_Interventions'] == 0)
        assert (sim.task.config["parameters"]["Enable_Demographics_Builtin"] == 0)

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
        assert (task.eradication_path == self.builders.eradication_path)
        assert (self.builders.eradication_path in [a.absolute_path for a in task.common_assets.assets])

        # check experiment common assets are as expected
        experiment.pre_creation(self.platform)
        assert (len(experiment.assets) == 1)
        assert (self.builders.eradication_path in [a.absolute_path for a in experiment.assets])

        sim = experiment.simulations[0]
        sim.pre_creation(self.platform)
        assert (len(sim.assets) == 1)
        assert ('config.json' in [a.filename for a in sim.assets])
        assert ('Campaign_Filename' not in sim.assets[0].content)
        config = json.loads(sim.assets[0].content)["parameters"]
        assert (config['Enable_Interventions'] == 0)
        assert (config["Enable_Demographics_Builtin"] == 1)

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
        assert (experiment.succeeded)

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
        assert (experiment2.succeeded)

    @pytest.mark.container
    def test_error_builders_dont_return_right_objects(self):
        """
        Test that demographics object is not returned when demographics is not enabled
        """
        from emodpy.campaign.individual_intervention import BroadcastEvent

        with pytest.raises(ValueError) as e_info:
            def demographics_builder():
                self.builders.demographics_builder()

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=demographics_builder)
        assert ("Something went wrong with demographics_builder, please make sure that the demographics_builder function returns a Demographics object" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def demographics_builder2():
                from emod_api import campaign
                campaign.set_schema(self.builders.schema_path)
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=demographics_builder2)
        assert ("Something went wrong with demographics_builder, please make sure that the demographics_builder function returns a Demographics object" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def config_builder(config):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=config_builder,
                                   demographics_builder=self.builders.demographics_builder)
        assert ("Something went wrong with config_builder, please make sure the config_builder function returns a config object" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def config_builder2(config):
                from emod_api import campaign
                campaign.set_schema(self.builders.schema_path)
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=config_builder2,
                                   demographics_builder=self.builders.demographics_builder)
        assert ("Something went wrong with config_builder, please make sure the config_builder function returns a config object" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def campaign_builder(campaign):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   campaign_builder=campaign_builder)
        assert ("Something went wrong with campaign_builder, please make sure that the campaign_builder function returns the campaign module" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def campaign_builder2(campaign):
                return BroadcastEvent(campaign=campaign, broadcast_event="NoTrigger")

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   campaign_builder=campaign_builder2)
        assert ("Something went wrong with campaign_builder, please make sure that the campaign_builder function returns the campaign module" in str(e_info))

        with pytest.raises(ValueError) as e_info:
            def reporters_builder(reporters):
                return None

            EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                   schema_path=self.builders.schema_path,
                                   config_builder=self.builders.config_builder,
                                   demographics_builder=self.builders.demographics_builder,
                                   report_builder=reporters_builder)
        assert ("Something went wrong with report_builder, please make sure the report_builder function returns a Reporters object" in str(e_info))

    @pytest.mark.skip
    def test_skip_config_deepcopy(self):
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
        assert (config == config_json)

    @pytest.mark.container
    def test_set_sif_function_with_slurm_file_process_platform(self):
        class FilePlatform:
            pass

        class SlurmPlatform:
            pass

        class ProcessPlatform:
            pass

        # successful cases
        for plat_class in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                          schema_path=self.builders.schema_path,
                                          config_builder=self.builders.config_builder,
                                          demographics_builder=self.builders.demographics_builder)
            fake_platform = plat_class()
            task.set_sif(path_to_sif="my_sif.sif", platform=fake_platform)
            experiment = Experiment.from_task(task, name=self.case_name)
            experiment.post_creation(fake_platform)
            assert (str(task.sif_path) == "my_sif.sif")

        # used a .id file, error!
        for plat_class in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            with pytest.raises(ValueError) as e_info:
                task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                              schema_path=self.builders.schema_path)
                fake_platform = plat_class()
                task.set_sif(path_to_sif="my_id.id", platform=fake_platform)
            assert (e_info)

        # used a file with an odd suffix. Error!
        for plat_class in [FilePlatform, SlurmPlatform, ProcessPlatform]:
            with pytest.raises(ValueError) as e_info:
                task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                              schema_path=self.builders.schema_path)
                fake_platform = plat_class()
                task.set_sif(path_to_sif="my_id.txt", platform=fake_platform)
            assert (e_info)

    @pytest.mark.container
    def test_set_sif_with_unknown_platforms(self):
        # This is an error! We have no idea how to handle sifs with new platforms without new logic.
        class DoesNotExistPlatform:
            pass

        with pytest.raises(ValueError) as e_info:
            task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                          schema_path=self.builders.schema_path,
                                          config_builder=self.builders.config_builder,
                                          demographics_builder=self.builders.demographics_builder)
            fake_platform = DoesNotExistPlatform()
            task.set_sif(path_to_sif="my_sif.sif", platform=fake_platform)
        assert (e_info)

    @pytest.mark.container
    def test_set_sif_with_container_platform(self):
        # Nothing happens in this case, just a warning
        class ContainerPlatform:
            pass

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        fake_platform = ContainerPlatform()
        pytest.warns(RuntimeWarning, task.set_sif, path_to_sif="my_sif.sif", platform=fake_platform)
        assert (task.sif_filename is None)
        assert (task.sif_path is None)

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

        assert (task.use_embedded_python)
        assert (f"--python-script-path './Assets/python;{virtual_path}'" in str(task.command))


class TestEMODTaskGeneric(TestEMODTask):
    """
    Testing using Generic-Ongoing EMOD
    """

    def setup_custom_params(self):
        self.builders = helpers.BuildersGeneric

    @pytest.mark.skip("emodpy does not support reporters for Generic-Ongoing yet.")
    def test_from_files_valid_custom_report(self):
        pass
