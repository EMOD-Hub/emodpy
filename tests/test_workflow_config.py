import os
import pytest
import shutil
from functools import partial
import json

from emod_api.config import default_from_schema_no_validation as dfs
from emod_api.config import from_schema as fs
from emod_api.config import from_overrides as fo

from emod_api.schema import get_schema as gs

from idmtools.entities.experiment import Experiment
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform

from emodpy.emod_task import EMODTask
from emodpy.utils import download_latest_bamboo, download_latest_schema, EradicationBambooBuilds, bamboo_api_login

# import sys
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from tests import manifest

sif_path = manifest.sft_id_file

num_seeds = 2


def param_update(simulation, param, value):
    return simulation.task.set_parameter(param, value)


set_Run_Number = partial(param_update, param="Run_Number")


# bamboo_api_login() only work in console
# Please run this test from console for the first time or run 'test_download_from_bamboo.py' from console before
# running this test
class TestWorkflowConfig():
    """
        Base test class to test emod_api.config in a workflow
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_WIN
        self.eradication_path = manifest.eradication_path_win
        self.schema_path = os.path.join(manifest.config_folder, f"generic_schema_{self._testMethodName}.json")
        self.config_file = os.path.join(manifest.config_folder, f"generic_config_{self._testMethodName}.json")
        self.default_config_file = "default_config.json"
        self.comps_platform = 'COMPS2'

    def setUp(self) -> None:
        self.is_singularity = False
        self.define_test_environment()
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.get_exe_from_bamboo()
        self.generate_schema()
        self.platform = Platform(self.comps_platform)

    def get_exe_from_bamboo(self):
        if not os.path.isfile(self.eradication_path):
            bamboo_api_login()
            print(f"Getting Eradication from bamboo for plan {self.plan}.")
            eradication_path_bamboo = download_latest_bamboo(
                plan=self.plan,
                scheduled_builds_only=False
            )
            shutil.move(eradication_path_bamboo, self.eradication_path)
        else:
            print(f"{self.eradication_path} already exists, no need to get from bamboo.")

    def generate_schema(self):
        manifest.delete_existing_file(self.schema_path)
        gs.dtk_to_schema(self.eradication_path, path_to_write_schema=self.schema_path)
        self.assertTrue(os.path.isfile(self.schema_path))

    def generate_config_from_builder(self, model):
        manifest.delete_existing_file(self.config_file)
        fs.SchemaConfigBuilder(schema_name=self.schema_path, config_out=self.config_file, model=model)
        self.assertTrue(os.path.isfile(self.config_file), msg=f"{self.config_file} doesn't exist.")

    def generate_default_config(self, default_config):
        manifest.delete_existing_file(default_config)
        print("get_default_from_schema")
        dfs.get_default_config_from_schema(self.schema_path, output_filename=self.default_config_file)
        print("move write_default_from_schema")
        shutil.move(self.default_config_file, default_config)
        self.assertTrue(os.path.isfile(default_config), msg=f"{default_config} doesn't exist.")

    def run_exp(self, task):
        # Create simulation sweep with builder
        builder = SimulationBuilder()
        builder.add_sweep_definition(set_Run_Number, range(num_seeds))

        experiment = Experiment.from_builder(builder, task, name=self._testMethodName)

        print("Run experiment...")
        self.platform.run_items(experiment)

        print("Wait experiment to finish...")
        self.platform.wait_till_done(experiment)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")

    def config_from_builder_test(self, model='GENERIC_SIM'):  # this workflow may be deprecated later
        # and we will use the workflow below 'config_from_default_and_set_fn_test' as our preferred workflow
        """
            Test a default config from fs.SchemaConfigBuilder() can be consumed by Eradication.
        """
        self.generate_config_from_builder(model=model)
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path, ep4_path=None)
        if self.is_singularity:
            task.set_sif(sif_path)
        self.run_exp(task)

    def config_from_default_and_set_fn_test(self):  # This is our preferred workflow which support the depends-on logic
        """
            Test a config from dfs.write_config_from_default_and_params() can work with a default config from
            dfs.write_default_from_schema() and set_param_fn; can be consumed by Eradication.
        """
        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Simulation_Duration = 10
            # config.parameters.Default_Geography_Initial_Node_Population = 100
            # config.parameters.Default_Geography_Torus_Size = 10
            # config.parameters.x_Base_Population = 1
            return config

        self.generate_default_config(self.config_file)
        dfs.write_config_from_default_and_params(self.config_file, set_param_fn, self.config_file)
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   ep4_path=None)
        if self.is_singularity:
            task.set_sif(sif_path)
        self.run_exp(task)

    def config_from_po_test(self, config_filename="config_from_po.json"):
        """
            Test a config from fo.flattenConfig() with a param_overrides.json and a default config from
            dfs.write_default_from_schema() can be consumed by Eradication.
        """
        # generate default config
        default_config = os.path.join(manifest.config_folder, self.default_config_file)
        self.generate_default_config(default_config)
        with open(default_config, 'r') as default_config_file:
            default_config_obj = json.load(default_config_file)
        # remove schema object
        default_config_obj['parameters'].pop("schema")
        with open(default_config, 'w') as default_config_file:
            json.dump(default_config_obj, default_config_file, indent=4)

        po_filename = 'param_overrides.json'
        self.config_file = os.path.join(manifest.config_folder, config_filename)
        manifest.delete_existing_file(self.config_file)

        fo.flattenConfig(configjson_path=os.path.join(manifest.config_folder, po_filename),
                         new_config_name=config_filename)

        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   ep4_path=None)
        if self.is_singularity:
            task.set_sif(sif_path)
        self.run_exp(task)

    def config_from_task_update_test(self, config_filename=None):
        if config_filename is None:
            config_filename = self.config_file
        # this workflow may be deprecated later
        # and we will use the workflow 'config_from_default_and_set_fn_test' as our preferred workflow
        """
            Test the current way of updating the config parameter with task.update_parameters() with work a default
            config from fs.SchemaConfigBuilder() and can be consumed by Eradication.
        """
        def standard_cb_updates(my_task: EMODTask):
            my_task.update_parameters({
                'Simulation_Duration': 10
            })

        self.config_file = os.path.join(manifest.config_folder, config_filename)
        self.generate_config_from_builder(model='GENERIC_SIM')
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   ep4_path=None)
        if self.is_singularity:
            task.set_sif(sif_path)
        standard_cb_updates(task)
        self.run_exp(task)

    def config_from_defaults(self, model='GENERIC_SIM'):  # This is our preferred workflow which support the depends-on logic
        """
            Test from_default2() with schema and Eradication.
        """
        print("This test is supposed to use the EMODTask.from_defaults(2) that is a pass through to emod-api defaults.")

        def set_param_fn(config):
            print("Setting params.")
            config.parameters.Incubation_Period_Exponential = 2
            config.parameters.Infectious_Period_Constant = 0
            config.parameters.Base_Infectivity_Constant = 0.2
            config.parameters.Base_Mortality = 0
            config.parameters.Simulation_Duration = 10
            config.parameters.Simulation_Type = model
            return config
        print(f"The config.json should be in {self.config_file}.")

        from emod_api.interventions import outbreak as ob
        from emod_api import campaign as camp 

        print(f"Telling emod-api to use {self.schema_path} as schema.")
        camp.set_schema( self.schema_path )  # this is brittle. We have to make sure schema exists by now but main way to gen schema is call to from_default2.... )

        # ToDo: when #276 is resolved, change campaign_builder=build_camp to campaign_builder=camp
        def build_camp():
            event = ob.new_intervention(camp, 1, cases=4)
            camp.add(event)
            # We are saving and reloading. Maybe there's an even better way? But even an outbreak seeding does not belong in the EMODTask.
            # camp_path = "campaign.json"
            # camp.save(camp_path)
            return camp

        task = EMODTask.from_default2(config_path=self.config_file, eradication_path=self.eradication_path,
                                      campaign_builder=build_camp, schema_path=self.schema_path,
                                      param_custom_cb=set_param_fn, ep4_custom_cb=None)
        if self.is_singularity:
            task.set_sif(sif_path)
        self.run_exp(task)


@pytest.mark.emod
class TestWorkflowConfigWin(TestWorkflowConfig):
    """
        Tested with Windows version of Generic Eradication
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_WIN
        self.eradication_path = manifest.eradication_path_win
        self.schema_path = os.path.join(manifest.config_folder, f"generic_schema_win_{self._testMethodName}.json")
        self.config_file = os.path.join(manifest.config_folder, f"generic_config_win_{self._testMethodName}.json")
        self.default_config_file = f"default_config_{self._testMethodName}.json"
        self.comps_platform = 'COMPS2'

    def generate_schema(self):
        print('Using schema.json downloaded from test_download_from_bamboo.py for test')
        self.schema_path = manifest.schema_path_win
        if not os.path.isfile(self.schema_path):
            download_latest_schema(plan=self.plan, scheduled_builds_only=False, out_path=self.schema_path)

    def test_1_config_from_builder_win(self):
        super().config_from_builder_test()

    def test_2_config_from_default_and_set_fn_win(self):
        super().config_from_default_and_set_fn_test()

    @pytest.skip(reason="TEST: broken test when ran using pytest-xdist #604", allow_module_level=True)
    def test_3_config_from_po_win(self):
        super().config_from_po_test()

    def test_4_config_from_task_update_win(self):
        super().config_from_task_update_test()

    def test_5_config_from_task_default_win(self):
        # if platform == "linux" or platform == "linux2":
        #     print('OS is Linux, skip test.')
        #     pass
        # else:
        #     super().config_from_defaults()
        super().config_from_defaults()


