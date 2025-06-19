import os
from functools import partial
import unittest
import pytest
import time
from emod_api.config import default_from_schema_no_validation as dfs
from emodpy.demographics.demographics import Demographics
import emod_api.demographics.Demographics as Demographics_api
import emod_api.demographics.Node as Node
from emod_api.demographics.PropertiesAndAttributes import IndividualAttributes, IndividualProperty, \
    IndividualProperties, NodeAttributes

from idmtools.entities.experiment import Experiment
from idmtools.core.platform_factory import Platform
from idmtools.builders import SimulationBuilder

from emodpy.emod_task import EMODTask, logger

import json

from pathlib import Path
import sys

parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers


def set_param_fn(config, implicit_config_set_fns=None):
    if implicit_config_set_fns:
        for fn in implicit_config_set_fns:
            config = fn(config)
    return config


@pytest.mark.container
class TestWorkflowDemographics(unittest.TestCase):
    """
        Tests for EMODTask
    """

    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.original_working_dir = os.getcwd()
        self.platform = Platform(manifest.container_platform_name)
        self.builders = helpers.BuildersCommon
        self.test_folder = helpers.make_test_directory(self.case_name)

    def tearDown(self) -> None:
        # Check if the test failed and leave the data in the folder if it did
        test_result = self.defaultTestResult()
        if test_result.errors:
            with open("experiment_location.txt", "w") as f:
                if hasattr(self, "experiment"):
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

    def run_exp(self, task):
        experiment = Experiment.from_task(task, name=self._testMethodName)
        with self.platform as plat:
            # The last step is to call run() on the ExperimentManager to run the simulations.
            experiment.run(platform=plat)
            plat.wait_till_done(experiment, refresh_interval=1)

        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        return experiment

    def set_param_fn(self, config, implicit_config_set_fns=None):
        config = self.builders.config_builder(config)
        if implicit_config_set_fns:
            for fn in implicit_config_set_fns:
                config = fn(config)
        return config

    def basic_demographics_test(self):
        """
            Testing the Demographics.from_template_node() with everything from default and make sure it can be consumed by
            the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = ["demographics.json"]
                Enable_Demographics_Builtin = 0
            (Test to make sure the default values are honored in demographics file is in emod_api tests folder)
        """

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=self.builders.demographics_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)

        self.assertEqual(['demographics.json'], task.config['parameters'][
            'Demographics_Filenames'])  # checking that it's using demog file from "from_defaults"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.run_exp(task)

    def demographic_sweep_test(self):
        def build_demog(age):
            from emodpy.utils.distributions import ConstantDistribution
            demographics = self.builders.demographics_builder()
            demographics.set_age_distribution(distribution=ConstantDistribution(age))
            return demographics

        def update_demog_initial_prevalence(simulation, _age):
            build_demog_prevalence = partial(build_demog, age=_age)
            simulation.task.create_demographics_from_callback(build_demog_prevalence, from_sweep=True)
            return {"Age": _age}

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=None)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        builder = SimulationBuilder()
        ages = [10, 12, 15, 17, 21]
        builder.add_sweep_definition(update_demog_initial_prevalence, ages)

        experiment = Experiment.from_builder(builder, task, name=self.case_name)
        experiment.run(platform=self.platform, wait_until_done=True)
        self.assertTrue(experiment.succeeded, msg=f"Experiment {experiment.uid} failed.\n")
        self.assertEqual(len(experiment.simulations), len(ages))

        for sim, prevalence in zip(experiment.simulations, ages):
            config = self.platform.get_files(sim, ["config.json"])
            config_dict = json.loads(config["config.json"])
            self.assertEqual(len(config_dict["parameters"]["Demographics_Filenames"]), 1)
            demog_filename = config_dict["parameters"]["Demographics_Filenames"][0]
            demog_file = self.platform.get_files(sim, [demog_filename])
            demographics_dict = json.loads(demog_file[demog_filename])
            self.assertEqual(demographics_dict['Defaults']['IndividualAttributes']['AgeDistribution1'],
                             prevalence)
            self.assertEqual(demographics_dict['Defaults']['IndividualAttributes']['AgeDistribution2'],
                             0)
            self.assertEqual(demographics_dict['Defaults']['IndividualAttributes']['AgeDistributionFlag'],
                             0)

    def complex_susceptibility_demographics_test(self):
        """
            Testing that setting SusceptibilityDistribution in demographics can be consumed by EMOD.
            Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = ["demographics.json"]
                Enable_Demographics_Builtin = 0
                Susceptibility_Initialization_Distribution_Type = DISTRIBUTION_COMPLEX

        """

        def build_demographics():
            from emodpy.demographics.demographics import Demographics
            from emod_api.demographics.Node import Node
            from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution

            default_node = Node(lat=0, lon=0, pop=10000, forced_id=0)
            nodes = [Node(lat=0, lon=0, pop=10000, forced_id=1, name='here')]
            demographics = Demographics(nodes=nodes, default_node=default_node)
            distribution = SusceptibilityDistribution(ages_years=[0, 5, 10],
                                                      susceptible_fraction=[0.9, 0.8, 0.7])
            demographics.set_susceptibility_distribution(distribution=distribution)
            return demographics

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      demographics_builder=build_demographics,
                                      config_builder=self.builders.config_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)

        self.assertEqual(['demographics.json'], task.config['parameters'][
            'Demographics_Filenames'])  # checking that it's using demog file from "from_default"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.assertEqual('DISTRIBUTION_COMPLEX',
                         task.config['parameters']['Susceptibility_Initialization_Distribution_Type'])
        self.run_exp(task)

    def add_individual_property_demographics_test(self):
        """
            Testing the Demographics builder with add_individual_property and make sure it can be
            consumed by the Eradication. Make sure following config parameters are set implicitly with
            implicit_config_fns:
                Demographics_Filenames = ["demographics.json"]
                Enable_Demographics_Builtin = 0
            (Test to make sure the Individual Property and HINT values are honored in demographics file is in
            emod_api tests folder)
        """

        def demog_builder():
            demog = self.builders.demographics_builder()
            property = 'QualityOfCare'
            values = ['High', 'Low']
            initial_distribution = [0.3, 0.7]
            demog.add_individual_property(property=property,
                                          values=values,
                                          initial_distribution=initial_distribution)

            return demog

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      demographics_builder=demog_builder,
                                      config_builder=self.builders.config_builder)

        task.set_sif(self.builders.sif_path, platform=self.platform)
        self.assertEqual([os.path.basename("demographics.json")], task.config.parameters['Demographics_Filenames'])
        self.assertEqual(0, task.config.parameters['Enable_Demographics_Builtin'])
        self.run_exp(task)

    def from_csv_demographics_test(self):
        """
            Testing the demographic generated by Demographics.from_csv() with a csv file can be consumed by the
            Eradication. Make sure following config parameters are set implicitly with implicit_config_fns:
                Demographics_Filenames = ["demographics.json"]
                Enable_Demographics_Builtin = 0
            (Test to make sure the demographics file matches the csv file is in emod-api tests folder.)
        """

        def demog_builder():
            input_file = os.path.join(manifest.demographics_folder, 'demog_in.csv')
            demog = Demographics_api.from_csv(input_file, res=1 / 3600)
            demog.SetDefaultProperties()
            return demog

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      demographics_builder=demog_builder,
                                      config_builder=self.builders.config_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        self.assertEqual(['demographics.json'], task.config['parameters'][
            'Demographics_Filenames'])  # checking that it's using demog file from "from_default"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        task.set_parameter('x_Base_Population', 0.00001)
        self.run_exp(task)

    def from_params_demographics_test(self):
        """
            Testing the demographic generated by Demographics.from_params() can be consumed by the
            Eradication. Make sure following config parameters are set implicitly with implicit_config_fns:
                Demographics_Filenames = ["demographics.json"]
                Enable_Demographics_Builtin = 0
            (Test to make sure the synth pop values are honored in demographics file is in emod_api tests folder)
        """

        def demog_builder():
            totpop = 1e4
            num_nodes = 250
            frac_rural = 0.1
            demog = Demographics_api.from_params(tot_pop=totpop, num_nodes=num_nodes, frac_rural=frac_rural)
            demog.SetDefaultProperties()
            return demog

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      demographics_builder=demog_builder,
                                      config_builder=self.builders.config_builder)
        task.set_sif(self.builders.sif_path, platform=self.platform)

        self.assertEqual(['demographics.json'], task.config['parameters'][
            'Demographics_Filenames'])  # checking that it's using demog file from "from_default"
        self.assertEqual(0, task.config['parameters']['Enable_Demographics_Builtin'])
        self.run_exp(task)

    def demographics_overlay_node_attributes_test(self):
        """
            Testing the Demographics.apply_overlay() and Node.OverlayNode from Emodapi and make sure it can be
            consumed by the Eradication.
        """

        def build_demog():
            node_attributes_1 = NodeAttributes(latitude=1, longitude=0, initial_population=1001,
                                               name="test_demo1")
            node_attributes_2 = NodeAttributes(latitude=0, longitude=1, initial_population=1002,
                                               name="test_demo2")
            default_node = Node.Node(lat=0, lon=0, pop=1000, forced_id=0)
            nodes = [Node.Node(lat=1, lon=0, pop=1001, node_attributes=node_attributes_1, forced_id=1),
                     Node.Node(lat=0, lon=1, pop=1002, node_attributes=node_attributes_2, forced_id=2)]
            demog = Demographics(nodes=nodes, default_node=default_node)
            overlay_nodes = []
            new_population = 100
            new_name = "Test NodeAttributes"
            new_node_attributes1 = NodeAttributes(name=new_name + "1", initial_population=new_population)
            new_node_attributes2 = NodeAttributes(name=new_name + "2", initial_population=new_population)

            overlay_nodes.append(Node.OverlayNode(node_id=1, node_attributes=new_node_attributes1))
            overlay_nodes.append(Node.OverlayNode(node_id=2, node_attributes=new_node_attributes2))
            demog.apply_overlay(overlay_nodes)

            return demog

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=build_demog)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        experiment = self.run_exp(task)

        inset_chart_filename = "output/InsetChart.json"
        demog_filename = "Assets/demographics.json"

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [inset_chart_filename, demog_filename])
            inset_chart = json.loads(files[inset_chart_filename])
            self.assertEqual(inset_chart['Channels']['Statistical Population']['Data'][0], 100 * 2)

            demographics = json.loads(files[demog_filename])
            self.assertEqual(demographics['Nodes'][0]["NodeAttributes"]['Latitude'], 1)
            self.assertEqual(demographics['Nodes'][1]["NodeAttributes"]['Latitude'], 0)

            self.assertEqual(demographics['Nodes'][0]["NodeAttributes"]['Longitude'], 0)
            self.assertEqual(demographics['Nodes'][1]["NodeAttributes"]['Longitude'], 1)

            self.assertEqual(demographics['Nodes'][0]["NodeAttributes"]['FacilityName'], "Test NodeAttributes1")
            self.assertEqual(demographics['Nodes'][1]["NodeAttributes"]['FacilityName'], "Test NodeAttributes2")

    def demographics_overlay_individual_attributes_test(self):
        """
            Testing the Demographics.apply_overlay() and Node.OverlayNode from Emodapi and make sure it can be
            consumed by the Eradication.
        """

        def build_demog():
            individual_attributes_1 = IndividualAttributes(age_distribution_flag=1,
                                                           age_distribution1=730,
                                                           age_distribution2=7300)
            individual_attributes_2 = IndividualAttributes(age_distribution_flag=1,
                                                           age_distribution1=365,
                                                           age_distribution2=3650)
            node_attributes = NodeAttributes(initial_population=100, latitude=0, longitude=1)
            default_node = Node.Node(lat=0, lon=0, pop=1000, forced_id=0)
            nodes = [Node.Node(lat=0, lon=1, pop=100, individual_attributes=individual_attributes_1, forced_id=1,
                               node_attributes=node_attributes),
                     Node.Node(lat=0, lon=1, pop=100, individual_attributes=individual_attributes_2, forced_id=2,
                               node_attributes=node_attributes)]
            demog = Demographics(nodes=nodes, default_node=default_node)
            overlay_nodes = []
            new_individual_attributes = IndividualAttributes(age_distribution_flag=0,
                                                             age_distribution1=300,
                                                             age_distribution2=600)

            overlay_nodes.append(Node.OverlayNode(node_id=1, individual_attributes=new_individual_attributes))
            overlay_nodes.append(Node.OverlayNode(node_id=2, individual_attributes=new_individual_attributes))
            demog.apply_overlay(overlay_nodes)

            return demog

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=self.builders.config_builder,
                                      demographics_builder=build_demog)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        experiment = self.run_exp(task)

        demog_filename = "Assets/demographics.json"

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [demog_filename])
            demographics = json.loads(files[demog_filename])
            self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistributionFlag'], 0)
            self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistributionFlag'], 0)

            self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution1'], 300)
            self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution1'], 300)

            self.assertEqual(demographics['Nodes'][0]["IndividualAttributes"]['AgeDistribution2'], 600)
            self.assertEqual(demographics['Nodes'][1]["IndividualAttributes"]['AgeDistribution2'], 600)

    def demographics_overlay_individual_properties_test(self):
        """
            Testing the Demographics.apply_overlay() and Node.OverlayNode from Emodapi and make sure it can be
            consumed by the Eradication.
        """

        def build_demog():
            node_attributes_1 = NodeAttributes(latitude=1, longitude=0, initial_population=1001,
                                               name="test_demo1")
            node_attributes_2 = NodeAttributes(latitude=0, longitude=1, initial_population=1002,
                                               name="test_demo2")
            default_node = Node.Node(lat=0, lon=0, pop=1000, forced_id=0)
            nodes = [Node.Node(lat=1, lon=0, pop=1001, node_attributes=node_attributes_1, forced_id=1),
                     Node.Node(lat=0, lon=1, pop=1002, node_attributes=node_attributes_2, forced_id=2)]
            demog = Demographics(nodes=nodes, default_node=default_node)
            overlay_nodes = []

            initial_distribution = [0.1, 0.9]
            property = "QualityOfCare"
            values = ["High", "Low"]
            new_individual_properties = IndividualProperties()
            new_individual_properties.add(IndividualProperty(initial_distribution=initial_distribution,
                                                             property=property,
                                                             values=values))

            overlay_nodes.append(Node.OverlayNode(node_id=1, individual_properties=new_individual_properties))
            overlay_nodes.append(Node.OverlayNode(node_id=2, individual_properties=new_individual_properties))
            demog.apply_overlay(overlay_nodes)

            return demog

        def set_param_fn(config):
            config = self.builders.config_builder(config)
            config.parameters.Enable_Property_Output = 1
            return config

        task = EMODTask.from_defaults(eradication_path=self.builders.eradication_path,
                                      schema_path=self.builders.schema_path,
                                      config_builder=set_param_fn,
                                      demographics_builder=build_demog)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        experiment = self.run_exp(task)

        property_filename = "output/PropertyReport.json"

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [property_filename])
            property_report = json.loads(files[property_filename])
            pop_high = property_report['Channels']['Statistical Population:QualityOfCare:High']['Data'][0]
            pop_low = property_report['Channels']['Statistical Population:QualityOfCare:Low']['Data'][0]
            self.assertAlmostEqual(pop_high / pop_low, 0.1 / 0.9, delta=0.01)

    def demographics_overlay_susceptibility_distribution_from_files_test(self):
        """
            Testing the Demographics and DemographicsOverlay from Emodapi and make sure it can be
            consumed by the Eradication.
        """
        from emod_api.demographics.demographics_overlay import DemographicsOverlay
        from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution

        default_node = Node.Node(lat=0, lon=0, pop=1000, forced_id=0)
        nodes = [Node.Node(lat=1, lon=0, pop=1001, forced_id=1)]
        demog = Demographics(nodes=nodes, default_node=default_node)
        demog.generate_file("demographics.json")

        # generate overlay files
        individual_attributes = IndividualAttributes()
        individual_attributes.susceptibility_distribution = SusceptibilityDistribution(
            ages_years=[12, 20],
            susceptible_fraction=[0.2, 0.3]
        )

        overlay = DemographicsOverlay(nodes=[Node.OverlayNode(1)],
                                      individual_attributes=individual_attributes,
                                      node_attributes=None,
                                      idref="Gridded world grump2.5arcmin")
        overlay_filename = os.path.join(self.test_folder, "demographics_susceptibility_overlay.json")
        overlay.to_file(overlay_filename)

        dfs.get_default_config_from_schema(path_to_schema=self.builders.schema_path, as_rod=True,
                                           output_filename="config.json")
        if self.__class__.__name__ == "TestWorkflowDemographicsGeneric":
            # For Generic-Ongoing, we need to set more implicits
            def _for_generic_ongoing(config):
                config.parameters.Enable_Acquisition_Heterogeneity = 0
                config.parameters.Enable_Heterogeneous_Intranode_Transmission = 0
                config.parameters.Enable_Initial_Prevalence = 0
                config.parameters.Enable_Natural_Mortality = 0
                return config

            demog.implicits.append(_for_generic_ongoing)
        dfs.write_config_from_default_and_params(config_path="config.json",
                                                 set_fn=partial(self.set_param_fn,
                                                                implicit_config_set_fns=demog.implicits),
                                                 config_out_path="config.json")
        task = EMODTask.from_files(config_path="config.json",
                                   eradication_path=self.builders.eradication_path,
                                   demographics_paths=["demographics.json", overlay_filename],
                                   embedded_python_scripts_path=None)
        task.set_sif(self.builders.sif_path, platform=self.platform)
        experiment = self.run_exp(task)

        demog_filename = os.path.join("Assets", os.path.basename("demographics.json"))
        demog_overlay_filename = "Assets/demographics_susceptibility_overlay.json"

        for sim in experiment.simulations:
            files = self.platform.get_files(sim, [demog_filename, demog_overlay_filename])
            demographics = json.loads(files[demog_filename])
            self.assertEqual(demographics['Defaults']['IndividualAttributes'], {})
            demographics_overlay = json.loads(files[demog_overlay_filename])
            self.assertListEqual(demographics_overlay['Defaults']['IndividualAttributes']
                                 ["SusceptibilityDistribution"]["DistributionValues"], [4380, 7300])
            self.assertListEqual(demographics_overlay['Defaults']['IndividualAttributes']
                                 ["SusceptibilityDistribution"]["ResultValues"], [0.2, 0.3])
            self.assertEqual(demographics_overlay['Defaults']['IndividualAttributes']
                             ["SusceptibilityDistribution"]["ResultScaleFactor"], 1)


