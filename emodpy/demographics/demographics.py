from typing import List, Callable, Dict, Union

from emod_api.demographics.Demographics import Demographics as EMODAPIDemographics
from emod_api.demographics.Node import Node
from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emodpy.utils.distributions import BaseDistribution
from emod_api.demographics.PropertiesAndAttributes import IndividualProperty


class Demographics(EMODAPIDemographics):
    PYROGENIC_THRESHOLD = 'PYROGENIC_THRESHOLD'
    CYTOKINE_KILLING = 'CYTOKINE_KILLING'

    def __init__(self, nodes: List[Node], default_node: Node, idref: str = "Gridded world grump2.5arcmin"):
        # Forces emodpy-layer Demographics instantiation to use Node object-route for default node . Cannot use
        # the old self.raw dict representation of a default node.
        super().__init__(nodes=nodes, default_node=default_node, idref=idref)

    @property
    def raw(self):
        raise AttributeError("raw is not a valid attribute for HIVDemographics objects")

    @raw.setter
    def raw(self, value):
        raise AttributeError("raw is not a valid attribute for HIVDemographics objects")

    def set_birth_rate(self, rate: float, node_ids: List[int] = None):
        """
        Sets a specified population-dependent birth rate value on the target node(s). Automatically handles any
        necessary config updates.

        Args:
            rate: (float) The birth rate to set in units of births/year/1000-women
            node_ids: (List[int]) The node id(s) to apply changes to. None or 0 means the default node.

        Returns:

        """
        from emod_api.demographics.DemographicsTemplates import _set_population_dependent_birth_rate

        rate = rate / 365 / 1000  # converting to births/day/woman, which is what EMOD internally uses.
        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            node.birth_rate = rate
        self.implicits.append(_set_population_dependent_birth_rate)

    #
    # These distribution setters accept either a simple or complex distribution
    #

    def set_age_distribution(self,
                             distribution: [BaseDistribution, AgeDistribution],
                             node_ids: List[int] = None) -> None:
        """
        Set the distribution from which the initial ages of the population will be drawn. At initialization, each person
        will be randomly assigned an age from the given distribution. Automatically handles any necessary config
        updates.

        Args:
            distribution: The distribution to set. Can either be a BaseDistribution object for a simple distribution
                or AgeDistribution object for complex.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_age_simple, _set_age_complex

        self._set_distribution(distribution=distribution,
                               use_case='age',
                               simple_distribution_implicits=[_set_age_simple],
                               complex_distribution_implicits=[_set_age_complex],
                               node_ids=node_ids)

    def set_susceptibility_distribution(self,
                                        distribution: SusceptibilityDistribution,
                                        node_ids: List[int] = None) -> None:
        """
        Set a distribution that will impact the probability that a person will acquire an infection based on immunity.
        The SusceptibilityDistribution is used to define an age-based distribution from which a probability is selected
        to determine if a person is susceptible or not. The older ages of the distribution are only used during
        initialization. Automatically handles any necessary config updates.


        Args:
            distribution: The distribution to set. Must be a SusceptibilityDistribution object for a complex
                distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_suscept_simple, _set_suscept_complex

        self._set_distribution(distribution=distribution,
                               use_case='susceptibility',
                               simple_distribution_implicits=[_set_suscept_simple],
                               complex_distribution_implicits=[_set_suscept_complex],
                               node_ids=node_ids)

    #
    # These distribution setters only accept simple distributions
    #

    def set_prevalence_distribution(self,
                                    distribution: BaseDistribution,
                                    node_ids: List[int] = None) -> None:
        """
        Sets a prevalence distribution on the demographics object. Automatically handles any necessary config updates.

        Args:
            distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_init_prev

        self._set_distribution(distribution=distribution,
                               use_case='prevalence',
                               simple_distribution_implicits=[_set_init_prev],
                               node_ids=node_ids)

    # TODO: This belongs in emodpy-malaria, as that is the one disease that uses this set of parameters.
    #  Should be moved into a subclass of emodpy Demographics inside emodpy-malaria during a 2.0 conversion of it.
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/706
    # def set_risk_distribution(self,
    #                           distribution: BaseDistribution,
    #                           node_ids: List[int] = None) -> None:
    #     """
    #     Sets a risk distribution on the demographics object. Automatically handles any necessary config updates.
    #
    #     Args:
    #         distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
    #         node_ids: The node id(s) to apply changes to. None or 0 means the default node.
    #
    #     Returns:
    #         Nothing
    #     """
    #     from emod_api.demographics.DemographicsTemplates import _set_enable_demog_risk
    #
    #     self._set_distribution(distribution=distribution,
    #                            use_case='risk',
    #                            simple_distribution_implicits=[_set_enable_demog_risk],
    #                            node_ids=node_ids)

    def set_migration_heterogeneity_distribution(self,
                                                 distribution: BaseDistribution,
                                                 node_ids: List[int] = None) -> None:
        """
        Sets a migration heterogeneity distribution on the demographics object. Automatically handles any necessary
        config updates.

        Args:
            distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_migration_model_fixed_rate, \
            _set_enable_migration_model_heterogeneity

        implicits = [_set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity]
        self._set_distribution(distribution=distribution,
                               use_case='migration_heterogeneity',
                               simple_distribution_implicits=implicits,
                               node_ids=node_ids)

    # TODO: This belongs in emodpy-malaria, as that is the one disease that uses this set of parameters.
    #  Should be moved into a subclass of emodpy Demographics inside emodpy-malaria during a 2.0 conversion of it.
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/706
    # def set_innate_immune_distribution(self,
    #                                    distribution: BaseDistribution,
    #                                    innate_immune_variation_type: str,
    #                                    node_ids: List[int] = None) -> None:
    #     """
    #     Sets a innate immune distribution on the demographics object. Automatically handles any necessary config
    #     updates.
    #
    #     Args:
    #         distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
    #         innate_immune_variation_type: the variation type to configure in EMOD. Must be either CYTOKINE_KILLING
    #             or PYROGENIC_THRESHOLD to be compatible with setting a innate immune distribution.
    #         node_ids: The node id(s) to apply changes to. None or 0 means the default node.
    #
    #     Returns:
    #         Nothing
    #     """
    #     from emod_api.demographics.DemographicsTemplates import _set_immune_variation_type_cytokine_killing, \
    #         _set_immune_variation_type_pyrogenic_threshold
    #
    #     valid_types = [self.CYTOKINE_KILLING, self.PYROGENIC_THRESHOLD]
    #     if innate_immune_variation_type == self.CYTOKINE_KILLING:
    #         implicits = [_set_immune_variation_type_cytokine_killing]
    #     elif innate_immune_variation_type == self.PYROGENIC_THRESHOLD:
    #         implicits = [_set_immune_variation_type_pyrogenic_threshold]
    #     else:
    #         valid_types_str = ', '.join(valid_types)
    #         raise ValueError(f'innate_immune_variation_type must be one of: {valid_types_str} ... to allow use of a '
    #                          f'distribution.')
    #
    #     self._set_distribution(distribution=distribution,
    #                            use_case='innate_immune',
    #                            simple_distribution_implicits=implicits,
    #                            node_ids=node_ids)

    #
    # These distribution setters only accept complex distributions
    #

    def set_mortality_distribution(self,
                                   distribution_male: MortalityDistribution,
                                   distribution_female: MortalityDistribution,
                                   node_ids: List[int] = None) -> None:
        """
        Sets the gendered mortality distributions on the demographics object. Automatically handles any necessary
        config updates.

        Args:
            distribution_male: The male MortalityDistribution to set. Must be a MortalityDistribution object for a
                complex distribution.
            distribution_female: The female MortalityDistribution to set. Must be a MortalityDistribution object for a
                complex distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.DemographicsTemplates import _set_enable_natural_mortality, \
            _set_mortality_age_gender_year

        # Note that we only need to set the implicit function once, even though we set two distributions.
        implicits = [_set_enable_natural_mortality, _set_mortality_age_gender_year]
        self._set_distribution(distribution=distribution_male,
                               use_case='mortality_male',
                               complex_distribution_implicits=implicits,
                               node_ids=node_ids)
        self._set_distribution(distribution=distribution_female,
                               use_case='mortality_female',
                               node_ids=node_ids)

    def _set_distribution(self,
                          distribution: [BaseDistribution,
                                         AgeDistribution,
                                         SusceptibilityDistribution,
                                         FertilityDistribution,
                                         MortalityDistribution],
                          use_case: str,
                          simple_distribution_implicits: List[Callable] = None,
                          complex_distribution_implicits: List[Callable] = None,
                          node_ids: List[int] = None) -> None:
        """
        A common core function for setting simple and complex distributions for all uses in EMOD demographics. This
        should not be called directly by users.

        Args:
            distribution: The distribution object to set. If it is a BaseDistribution object, a simple distribution
                will be set on the demographics object. If it is of any other allowed type, a complex distribution is
                set.
            use_case: A string used to identify which function to call on specified nodes to properly configure the
                specified distribution.
            simple_distribution_implicits: for simple distributions, a list of functions to call at config build-time to
                ensure the specified distribution is utilized properly.
            complex_distribution_implicits: for complex distributions, a list of functions to call at config build-time
                to ensure the specified distribution is utilized properly.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        if isinstance(distribution, BaseDistribution):
            distribution_values = distribution.get_demographic_distribution_parameters()
            function_name = f"_set_{use_case}_simple_distribution"
            implicit_calls = simple_distribution_implicits
        else:
            function_name = f"_set_{use_case}_complex_distribution"
            distribution_values = {'distribution': distribution}
            implicit_calls = complex_distribution_implicits

        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            getattr(node, function_name)(**distribution_values)

        # ensure the config is properly set up to know about this distribution
        if implicit_calls is not None:
            self.implicits.extend(implicit_calls)

    def to_dict(self) -> Dict:
        demographics_dict = {
            'Defaults': self.default_node.to_dict(),
            'Nodes': [node.to_dict() for node in self.nodes],
            'Metadata': self.metadata
        }
        demographics_dict["Metadata"]["NodeCount"] = len(self.nodes)
        return demographics_dict

    def add_individual_property(self, property: str,
                                values: Union[List[str], List[float]] = None,
                                initial_distribution: List[float] = None,
                                node_ids: List[int] = None,
                                overwrite_existing: bool = False) -> None:
        """
        Adds a new individual property or replace values on an already-existing property in a demographics object.

        Individual properties act as 'labels' on model agents that can be used for identifying and targeting
        subpopulations in campaign elements and reports. E.g. model agents may be given a property ('Accessibility')
        that labels them as either having access to health care (value: 'Yes') or not (value: 'No').

        Note: EMOD requires individual property key and values (property and values arguments) to be the same across all
            nodes. The individual distributions of individual properties (initial_distribution) can vary across nodes.

        Documentation of individual properties and HINT:
            For malaria, see :doc:`emod-malaria:emod/model-properties`
                    and for HIV, see :doc:`emod-hiv:emod/model-properties`.

        Args:
            property: a new individual property key to add. If property already exists an exception is raised
                unless overwrite_existing is True.
            values: A list of valid values for the property key. E.g. ['Yes', 'No'] for an 'Accessibility' property key.
            initial_distribution: The fractional, between 0 and 1, initial distribution of each valid values entry.
                Order must match values argument. The values must add up to 1.
            node_ids: The node ids to apply changes to. None or 0 means the 'Defaults' node, which will apply to all
                the nodes unless a node has its own individual properties re-definition.
            overwrite_existing: When True, overwrites existing individual properties with the same key. If False,
                raises an exception if the property already exists in the node(s).

        Returns:
            None
        """
        nodes = self.get_nodes_by_id(node_ids=node_ids).values()
        individual_property = IndividualProperty(property=property,
                                                 values=values,
                                                 initial_distribution=initial_distribution)
        for node in nodes:
            if not overwrite_existing and node.has_individual_property(property_key=property):
                raise ValueError(f"Property key '{property}' already present in IndividualProperties list")

            node.individual_properties.add(individual_property=individual_property, overwrite=overwrite_existing)