@pytest.mark.emod
class TestWorkflowConfigLinux(TestWorkflowConfig):
    """
        Tested with Linux version of Generic Eradication
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_LINUX
        self.eradication_path = manifest.eradication_path_linux
        self.schema_path = os.path.join(manifest.config_folder, f"generic_schema_lnx_{self._testMethodName}.json")
        self.config_file = os.path.join(manifest.config_folder, f"generic_config_lnx_{self._testMethodName}.json")
        self.default_config_file = "default_config.json"
        self.comps_platform = 'SLURM'

    def generate_schema(self):
        print('Using schema.json downloaded from test_download_from_bamboo.py for test')
        self.schema_path = manifest.schema_path_linux
        if not os.path.isfile(self.schema_path):
            download_latest_schema(plan=self.plan, scheduled_builds_only=False, out_path=self.schema_path)

    def test_1_config_from_builder_linux(self):
        self.is_singularity = True
        super().config_from_builder_test()

    def test_2_config_from_default_and_set_fn_linux(self):
        self.is_singularity = True
        super().config_from_default_and_set_fn_test()

    def test_3_config_from_po_linux(self):
        self.is_singularity = True
        super().config_from_po_test(config_filename="config_from_po_l.json")

    def test_4_config_from_task_update_linux(self):
        self.is_singularity = True
        super().config_from_task_update_test(config_filename="generic_config_l.json")

    def test_5_config_from_task_default_linux(self):
        self.is_singularity = True
        super().config_from_defaults()


@pytest.mark.emod
@pytest.mark.skip('Skip Window all tests for now.')
class TestWorkflowConfigWinALL(TestWorkflowConfig):
    """
        Tested with Windows version of monolithic Eradication
    """
    def define_test_environment(self):
        self.plan = EradicationBambooBuilds.GENERIC_WIN_ALL
        self.eradication_path = manifest.eradication_path_win_all
        self.schema_path = os.path.join(manifest.config_folder, f"generic_schema_win_all_{self._testMethodName}.json")
        self.config_file = os.path.join(manifest.config_folder, f"generic_config_win_all_{self._testMethodName}.json")
        self.default_config_file = "default_config.json"
        self.comps_platform = 'COMPS2'

    def generate_schema(self):
        print('Using schema.json downloaded from test_download_from_bamboo.py for test')
        self.schema_path = manifest.schema_path_win_all
        if not os.path.isfile(self.schema_path):
            download_latest_schema(plan=self.plan, scheduled_builds_only=False, out_path=self.schema_path)

    def test_1_config_from_builder_win_all(self):
        super().config_from_builder_test()

    def test_2_config_from_default_and_set_fn_win_all(self):
        super().config_from_default_and_set_fn_test()

    def test_3_config_from_po_win_all(self):
        super().config_from_po_test(config_filename="config_from_po_all.json")

    def test_4_config_from_task_update_win_all(self):
        super().config_from_task_update_test(config_filename="config_all.json")

    def test_5_config_from_task_default_win_all(self):
        # if platform == "linux" or platform == "linux2":
        #     print('OS is Linux, skip test.')
        #     pass
        # else:
        #     super().config_from_defaults()
        super().config_from_defaults()
