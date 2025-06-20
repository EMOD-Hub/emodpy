import unittest
import pytest
from typing import List, Callable

from emod_api.demographics.Node import Node
from emod_api.demographics.Updateable import Updateable
from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution

from emodpy.demographics.demographics import Demographics
from emodpy.utils.distributions import *

@pytest.mark.unit
class TestDemographics(unittest.TestCase):
    def setUp(self) -> None:
        self.default_node = Node(lat=0, lon=1, pop=100, name='The default node', forced_id=0)
        self.nodes = []
        self.demographics = Demographics(nodes=self.nodes, default_node=self.default_node)
        self.simple_distribution_dict = {'Distribution': 'UNIFORM_DISTRIBUTION', 'Min': 1, 'Max': 2}
        self.simple_distribution = UniformDistribution(uniform_min=1, uniform_max=2)
        self.complex_age_distribution1 = AgeDistribution(ages_years=[0, 10, 50, 100],
                                                         cumulative_population_fraction=[0, 0.25, 0.5, 1])
        self.complex_age_distribution2 = AgeDistribution(ages_years=[0, 5, 10, 15, 20, 100],
                                                         cumulative_population_fraction=[0, 0.1, 0.2, 0.3, 0.4, 1])
        self.complex_susceptibility_distribution1 = SusceptibilityDistribution(ages_years=[0, 10, 50, 100],
                                                                               susceptible_fraction=[0, 0.25, 0.5, 1])
        self.complex_susceptibility_distribution2 = SusceptibilityDistribution(ages_years=[0, 5, 10, 15, 20, 100],
                                                                               susceptible_fraction=[0, 0.1, 0.2, 0.3, 0.4, 1])
        self.mm1 = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
            [0.92, 0.94, 0.96]
        ]
        self.mm2 = [
            [0.03, 0.06],
            [0.09, 0.12],
            [0.15, 0.18]
        ]
        self.complex_mortality_distribution1 = MortalityDistribution(ages_years=[0, 10, 50, 100],
                                                                     calendar_years=[1950, 1970, 1990],
                                                                     mortality_rate_matrix=self.mm1,
                                                                     )
        self.complex_mortality_distribution2 = MortalityDistribution(ages_years=[0, 20, 40],
                                                                     calendar_years=[1950, 1970],
                                                                     mortality_rate_matrix=self.mm2)

    #
    # a few of reusable, "age", "fertility", "mortality", etc. -agnostic testing functions to be reused below
    #

    def _verify_simple_distribution_values(self, use_case: str, node: Node):
        complex_attribute = f"{use_case}_distribution"
        if hasattr(node.individual_attributes, complex_attribute):
            self.assertEqual(getattr(node.individual_attributes, complex_attribute), None)
        self.assertEqual(getattr(node.individual_attributes, f"{use_case}_distribution_flag"), 1)
        self.assertEqual(getattr(node.individual_attributes, f"{use_case}_distribution1"), self.simple_distribution_dict['Min'])
        self.assertEqual(getattr(node.individual_attributes, f"{use_case}_distribution2"), self.simple_distribution_dict['Max'])

    def _verify_complex_distribution_values(self, use_case: str, node: Node, expected: Updateable):
        self.assertIsInstance(getattr(node.individual_attributes, f"{use_case}_distribution"), Updateable)

        # Value-checking complex distribution, not memory address checking as Updateable will not change addresses
        attributes = vars(getattr(node.individual_attributes, f"{use_case}_distribution"))
        expected_attributes = vars(expected)
        self.assertEqual(sorted(attributes.keys()), sorted((expected_attributes.keys())))
        for attribute, value in attributes.items():
            self.assertEqual(value, expected_attributes[attribute])

        flag_attribute = f"{use_case}_distribution_flag"
        if hasattr(node.individual_attributes, flag_attribute):
            self.assertEqual(getattr(node.individual_attributes, flag_attribute), None)
            self.assertEqual(getattr(node.individual_attributes, f"{use_case}_distribution1"), None)
            self.assertEqual(getattr(node.individual_attributes, f"{use_case}_distribution2"), None)

    def _test_set_simple_distribution_works(self,
                                            use_case: str,
                                            implicit_functions: List[Callable] = None,
                                            explicit=True,
                                            **kwargs):
        """
        Some common code to allow slight test variations/test naming sugar
        Args:
            explicit: True/False: explicitly or implicitly specify the default node
            kwargs: These are additional arguments to go directly to the setting function (extends reusability of this fxn).
        Returns:
            Nothing
        """

        distribution = self.simple_distribution
        selected_node_ids = [0]  # one way to specify the default node

        initial_n_implicits = len(self.demographics.implicits)
        setting_function = getattr(self.demographics, f"set_{use_case}_distribution")
        if explicit is True:
            setting_function(distribution=distribution, node_ids=selected_node_ids, **kwargs)
        else:
            setting_function(distribution=distribution, **kwargs)

        final_n_implicits = len(self.demographics.implicits)

        # check right values on modified demographics object
        nodes = self.demographics.get_nodes_by_id(node_ids=selected_node_ids)
        for _, node in nodes.items():
            self._verify_simple_distribution_values(node=node, use_case=use_case)

        # ensuring implicit config call/update(s) are set up properly
        if implicit_functions is not None:
            self.assertEqual(final_n_implicits - initial_n_implicits, len(implicit_functions))
            implicits_set = self.demographics.implicits[-1 * len(implicit_functions):]
            for i in range(len(implicits_set)):
                self.assertEqual(implicits_set[i], implicit_functions[i])
        else:
            self.assertEqual(final_n_implicits, initial_n_implicits)

    def _test_set_complex_distribution_works(self,
                                             use_case: str,
                                             distribution,
                                             implicit_functions: List[Callable] = None):
        """
        Some common code to allow slight test variations/test naming sugar
        Args:
            explicit: True/False: explicitly or implicitly specify the default node

        Returns:
            Nothing
        """
        selected_node_ids = [0]  # one way to specify the default node

        initial_n_implicits = len(self.demographics.implicits)
        setting_function = getattr(self.demographics, f"set_{use_case}_distribution")
        setting_function(distribution=distribution, node_ids=selected_node_ids)

        final_n_implicits = len(self.demographics.implicits)

        # check right values on modified demographics object
        nodes = self.demographics.get_nodes_by_id(node_ids=selected_node_ids)
        for _, node in nodes.items():
            self._verify_complex_distribution_values(node=node, expected=distribution, use_case=use_case)

        # ensuring implicit config call/update(s) are set up properly
        if implicit_functions is not None:
            self.assertEqual(final_n_implicits - initial_n_implicits, len(implicit_functions))
            implicits_set = self.demographics.implicits[-1 * len(implicit_functions):]
            for i in range(len(implicits_set)):
                self.assertEqual(implicits_set[i], implicit_functions[i])
            # self.assertEqual(self.demographics.implicits[-1], implicit_functions)
        else:
            self.assertEqual(final_n_implicits, initial_n_implicits)

    def _test_set_complex_distribution_works_twice(self, use_case: str,
                                                   distribution1, distribution2, implicit_functions: List[Callable] = None):
        """
        Ensure that setting a complex distribution more than once updates properly (last updated values win)

        Returns:
            Nothing
        """
        selected_node_ids = [0]  # one way to specify the default node

        initial_n_implicits = len(self.demographics.implicits)

        setting_function = getattr(self.demographics, f"set_{use_case}_distribution")
        setting_function(distribution=distribution1, node_ids=selected_node_ids)
        setting_function(distribution=distribution2, node_ids=selected_node_ids)

        final_n_implicits = len(self.demographics.implicits)

        # check right values on modified demographics object
        nodes = self.demographics.get_nodes_by_id(node_ids=selected_node_ids)
        for _, node in nodes.items():
            self._verify_complex_distribution_values(node=node, expected=distribution2, use_case=use_case)

        # ensuring implicit config call/update(s) are set up properly
        if implicit_functions is not None:
            self.assertEqual(final_n_implicits - initial_n_implicits, 2 * len(implicit_functions))
            implicits_set = self.demographics.implicits[-2 * len(implicit_functions):]  # They've been set twice
            implicit_functions = implicit_functions + implicit_functions  # They've been set twice
            for i in range(len(implicits_set)):
                self.assertEqual(implicits_set[i], implicit_functions[i])
            # self.assertEqual(self.demographics.implicits[-1], implicit_functions)
        else:
            self.assertEqual(final_n_implicits, initial_n_implicits)

    #
    # Distribution-specific tests (age, fertility, mortality, ...)
    #

    #
    # Age distributions
    #

    def test_set_simple_age_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_age_simple
        self._test_set_simple_distribution_works(use_case='age', implicit_functions=[_set_age_simple])

    def test_set_complex_age_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_age_complex
        self._test_set_complex_distribution_works(use_case='age', implicit_functions=[_set_age_complex],
                                                  distribution=self.complex_age_distribution1)

    def test_set_complex_age_distribution_works_twice(self):
        from emod_api.demographics.DemographicsTemplates import _set_age_complex
        self._test_set_complex_distribution_works_twice(use_case='age', implicit_functions=[_set_age_complex],
                                                        distribution1=self.complex_age_distribution1,
                                                        distribution2=self.complex_age_distribution2)

    #
    # Susceptibility distributions
    #

    def test_set_simple_susceptibility_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_suscept_simple
        self._test_set_simple_distribution_works(use_case='susceptibility', implicit_functions=[_set_suscept_simple])

    def test_set_complex_susceptibility_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_suscept_complex
        self._test_set_complex_distribution_works(use_case='susceptibility', implicit_functions=[_set_suscept_complex],
                                                  distribution=self.complex_susceptibility_distribution1)

    def test_set_complex_susceptibility_distribution_works_twice(self):
        from emod_api.demographics.DemographicsTemplates import _set_suscept_complex
        self._test_set_complex_distribution_works_twice(use_case='susceptibility', implicit_functions=[_set_suscept_complex],
                                                        distribution1=self.complex_susceptibility_distribution1,
                                                        distribution2=self.complex_susceptibility_distribution2)

    #
    #  Simple-only distributions
    #

    def test_set_simple_prevalence_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_init_prev
        self._test_set_simple_distribution_works(use_case='prevalence', implicit_functions=[_set_init_prev])

    # TODO: move risk to emodpy-malaria
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/706
    # def test_set_simple_risk_distribution_works(self):
    #     from emod_api.demographics.DemographicsTemplates import _set_enable_demog_risk
    #     self._test_set_simple_distribution_works(use_case='risk_', implicit_functions=[_set_enable_demog_risk])

    def test_set_simple_migration_heterogeneity_distribution_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity
        implicit_functions = [_set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity]
        self._test_set_simple_distribution_works(use_case='migration_heterogeneity',
                                                 implicit_functions=implicit_functions)

    # TODO: move innate_immune to emodpy-malaria
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/706
    # def test_set_simple_innate_immune_distribution_works(self):
    #     from emod_api.demographics.DemographicsTemplates import _set_immune_variation_type_cytokine_killing, \
    #         _set_immune_variation_type_pyrogenic_threshold
    #
    #     # cytokine killing should be allowed
    #     self._test_set_simple_distribution_works(use_case='innate_immune',
    #                                              implicit_functions=[_set_immune_variation_type_cytokine_killing],
    #                                              innate_immune_variation_type=Demographics.CYTOKINE_KILLING)
    #
    #     # pyrogenic threshold should be allowed
    #     self._test_set_simple_distribution_works(use_case='innate_immune',
    #                                              implicit_functions=[_set_immune_variation_type_pyrogenic_threshold],
    #                                              innate_immune_variation_type=Demographics.PYROGENIC_THRESHOLD)
    #
    # def test_set_simple_innate_immune_distribution_detects_bad_variation_type(self):
    #     self.assertRaises(ValueError,
    #                       self.demographics.set_innate_immune_distribution,
    #                       distribution=self.simple_distribution,
    #                       innate_immune_variation_type="This is only a test. BEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEP")

    #
    # Complex-only distributions
    #

    def test_set_complex_mortality_distribution_by_year_works(self):
        # This one is weird, because it uses two args for distributions that vary from the standard used by all the
        # others.
        from emod_api.demographics.DemographicsTemplates import _set_enable_natural_mortality, _set_mortality_age_gender_year

        implicit_functions = [_set_enable_natural_mortality, _set_mortality_age_gender_year]
        selected_node_ids = [0]  # one way to specify the default node
        male_distribution = self.complex_mortality_distribution1
        female_distribution = self.complex_mortality_distribution2

        initial_n_implicits = len(self.demographics.implicits)
        setting_function = getattr(self.demographics, "set_mortality_distribution")
        setting_function(distribution_male=male_distribution, distribution_female=female_distribution,
                         node_ids=selected_node_ids)
        final_n_implicits = len(self.demographics.implicits)

        # check right values on modified demographics object
        nodes = self.demographics.get_nodes_by_id(node_ids=selected_node_ids)
        for _, node in nodes.items():
            self._verify_complex_distribution_values(node=node, expected=male_distribution, use_case="mortality_male")
            self._verify_complex_distribution_values(node=node, expected=female_distribution, use_case="mortality_female")

        # ensuring implicit config call/update(s) are set up properly
        if implicit_functions is not None:
            self.assertEqual(final_n_implicits - initial_n_implicits, len(implicit_functions))
            implicits_set = self.demographics.implicits[-1 * len(implicit_functions):]
            for i in range(len(implicits_set)):
                self.assertEqual(implicits_set[i], implicit_functions[i])
        else:
            self.assertEqual(final_n_implicits, initial_n_implicits)

    #
    # For these tests, it doesn't matter if we use simple, complex, age_, mortality_, ... distributions. Just use one.
    #

    def test_setting_simple_then_complex_distribution_works(self):
        """
        Ensure that a user swapping from a simple to a complex distribution yields a correct complex result
        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_age_simple, _set_age_complex
        self._test_set_simple_distribution_works(use_case='age', implicit_functions=[_set_age_simple])
        self._test_set_complex_distribution_works(use_case='age', implicit_functions=[_set_age_complex],
                                                  distribution=self.complex_age_distribution1)

    def test_setting_complex_then_simple_distribution_works(self):
        """
        Ensure that a user swapping from a complex to simple distribution yields a correct simple result
        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_age_simple, _set_age_complex
        self._test_set_complex_distribution_works(use_case='age', implicit_functions=[_set_age_complex],
                                                  distribution=self.complex_age_distribution1)
        self._test_set_simple_distribution_works(use_case='age', implicit_functions=[_set_age_simple])

    # No need to re-implement these when other tests are doing the exact same thing & we can reuse the code
    def test_explicit_node_selection_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_age_simple
        self._test_set_simple_distribution_works(use_case='age', implicit_functions=[_set_age_simple], explicit=True)

    def test_implicit_node_selection_works(self):
        from emod_api.demographics.DemographicsTemplates import _set_age_simple
        self._test_set_simple_distribution_works(use_case='age', implicit_functions=[_set_age_simple], explicit=False)

    def test_add_ip_specific_node(self):
        self.demographics.nodes.append(Node(lat=0, lon=1, pop=100, name='two', forced_id=2))
        key = 'Risk'
        values = ['high', 'low']
        initial_distribution = [0.1, 0.9]
        ip_dictionary_expected0 = {
            "Property": key,
            "Values": values,
            "Initial_Distribution": initial_distribution}
        self.demographics.add_individual_property(property=key, values=values,
                                                  initial_distribution=initial_distribution)

        property = 'Cat'
        values = ['Asleep', 'Awake']
        initial_distribution = [0.3, 0.7]
        ip_dictionary_expected1 = {
            "Property": property,
            "Values": values,
            "Initial_Distribution": initial_distribution}
        self.demographics.nodes.append(Node(lat=0, lon=1, pop=100, name='two', forced_id=2))
        self.demographics.add_individual_property(property=property, values=values,
                                                  initial_distribution=initial_distribution, node_ids=[2])

        new_ip = self.demographics.get_node_by_id(0).individual_properties[0]
        self.assertEqual(new_ip.to_dict(), ip_dictionary_expected0)

        new_ip = self.demographics.get_node_by_id(2).individual_properties[0]
        self.assertEqual(new_ip.to_dict(), ip_dictionary_expected1)

    def test_add_ip_and_hint_errors(self):
        key = 'Cat'
        values = ['Asleep', 'Awake']
        initial_distribution = [0.3, 0.7]
        with self.assertRaises(ValueError) as context:
            self.demographics.add_individual_property(property=key, values=values,
                                                      initial_distribution=initial_distribution)
            self.demographics.add_individual_property(property=key, values=values,
                                                      initial_distribution=initial_distribution)
        self.assertTrue("Property key 'Cat' already present in IndividualProperties list" in str(context.exception),
                        msg=str(context.exception))


if __name__ == '__main__':
    unittest.main()