@pytest.mark.container
class TestWorkflowDemographicsGeneric(TestWorkflowDemographics):
    """
        Testing with Generic-Ongoing
    """

    def setUp(self) -> None:
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + self._testMethodName
        print(f"\n{self.case_name}")
        self.original_working_dir = os.getcwd()
        self.platform = Platform(manifest.container_platform_name)
        self.builders = helpers.BuildersGeneric
        self.test_folder = helpers.make_test_directory(self.case_name)

    def test_a_basic_demographics_generic(self):
        super().basic_demographics_test()

    def test_b_complex_susceptibility_demographics_generic(self):
        super().complex_susceptibility_demographics_test()

    def test_d_add_individual_property_demographics_generic(self):
        super().add_individual_property_demographics_test()

    def test_f_from_csv_demographics_generic(self):
        super().from_csv_demographics_test()

    def test_g_from_params_demographics_generic(self):
        super().from_params_demographics_test()

    def test_h_demographics_sweep_generic(self):
        super().demographic_sweep_test()

    def test_i_demographics_overlay_node_attributes_generic(self):
        super().demographics_overlay_node_attributes_test()

    def test_j_demographics_overlay_individual_attributes_generic(self):
        super().demographics_overlay_individual_attributes_test()

    def test_k_demographics_overlay_individual_properties_generic(self):
        super().demographics_overlay_individual_properties_test()

    def test_l_demographics_overlay_susceptibility_distribution_from_files_generic(self):
        super().demographics_overlay_susceptibility_distribution_from_files_test()
