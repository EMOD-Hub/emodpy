import copy
import json
import os
from abc import ABC, abstractmethod
import pytest

from emod_api.config import from_schema as fs
from emod_api.interventions import outbreak as ob
from emod_api import campaign as camp
import emod_api.demographics.Demographics as Demographics

from idmtools.assets import Asset  # ,AssetCollection
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.core import ItemType
from idmtools.entities.experiment import Experiment
from idmtools.entities.iplatform import IPlatform
from idmtools.entities.simulation import Simulation
from idmtools_platform_comps.utils.singularity_build import SingularityBuildWorkItem

from emodpy.emod_task import EMODTask, add_ep4_from_path

from tests import manifest


emod_version = '2.20.0'
num_sim = 2
num_sim_long = 20  # to catch issue like config is not deep copied #251 and #238
sif_path = os.path.join(manifest.current_directory, "stage_sif.id")


@pytest.mark.emod
class EMODExperimentTest(ABC):
    """
    Base test class for idmtools.entities.experiment
    """

    @classmethod
    @abstractmethod
    def get_emod_binary(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_emod_schema(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_emod_config(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_platform(cls) -> IPlatform:
        pass

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)

    @pytest.mark.long
    def test_experiment_from_task_with_task_from_default2_simple(self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/287
        """
            Test idmtools.entities.experiment.Experiment.from_task() with EMODTask.from_default2()(all default values)
        """
        def set_param_fn(config):
            print("Setting params.")
            return config

        self.platform = Platform("SLURMStage")
        base_task = EMODTask.from_default2(eradication_path=self.get_emod_binary(),
                                           schema_path=self.get_emod_schema(),
                                           param_custom_cb=set_param_fn)
        # pl = RequirementsToAssetCollection(self.platform, requirements_path=manifest.requirements)
        base_task.set_sif(sif_path)

        base_task.set_parameter('Enable_Immunity', 0)
        e = Experiment.from_task(
            base_task,
            self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )

        # other_assets = AssetCollection.from_id(pl.run())
        # e.assets.add_assets(other_assets)
        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
        self.assertTrue(e.succeeded)

        for sim in e.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            self.assertEqual(config_parameters["Enable_Immunity"], 0)

    def download_singularity_ac(self, ac_id, out_filenames, output_path):
        self.platform.get_files_by_id(ac_id, ItemType.ASSETCOLLECTION, out_filenames, output_path)

    def singularity_test(self, my_sif_path, ep4_fn):
        def set_param_fn(config):
            print("Setting params.")
            return config

        base_task = EMODTask.from_default2(eradication_path=self.get_emod_binary(),
                                           schema_path=self.get_emod_schema(),
                                           param_custom_cb=set_param_fn,
                                           ep4_custom_cb=ep4_fn)

        demographics_asset = Asset(
            os.path.join(manifest.current_directory, "inputs", "demographics", "generic_demographics_singularity_test.json"),
            relative_path='python')
        base_task.common_assets.add_asset(demographics_asset)

        base_task.set_sif(my_sif_path)

        e = Experiment.from_task(
            base_task,
            self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 100}
        )

        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
        self.assertTrue(e.succeeded)
        for sim in e.simulations:
            files = self.platform.get_files(sim, ["stdout.txt"])
            stdout = files["stdout.txt"].decode("utf-8")
            self.assertIn("emod_api version =  1.11.7", stdout)

    @pytest.mark.long
    @pytest.mark.skip(reason="download AC from comps not supported currently")
    def test_experiment_from_task_with_singularity_from_local_file(self):
        self.platform = Platform("SLURMStage")

        # download sif from comps, currently not working, see issue: https://github.com/InstituteforDiseaseModeling/idmtools/issues/1574
        # ac_id = "3d366cfa-94c8-eb11-92dd-f0921c167860" # please update to the latest one
        # out_filenames = "dtk_runtime_CentOS.sif"
        # output_path = os.path.join(manifest.current_directory, "inputs/singularity")
        # self.download_singularity_ac(ac_id, out_filenames, output_path)

        def ep4_fn(task):
            task = add_ep4_from_path(task, os.path.join(manifest.current_directory, "inputs/ep4/singularity"))
            return task

        self.singularity_test(my_sif_path=os.path.join(manifest.current_directory, "inputs/singularity/emod_latest.sif"),
                              ep4_fn=ep4_fn)

    @pytest.mark.long
    @pytest.mark.skip(reason="CentOS.sif file is out of date, needs python 3.9 which is not compatible with CentOS")
    def test_experiment_from_task_with_singularity(self):
        def make_sif(my_sif_path):
            """
            Creating a singularity image on Comps, only run when the image is not available on Comps.
            After creating the image, please use the Asset Collection ID of this image in the simulation.
            """
            sbi = SingularityBuildWorkItem(name="Creating CentOS sif with def file",
                                           definition_file=os.path.join(manifest.current_directory, "inputs/singularity/CentOS_base.def"),
                                           image_name="CentOS.sif")
            sbi.tags = dict(os="CentOS")
            sbi.run(wait_until_done=True, platform=self.platform)
            if sbi.succeeded:
                # Write ID file
                sbi.asset_collection.to_id_file(my_sif_path)

        def ep4_fn(task):
            task = add_ep4_from_path(task, os.path.join(manifest.current_directory, "inputs/ep4/singularity"))
            return task

        self.platform = Platform("SLURMStage")
        # use the commented line to create a singularity image on Comps for the first time.
        # make_sif(sif_path)
        self.singularity_test(sif_path, ep4_fn)

    @pytest.mark.long
    def test_experiment_from_task_with_task_from_default2_param_custom_cb(self):  # https://github.com/InstituteforDiseaseModeling/emodpy/issues/288
        """
            Test idmtools.entities.experiment.Experiment.from_task() with EMODTask.from_default2() (set_param_fn=None)
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Simulation_Duration = 3
            return config

        config_path = "config_from_default2_1"
        self.platform = Platform("SLURMStage")
        base_task = EMODTask.from_default2(config_path=config_path,
                                           eradication_path=self.get_emod_binary(),
                                           schema_path=self.get_emod_schema(),
                                           param_custom_cb=set_param_fn)
        # pl = RequirementsToAssetCollection(self.platform, requirements_path=manifest.requirements)
        base_task.set_sif(sif_path)

        e = Experiment.from_task(
            base_task,
            self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )

        # other_assets = AssetCollection.from_id(pl.run())
        # e.assets.add_assets(other_assets)

        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
            # use system status as the exit code
        self.assertTrue(e.succeeded)
        # get the files in a platform agnostic way
        for sim in e.simulations:
            files = self.platform.get_files(sim, [config_path])
            config_parameters = json.loads(files[config_path])['parameters']
            self.assertEqual(config_parameters["Simulation_Duration"], 3)

    @pytest.mark.long
    def test_experiment_from_builder_with_task_from_default2(self):
        """
            Test idmtools.entities.experiment.Experiment.from_builder() with EMODTask.from_default2()
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 5
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 5
            config.parameters.Base_Infectivity_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Base_Infectivity_Constant = 1
            config.parameters.Simulation_Duration = 3
            return config

        def build_camp():
            event = ob.new_intervention(camp, 1, cases=4)
            camp.add(event)
            return camp

        def build_demo():
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            return demog

        print(f"Telling emod-api to use {self.get_emod_schema()} as schema.")
        ob.schema_path = self.get_emod_schema()
        camp.set_schema( self.get_emod_schema() )

        config_path = f"config_{self._testMethodName}.json"
        base_task = EMODTask.from_default2(config_path=config_path, eradication_path=self.get_emod_binary(),
                                           campaign_builder=build_camp, schema_path=self.get_emod_schema(),
                                           param_custom_cb=set_param_fn, ep4_custom_cb=None)

        # build tmpxxx.json for demographics file to avoid random pick wrong demographics.json file from other test
        base_task.create_demog_from_callback(build_demo, from_sweep=True)
        base_task.set_sif(sif_path)

        builder = SimulationBuilder()
        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim))
        e = Experiment.from_builder(
            builder, base_task,
            name=self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )
        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
            # use system status as the exit code
        self.assertTrue(e.succeeded)
        for sim in e.simulations:
            files = self.platform.get_files(sim, [config_path])
            config_parameters = json.loads(files[config_path])['parameters']
            self.assertEqual(config_parameters["Run_Number"], sim.tags["Run_Number"])

    @pytest.mark.long
    def test_simulations_manual_builder_with_task_from_file(self):
        """
            Test idmtools.entities.experiment.Experiment.simulations.append(sim) with EMODTask.from_files()
        """
        self.platform = Platform("SLURMStage")
        base_task = EMODTask.from_files(eradication_path=self.get_emod_binary(), config_path=self.get_emod_config(),
                                        ep4_path=None)
        base_task.set_sif(sif_path)
        base_task.set_parameter('Enable_Immunity', 0)
        e = Experiment(
            name=self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )

        base_sim = Simulation(task=base_task)
        for i in range(num_sim_long):
            sim = copy.deepcopy(base_sim)
            sim.task.common_assets = base_task.common_assets # workaround coz copy doesn't copy common_assets anymore.
            sim.task.set_parameter("Enable_Immunity", 0)
            e.simulations.append(sim)

        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
            # use system status as the exit code
        self.assertTrue(e.succeeded)
        for sim in e.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            self.assertEqual(config_parameters["Enable_Immunity"], 0)

    @pytest.mark.long
    def test_experiment_from_builder_with_task_from_file(self):
        """
            Test idmtools.entities.experiment.Experiment.from_builder() with EMODTask.from_files()
        """
        self.platform = Platform("SLURMStage")
        base_task = EMODTask.from_files(eradication_path=self.get_emod_binary(), config_path=self.get_emod_config(),
                                        ep4_path=None)
        base_task.set_sif(sif_path)
        builder = SimulationBuilder()
        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim_long))
        e = Experiment.from_builder(
            builder, base_task,
            name=self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )
        with self.platform as p:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)
            # use system status as the exit code

        self.assertTrue(e.succeeded)
        for sim in e.simulations:
            files = self.platform.get_files(sim, ["config.json"])
            config_parameters = json.loads(files["config.json"])['parameters']
            self.assertEqual(config_parameters["Run_Number"], sim.tags["Run_Number"])


