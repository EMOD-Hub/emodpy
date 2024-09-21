import os
from abc import ABC, abstractmethod
from functools import partial
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
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence

from emodpy.emod_task import EMODTask
from pathlib import Path

from tests import manifest2
from . import manifest

num_sim = 3
num_sim_long = 20  # to catch issue like config is not deep copied #251 and #238
sif_path = os.path.join(manifest.current_directory, "stage_sif.id")


def param_update(simulation, param, value):
    return simulation.set_parameter(param, value)


def param_update_task(simulation, param, value):
    return simulation.task.set_parameter(param, value)


def add_ep4_post(task):
    asset = Asset(os.path.join(manifest.ep4_path, "dtk_post_process.py"), relative_path="python")
    print("adding dtk_post_process.py asset ")
    task.common_assets.add_asset(asset)
    return task


@pytest.mark.emod
class EMODExperimentTest(ABC):

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

    def download_singularity_ac(self, ac_id, out_filenames, output_path):
        self.platform.get_files_by_id(ac_id, ItemType.ASSETCOLLECTION, out_filenames, output_path)

    def validate_results_db(self, resdbfile, expectedrows, expectedcols):
        import sqlite3
        self.assertTrue(Path(resdbfile).exists())
        conn = sqlite3.connect(resdbfile)
        cur = conn.cursor()
        # For validation of rows
        cur.execute("SELECT Count() FROM results")
        numberOfRows = cur.fetchone()[0]
        self.assertEqual(expectedrows, numberOfRows)
        # For validation of columns
        cur.execute("PRAGMA table_info(results)")
        numberOfColumns = len(cur.fetchall())
        self.assertEqual(expectedcols, numberOfColumns)

    def debugOnly_test_function_test(self):
        id = "282e5918-4f29-ed11-92ee-f0921c167860"
        resfile = Path(os.path.join(os.path.curdir, id, "results.db"))
        if resfile.exists():
            os.remove(resfile)
        EMODTask.cache_experiment_metadata_in_sql(exp_id=id)
        self.validate_results_db(resfile, 32, 4)

    @pytest.mark.long
    def test_e2e_experiment_from_default2_with_misc_features(self):
        num_sim = 2

        def set_param_fn(config):
            print("Setting params.")
            # region SettingParams
            # Incubation Period
            config.parameters.Incubation_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Incubation_Period_Constant = 5
            # Infectious Period
            config.parameters.Infectious_Period_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Infectious_Period_Constant = 5
            # Base Infectivity
            config.parameters.Base_Infectivity_Distribution = "CONSTANT_DISTRIBUTION"
            config.parameters.Base_Infectivity_Constant = 1
            # endregion

            config.parameters.Simulation_Duration = 3
            return config

        def build_camp():
            event = ob.new_intervention(camp, 1, cases=4)
            camp.add(event, first=True)
            return camp

        def build_demo():
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            return demog

        ob.schema_path = self.get_emod_schema()
        camp.schema_path = self.get_emod_schema()

        config_path = f"config_{self._testMethodName}.json"
        base_task = EMODTask.from_default2(config_path=config_path, eradication_path=self.get_emod_binary(),
                                           campaign_builder=build_camp, schema_path=self.get_emod_schema(),
                                           param_custom_cb=set_param_fn, ep4_custom_cb=add_ep4_post,
                                           demog_builder=build_demo)
        base_task.set_sif(sif_path)

        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"   
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim))

        # Custom 
        builder.add_sweep_definition(partial(param_update_task, param="numeric_values"), [123, 234])
        builder.add_sweep_definition(partial(param_update_task, param="bool_values"), [True, False])
        builder.add_sweep_definition(partial(param_update_task, param="hyphen-tags-numeric-values"), [.001, .06])
        builder.add_sweep_definition(partial(param_update_task, param="hyphen-tags-alpha-values"), ["a", "b"])

        e = Experiment.from_builder(
            builder, base_task,
            name=self.case_name,
            tags={"emodpy": "emodpy-automation", "string_tag": "test", "number_tag": 123}
        )
        with self.platform as p:
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)

        self.assertTrue(e.succeeded)
        EMODTask.cache_experiment_metadata_in_sql(exp_id=e.id)
        resfile = Path(os.path.join(os.path.curdir, e.id, "results.db"))
        print(resfile)
        self.assertTrue(resfile.exists())
        self.validate_results_db(resfile, 32, 4)

    @pytest.mark.long
    def test_e2e_experiment_from_files_with_misc_features(self):

        self.platform = Platform("SLURMStage")
        base_task = EMODTask.from_files(eradication_path=self.get_emod_binary(), 
                                        config_path=self.get_emod_config(),
                                        ep4_path=os.path.join(manifest2.current_directory, "inputs", "ep4", "e2e"))
        base_task.set_sif(sif_path)
        builder = SimulationBuilder()

        # Sweep parameter "Run_Number"
        builder.add_sweep_definition(EMODTask.set_parameter_partial("Run_Number"), range(0, num_sim_long))

        e = Experiment.from_builder(
            builder, base_task,
            name=self.case_name,
            tags={"emodpy": "emodpy-tag", "bool_tag": True, "string_tag": "test", "number_tag": 123}
        )
        with self.platform as p:
            e.run(platform=p)
            p.wait_till_done(e, refresh_interval=1)

        self.assertTrue(e.succeeded)
        EMODTask.cache_experiment_metadata_in_sql(exp_id=e.id)
        resfile = Path(os.path.join(os.path.curdir, e.id, "results.db"))
        print(resfile)
        self.assertTrue(resfile.exists())


@pytest.mark.comps
@pytest.mark.emod
class TestEMODExperimentLinux(ITestWithPersistence, EMODExperimentTest):

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


if __name__ == "__main__":
    import unittest
    unittest.main()
