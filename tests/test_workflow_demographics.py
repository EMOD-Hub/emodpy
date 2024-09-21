import os
import pytest
import shutil
from functools import partial
from abc import ABC, abstractmethod

from emod_api.config import default_from_schema_no_validation as dfs
import emod_api.demographics.Demographics as Demographics
import emod_api.demographics.DemographicsTemplates as DT

from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools_test.utils.itest_with_persistence import ITestWithPersistence
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask
from emodpy.utils import download_latest_bamboo, download_latest_schema, EradicationBambooBuilds, bamboo_api_login

from io import StringIO
from contextlib import redirect_stdout
import json

# import sys
# file_dir = os.path.dirname(__file__)
# sys.path.append(file_dir)
from . import manifest

default_config_file = "default_config.json"  # this is a hard-coded value


def set_param_fn(config, implicit_config_set_fns=None):
    if implicit_config_set_fns:
        for fn in implicit_config_set_fns:
            config = fn(config)
    return config


# bamboo_api_login() only work in console
# Please run this test from console for the first time or run 'test_download_from_bamboo.py' from console before
# running this test
class TestWorkflowDemographics(ITestWithPersistence, ABC):
    """
        Base test class to test emod_api.demographics in a workflow
    """
    @classmethod
    @abstractmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.CI_GENERIC
        cls.eradication_path = manifest.eradication_path_win
        cls.schema_path = manifest.schema_path_win
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_demographics_workflow.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.demographics_file = os.path.join(manifest.demographics_folder, "generic_demographics.json")
        cls.comps_platform = 'COMPS2'

    @classmethod
    def setUpClass(cls) -> None:
        cls.define_test_environment()
        manifest.delete_existing_file(cls.config_file)
        manifest.delete_existing_file(default_config_file)
        print("write_default_from_schema")
        dfs.write_default_from_schema(cls.schema_path)
        print("move default_config.json")
        shutil.move(default_config_file, cls.default_config_file)

    def setUp(self) -> None:
        self.case_name = os.path.basename(__file__) + "--" + self._testMethodName
        print(self.case_name)
        self.get_exe_from_bamboo()
        self.get_schema_from_bamboo()
        self.platform = Platform(self.comps_platform)
        manifest.delete_existing_file(self.demographics_file)

    def get_exe_from_bamboo(self):
        if not os.path.isfile(self.eradication_path):
            bamboo_api_login()
            print(
                f"Getting Eradication from bamboo for plan {self.plan}. Please run this script in console if this "
                "is the first time you use bamboo_api_login()."
            )
            eradication_path_bamboo = download_latest_bamboo(
                plan=self.plan,
                scheduled_builds_only=False
            )
            shutil.move(eradication_path_bamboo, self.eradication_path)
        else:
            print(f"{self.eradication_path} already exists, no need to get it from bamboo.")

    def get_schema_from_bamboo(self):
        if not os.path.isfile(self.schema_path):
            bamboo_api_login()
            print(
                f"Getting Schema.json from bamboo for plan {self.plan}. Please run this script in console if this "
                "is the first time you use bamboo_api_login()."
            )
            download_latest_schema(
                plan=self.plan,
                scheduled_builds_only=False,
                out_path=self.schema_path
            )
        else:
            print(f"{self.schema_path} already exists, no need to get it from bamboo.")

    def run_exp(self, task):
        experiment = Experiment.from_task(task, name=self._testMethodName)

        print("Run experiment...")
        with self.platform as plat:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            experiment.run(platform=plat)
            plat.wait_till_done(experiment, refresh_interval=1)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")

        print(f"Experiment {experiment.uid} succeeded.")

    @staticmethod
    def set_demog_file(config, demographics_file):
        """
        This is a supplement to the main parameter setting function with params that need to be set as a result
        of our demographics specifics. Ideally this will go away because those will be set implicitly either in
        emod-api itself (via a callback) or emodpy base functionality.
        See ticket https://github.com/InstituteforDiseaseModeling/emodpy/issues/225
        """
        demog_files = [os.path.basename(demographics_file)]
        config.parameters.Demographics_Filenames = demog_files
        config.parameters.Enable_Demographics_Builtin = 0  # should be implicit
        # config.parameters.Enable_Heterogeneous_Intranode_Transmission = 1 # implicit
        return config

    def basic_demographics_test(self):
        """
            Testing the Demographics.from_template_node() with everything from default and make sure it can be consumed by
            the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
            (Test to make sure the default values are honored in demographics file is in emod_api tests folder)
        """
        def build_demo():
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            return demog

        task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                      schema_path=manifest.schema_path_linux,
                                      config_path=self.default_config_file,
                                      param_custom_cb=None,
                                      ep4_custom_cb=None, demog_builder=build_demo)

        self.assertEqual(['demographics.json'], task.config['parameters']['Demographics_Filenames'])  # checking that it's using demog file from "from_default2"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.run_exp(task)

    def demographic_sweep_test(self):
        def build_demog(initial_prevalence):
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            demog.raw['Defaults']['IndividualAttributes']['InitialPrevalence'] = initial_prevalence
            return demog

        def update_demog_initial_prevalence(simulation, prevalence):
            build_demog_prevalence = partial(build_demog, initial_prevalence=prevalence)
            simulation.task.create_demog_from_callback(build_demog_prevalence, from_sweep=True)
            return {"InitialPrevalence": prevalence}

        def get_file_names(debug):
            result = []
            filenames = debug.split(".json")
            filenames = [name.split("tmp") for name in filenames]
            filenames = [item for sublist in filenames for item in sublist]
            for item in filenames:
                if len(item) == 8 and " " not in item and "." not in item:
                    result.append("tmp" + item + ".json")
            return result

        printed_output = StringIO()

        with redirect_stdout(printed_output):
            task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                          schema_path=manifest.schema_path_linux,
                                          config_path=self.default_config_file,
                                          param_custom_cb=None, demog_builder=None, ep4_custom_cb=None)
            builder = SimulationBuilder()
            prevalences = [0.1, 0.3, 0.5, 0.7, 1]
            builder.add_sweep_definition(update_demog_initial_prevalence, prevalences)

            experiment = Experiment.from_builder(builder, task, name=self._testMethodName)
            print("Running demographics sweep...")
            # This can be optimized for refresh rate
            experiment.run(platform=self.platform, wait_until_done=True)

        filenames = get_file_names(printed_output.getvalue())
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        print(f"Experiment {experiment.uid} succeeded.")
        self.assertEqual(len(experiment.simulations), len(prevalences))
        self.assertEqual(len(experiment.simulations), len(filenames))

        for sim, filename, prevalence in zip(experiment.simulations, filenames, prevalences):
            files = self.platform.get_files(sim, [filename])
            demographics_dict = json.loads(files[filename])
            self.assertEqual(demographics_dict['Defaults']['IndividualAttributes']['InitialPrevalence'], prevalence)

    def simple_susceptibility_demographics_test(self):
        """
            Testing the Demographics.from_template_node() with DT.SimpleSusceptibilityDistribution() and make sure it can be
            consumed by the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
                Susceptibility_Initialization_Distribution_Type = DISTRIBUTION_COMPLEX
            (Test to make sure the meanAgeAtInfection values are honored in demographics file is in emod_api tests folder)
        """
        def build_demo():
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            DT.SimpleSusceptibilityDistribution(demog, meanAgeAtInfection=10)
            return demog

        task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                      schema_path=manifest.schema_path_linux,
                                      config_path=self.default_config_file,
                                      param_custom_cb=None, demog_builder=build_demo, ep4_custom_cb=None)  # remove schema path later

        self.assertEqual(['demographics.json'], task.config['parameters']['Demographics_Filenames'])  # checking that it's using demog file from "from_default2"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.assertEqual('DISTRIBUTION_COMPLEX', task.config['parameters']['Susceptibility_Initialization_Distribution_Type'])
        self.run_exp(task)

    def age_dependent_transmission_demographics_test(self):
        """
            Testing the Demographics.from_template_node() with AddAgeDependentTransmission() and make sure it can be
            consumed by the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
                Enable_Heterogeneous_Intranode_Transmission = 1
            (Test to make sure the age dependent transmission values are honored in demographics file is in
            emod_api tests folder)
        """
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        demog.AddAgeDependentTransmission(Age_Bin_Edges_In_Years=[0, 10, 20, -1],
                                          TransmissionMatrix=[[0.2, 0.8, 1.0], [0, 0.4, 1.0], [0.2, 0.4, 1.0]])
        demog.generate_file(self.demographics_file)

        dfs.write_config_from_default_and_params(config_path=self.default_config_file,
                                                 set_fn=partial(set_param_fn, implicit_config_set_fns=demog.implicits),
                                                 config_out_path=self.config_file)
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   demographics_paths=self.demographics_file, ep4_path=None)
        self.assertEqual([os.path.basename(self.demographics_file)], task.config['Demographics_Filenames'])
        self.assertEqual(0, task.config['Enable_Demographics_Builtin'])
        self.assertEqual(1, task.config['Enable_Heterogeneous_Intranode_Transmission'])
        self.run_exp(task)

    def add_individual_property_and_HINT_demographics_test(self):
        """
            Testing the Demographics.from_template_nodeNode() with AddIndividualPropertyAndHINT() and make sure it can be
            consumed by the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
                Enable_Heterogeneous_Intranode_Transmission = 1
            (Test to make sure the Individual Property and HINT values are honored in demographics file is in
            emod_api tests folder)
        """
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        property = 'QualityOfCare'
        values = ['High', 'Low']
        initial_distribution = [0.3, 0.7]
        transmission_matrix = [[1, 0], [0, 1]]
        demog.AddIndividualPropertyAndHINT(Property=property, Values=values, InitialDistribution=initial_distribution,
                                           TransmissionMatrix=transmission_matrix)
        demog.generate_file(self.demographics_file)

        dfs.write_config_from_default_and_params(config_path=self.default_config_file,
                                                 set_fn=partial(set_param_fn, implicit_config_set_fns=demog.implicits),
                                                 config_out_path=self.config_file)
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   demographics_paths=self.demographics_file, ep4_path=None)
        self.assertEqual([os.path.basename(self.demographics_file)], task.config['Demographics_Filenames'])
        self.assertEqual(0, task.config['Enable_Demographics_Builtin'])
        self.assertEqual(1, task.config['Enable_Heterogeneous_Intranode_Transmission'])
        self.run_exp(task)

    def add_individual_property_and_HINT_disable_whitelist_demographics_test(self):
        """
            Testing the Demographics.from_template_node() with AddIndividualPropertyAndHINT()(with a IP that is not in Emod
            IP white list) and make sure it can be consumed by the Eradication. Make sure following config parameters
            are set implicitly with implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
                Enable_Heterogeneous_Intranode_Transmission = 1
                Disable_IP_Whitelist = 1
            (Test to make sure the Individual Property and HINT values are honored in demographics file is in
            emod_api tests folder)
        """
        demog = Demographics.from_template_node()
        demog.SetDefaultProperties()
        property = 'my_propertry'
        values = ['1', '2']
        initial_distribution = [0.2, 0.8]
        demog.AddIndividualPropertyAndHINT(Property=property, Values=values, InitialDistribution=initial_distribution)
        demog.generate_file(self.demographics_file)

        dfs.write_config_from_default_and_params(config_path=self.default_config_file,
                                                 set_fn=partial(set_param_fn, implicit_config_set_fns=demog.implicits),
                                                 config_out_path=self.config_file)
        task = EMODTask.from_files(config_path=self.config_file, eradication_path=self.eradication_path,
                                   demographics_paths=self.demographics_file, ep4_path=None)
        self.assertEqual([os.path.basename(self.demographics_file)], task.config['Demographics_Filenames'])
        self.assertEqual(0, task.config['Enable_Demographics_Builtin'])
        self.assertEqual(1, task.config['Enable_Heterogeneous_Intranode_Transmission'])
        self.assertEqual(1, task.config['Disable_IP_Whitelist'])
        self.run_exp(task)

    def from_csv_demographics_test(self):
        """
            Testing the demographic generated by Demographics.from_csv() with a csv file can be consumed by the
            Eradication. Make sure following config parameters are set implicitly with implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
            (Test to make sure the demographics file matches the csv file is in emod-api tests folder.)
        """
        def demog_builder():
            input_file = os.path.join(manifest.current_directory, 'inputs', 'demographics', 'demog_in.csv')
            demog = Demographics.from_csv(input_file, res=25 / 3600)
            demog.SetDefaultProperties()
            return demog

        task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                      schema_path=manifest.schema_path_linux,
                                      config_path=self.default_config_file, demog_builder=demog_builder,
                                      ep4_custom_cb=None, param_custom_cb=None)
        self.assertEqual(['demographics.json'], task.config['parameters']['Demographics_Filenames'])  # checking that it's using demog file from "from_default2"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        task.set_parameter('x_Base_Population', 0.00001)
        self.run_exp(task)

    def from_params_demographics_test(self):
        """
            Testing the demographic generated by Demographics.from_params() can be consumed by the
            Eradication. Make sure following config parameters are set implicitly with implicit_config_fns:
                Demographics_Filenames = [{self.demographics_file}]
                Enable_Demographics_Builtin = 0
            (Test to make sure the synth pop values are honored in demographics file is in emod_api tests folder)
        """
        def demog_builder():
            totpop = 1e4
            num_nodes = 250
            frac_rural = 0.1
            demog = Demographics.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural)
            demog.SetDefaultProperties()
            return demog

        task = EMODTask.from_default2(eradication_path=self.eradication_path,
                                      schema_path=manifest.schema_path_linux,
                                      config_path=self.default_config_file, demog_builder=demog_builder,
                                      param_custom_cb=None, ep4_custom_cb=None)

        self.assertEqual(['demographics.json'], task.config['parameters']['Demographics_Filenames'])  # checking that it's using demog file from "from_default2"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.run_exp(task)