@pytest.mark.comps
@pytest.mark.emod
class TestEMODExperimentLinux(EMODExperimentTest):
    """
    Test idmtools.entities.experiment with Linux Generic Emod build
    """

    @classmethod
    def setUpClass(cls):
        cls.platform: IPlatform = cls.get_platform()

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)

    @classmethod
    def get_emod_experiment(cls) -> EMODTask:
        return EMODTask

    @classmethod
    def get_platform(cls) -> IPlatform:
        return Platform('SLURM')

    @classmethod
    def get_emod_binary(cls) -> str:
        emod_binary_path = manifest.eradication_path_linux
        print(f"get_emod_binary returning {emod_binary_path}")
        return emod_binary_path

    @classmethod
    def get_emod_schema(cls) -> str:
        emod_schema_path = manifest.schema_path_linux
        print(f"get_emod_schema returning {emod_schema_path}")
        return emod_schema_path

    @classmethod
    def get_emod_config(cls) -> str:
        config_file_path = os.path.join(manifest.config_folder, 'config_emod_test.json')
        manifest.delete_existing_file(config_file_path)
        schema_path = manifest.schema_path_linux
        fs.SchemaConfigBuilder(schema_name=schema_path, config_out=config_file_path)
        print(f"get_emod_config returning {config_file_path}")
        return config_file_path

# try:

# @pytest.mark.docker
# @pytest.mark.emod
# class TestLocalPlatformEMOD(ITestWithPersistence, EMODPlatformTest):
#
#     def setUp(self) -> None:
#         self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
#         print(self.case_name)
#
#     @classmethod
#     def setUpClass(cls) -> None:
#         from idmtools_platform_local.infrastructure.service_manager import DockerServiceManager
#         from idmtools_platform_local.infrastructure.docker_io import DockerIO
#         import docker
#         cls.do = DockerIO()
#         cls.sdm = DockerServiceManager(docker.from_env())
#         cls.sdm.cleanup(True, True)
#         cls.do.cleanup(True)
#         cls.platform: IPlatform = cls.get_platform()
#
#     @classmethod
#     def tearDownClass(cls) -> None:
#         cls.sdm.cleanup(True, True)
#         cls.do.cleanup(True)
#
#     @classmethod
#     def get_emod_experiment(cls) -> IEMODExperiment:
#         return DockerEMODExperiment
#
#     @classmethod
#     def get_platform(cls) -> IPlatform:
#         return Platform('Local')
#
#     @classmethod
#     def get_emod_binary(cls) -> str:
#         return get_github_eradication_url(emod_version)


if __name__ == "__main__":
    import unittest
    unittest.main()