# @pytest.mark.skip('skip tests for Windows Eradication for now')
@pytest.mark.emod
class TestWorkflowDemographicsWin(TestWorkflowDemographics):
    """
        Tested with Windows version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_WIN
        cls.eradication_path = manifest.eradication_path_win
        cls.schema_path = manifest.schema_path_win
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_demographics_workflow.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.demographics_file = os.path.join(manifest.demographics_folder, "generic_demographics.json")
        cls.comps_platform = 'COMPS2'

    def test_1_basic_demographics_win(self):
        super().basic_demographics_test()

    def test_2_simple_susceptibility_demographics_win(self):
        super().simple_susceptibility_demographics_test()

    def test_3_age_dependent_transmission_demographics_win(self):
        super().age_dependent_transmission_demographics_test()

    def test_4_add_individual_property_and_HINT_demographics_win(self):
        super().add_individual_property_and_HINT_demographics_test()

    def skip_test_5_add_individual_property_and_HINT_disable_whitelist_demographics_win(self):
        super().add_individual_property_and_HINT_disable_whitelist_demographics_test()

    def test_6_from_csv_demographics_win(self):
        super().from_csv_demographics_test()

    def test_7_from_params_demographics_win(self):
        super().from_params_demographics_test()

    def test_8_demographics_sweep_win(self):
        super().demographic_sweep_test()


# @pytest.mark.skip('skip tests for Linux Eradication for now')
@pytest.mark.emod
class TestWorkflowDemographicsLinux(TestWorkflowDemographics):
    """
        Tested with Linux version of Generic Eradication
    """
    @classmethod
    def define_test_environment(cls):
        cls.plan = EradicationBambooBuilds.GENERIC_LINUX
        cls.eradication_path = manifest.eradication_path_linux
        cls.schema_path = manifest.schema_path_linux
        cls.config_file = os.path.join(manifest.config_folder, "generic_config_for_demographics_workflow_l.json")
        cls.default_config_file = os.path.join(manifest.config_folder, default_config_file)
        cls.demographics_file = os.path.join(manifest.demographics_folder, "generic_demographics_l.json")
        cls.comps_platform = 'SLURM'

    def test_1_basic_demographics_linux(self):
        super().basic_demographics_test()

    def test_2_simple_susceptibility_demographics_linux(self):
        super().simple_susceptibility_demographics_test()

    def test_3_age_dependent_transmission_demographics_linux(self):
        super().age_dependent_transmission_demographics_test()

    def test_4_add_individual_property_and_HINT_demographics_linux(self):
        super().add_individual_property_and_HINT_demographics_test()

    def skip_test_5_add_individual_property_and_HINT_disable_whitelist_demographics_linux(self):
        super().add_individual_property_and_HINT_disable_whitelist_demographics_test()

    def test_6_from_csv_demographics_linux(self):
        super().from_csv_demographics_test()

    def test_7_from_params_demographics_linux(self):
        super().from_params_demographics_test()

    def test_8_demographics_sweep_linux(self):
        super().demographic_sweep_test()
