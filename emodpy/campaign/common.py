from emod_api import schema_to_class as s2c

from emodpy.utils import validate_key_value_pair
from emodpy.utils.emod_constants import MAX_AGE_YEARS
from typing import List, Union
from enum import Enum
import warnings
import re


class CommonInterventionParameters:
    """
    A class that is used to configure the common parameters for the intervention classes in the campaign object.

    Args:
        cost (float, optional):
            - The unit 'cost' per intervention distributed. For interventions distributed to people, the cost will be
              added for each person. For internventions distributed to nodes, the cost is for each node. Setting
              cost to zero for all other interventions, and to a non-zero amount for one intervention, provides a
              convenient way to track the number of times the intervention has been applied in a simulation.
            - Minimum value: 0.
            - Maximum value: 99999.
            - Defaults: None.

        disqualifying_properties (list[str], optional):
            - A list of IndividualProperty 'key:value' pairs that will prevent an intervention from being distributed
              or applied/updated (persistent interventions will abort/expire in the time step they see the change in
              their individual property). See :ref:demo-properties parameters for more information. Generally used to
              control the flow of health care access. For example, to prevent the same individual from accessing health
              care via two different routes at the same time.
            - Defaults to None.

        dont_allow_duplicates (bool, optional):
            - If set to True, the intervention is not allowed to be distributed to the same individual more than once.
            - If set to False, the intervention can be distributed to the same individual multiple times.
            - If set to None, it will use the Emod default value: False.
            - Defaults to None.

        intervention_name (str, optional):
            - The optional name used to refer to this intervention as a means to differentiate it from others that use
              the same class. If set to None, it will use the name of the intervention class.
            - Defaults to None.

        new_property_value (str, optional):
            - An optional IndividualProperty 'key:value' pair that will be assigned when the intervention is first
              applied/updated. See :ref:demo-properties parameters for more information. Generally used to indicate the
              broad category of health care cascade to which an intervention belongs to prevent individuals from
              accessing care through multiple pathways. For example, if an individual must already be taking a
              particular medication to be prescribed a new one.
            - Defaults to None.

    """
    def __init__(self,
                 cost: float = None,
                 disqualifying_properties: list[str] = None,
                 dont_allow_duplicates: bool = None,
                 intervention_name: str = None,
                 new_property_value: str = None
                 ):

        # Validate the input parameters and modify them if necessary
        self._validate_cost(cost)

        self._validate_disqualifying_properties(disqualifying_properties)

        self._validate_dont_allow_duplicates(dont_allow_duplicates)

        self._validate_intervention_name(intervention_name)

        new_property_value = self._validate_new_property_value(new_property_value)

        # Set the validated parameters to the class attributes
        self.cost = cost
        self.disqualifying_properties = disqualifying_properties
        self.dont_allow_duplicates = dont_allow_duplicates
        self.intervention_name = intervention_name
        self.new_property_value = new_property_value

    def _validate_new_property_value(self, new_property_value):
        if new_property_value is not None:
            if not isinstance(new_property_value, str):
                raise ValueError(f'new_property_value must be a string, not {type(new_property_value)}')
            new_property_value = validate_key_value_pair(new_property_value)
        return new_property_value

    def _validate_intervention_name(self, intervention_name):
        if intervention_name is not None:
            if not isinstance(intervention_name, str):
                raise ValueError(f'intervention_name must be a string, not {type(intervention_name)}')

    def _validate_dont_allow_duplicates(self, dont_allow_duplicates):
        if dont_allow_duplicates is not None:
            if not isinstance(dont_allow_duplicates, bool):
                raise ValueError(f'dont_allow_duplicates must be a boolean, not {type(dont_allow_duplicates)}')

    def _validate_disqualifying_properties(self, disqualifying_properties):
        if disqualifying_properties is not None:
            if isinstance(disqualifying_properties, list):
                for i in range(len(disqualifying_properties)):
                    if not isinstance(disqualifying_properties[i], str):
                        raise ValueError(f'Item {disqualifying_properties[i]} in disqualifying_properties is not a '
                                         f'string.')

                    disqualifying_properties[i] = validate_key_value_pair(disqualifying_properties[i])
            else:
                raise ValueError(f'disqualifying_properties must be a list, not '
                                 f'{type(disqualifying_properties)}')

    def _validate_cost(self, cost):
        if cost is not None:
            if cost < 0 or cost > 99999:
                raise ValueError("The cost should be between 0 and 99999.")


class TargetGender(Enum):
    ALL = "All"
    MALE = "Male"
    FEMALE = "Female"


class TargetDemographicsConfig:
    """
    A class that is used to configure the Demographics_Coverage, Target_Demographic, Target_Age_Min, Target_Age_Max,
    Target_Gender and Target_Residents_Only in the coordinator class. Please refer to emodpy.campaign.distributor
    for its usage.

    Args:
        demographic_coverage (float, optional):
            - The fraction of the demographic covered by the event.
            - Defaults to 1.0.

        target_age_min (float, optional):
            - The minimum age targeted by the event, in years.
            - Defaults to 0.

        target_age_max (float, optional):
            - The maximum age targeted by the event, in years.
            - Defaults to MAX_AGE_YEARS.

        target_gender (Gender, optional):
            - A member of the Gender enum indicating the gender targeted by the event.
            - The function accepts TargetGender.ALL, TargetGender.MALE, or TargetGender.FEMALE as valid inputs.
            - Defaults to Gender.ALL.

        target_residents_only (bool, optional):
            - When set to true, the intervention is only distributed to individuals that began the simulation in the node (i.e. those that claim the node as their residence).
            - You can use the MigrateIndividuals function to modify an individual's HOME node. For more details on MigrateIndividuals, refer to the Emod documentation: :doc:`emod-hiv:emod/parameter-campaign-individual-migrateindividuals`
            - Defaults to False.

    Examples:
        >>> # replace emodpy with emodpy_hiv or emodpy_malaria based on the disease you are working on.
        >>> from emodpy.campaign.common import TargetDemographicsConfig, TargetGender
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> demographics_config = TargetDemographicsConfig(demographic_coverage=0.5, target_age_min=10,
        >>>                                                target_age_max=20, target_gender=TargetGender.FEMALE)
        >>> add_intervention_scheduled(demographics_config=demographics_config, ...)
    """
    class _TargetDemographic(Enum):
        EVERYONE = "Everyone"
        EXPLICIT_AGE_RANGES = "ExplicitAgeRanges"
        EXPLICIT_AGE_RANGES_AND_GENDER = "ExplicitAgeRangesAndGender"
        EXPLICIT_GENDER = "ExplicitGender"
        _POSSIBLE_MOTHERS = "PossibleMothers"  # TODO: Not yet implemented
        _EXPLICIT_DISEASE_STATE = "ExplicitDiseaseState"  # TODO: Not yet implemented

    def __init__(self, demographic_coverage: Union[float, None] = 1.0, target_age_min: float = 0,
                 target_age_max: float = MAX_AGE_YEARS, target_gender: TargetGender = TargetGender.ALL,
                 target_residents_only: bool = False):
        self.demographic_coverage = demographic_coverage
        self.target_age_min = target_age_min
        self.target_age_max = target_age_max
        self.target_gender = target_gender
        self.target_residents_only = target_residents_only

    def _set_target_demographics(self, campaign_object: s2c.ReadOnlyDict):
        """
        A function that configure the Target_Age_Min, Target_Age_Max, Target_Gender and Target_Residents_Only for the
        campaign_object and set Target_Demographic based on the values of the first 3 parameters.

        This function is a private function that is used by the coordinator class and should not be called directly by
        user code.

        Args:
            campaign_object(s2c.ReadOnlyDict): an EventCoordinator object.

        Returns:
            This function does not return any value; instead, it modifies the campaign_object.

        """
        if self.demographic_coverage is not None:
            campaign_object.Demographic_Coverage = self.demographic_coverage
        if self.target_residents_only is not None:
            campaign_object.Target_Residents_Only = self.target_residents_only

        # Target_Demographic is 'ExplicitAgeRangesAndGender'
        if self.target_gender != TargetGender.ALL and (self.target_age_min > 0 or self.target_age_max < MAX_AGE_YEARS):
            campaign_object.Target_Age_Min = self.target_age_min
            campaign_object.Target_Age_Max = self.target_age_max
            campaign_object.Target_Gender = self.target_gender.value
            campaign_object.Target_Demographic = self._TargetDemographic.EXPLICIT_AGE_RANGES_AND_GENDER.value
        # Target_Demographic is 'ExplicitGender'
        elif self.target_gender != TargetGender.ALL:
            campaign_object.Target_Gender = self.target_gender.value
            campaign_object.Target_Demographic = self._TargetDemographic.EXPLICIT_GENDER.value
        # Target_Demographic is 'ExplicitAgeRanges'
        elif self.target_age_min > 0 or self.target_age_max < MAX_AGE_YEARS:
            campaign_object.Target_Age_Min = self.target_age_min
            campaign_object.Target_Age_Max = self.target_age_max
            campaign_object.Target_Demographic = self._TargetDemographic.EXPLICIT_AGE_RANGES.value
        # Set Target_Demographic to 'Everyone' by default
        else:
            campaign_object.Target_Demographic = self._TargetDemographic.EVERYONE.value


class RepetitionConfig:
    """
    A class that is used to configure the number of times the intervention event will occur by setting the
    Number_Repetitions, Timesteps_Between_Repetitions in the Event_Coodinator.

    It's used with emodpy.campaign.distributor.add_intervention_scheduled function.

    Args:
        number_repetitions (int, optional):
            - The number of times the event will occur. If the value is 1, it implies that there will be no repetitions and the event will occur only once.
            - This parameter accepts integer values that are greater than or equal to 1.
            - This argument is ignored if infinite_repetitions is set to True.
            - Defaults to 1.

        timesteps_between_repetitions (int, optional):
            - The number of timesteps between repetitions.
            - Used in conjunction with number_repetitions or infinite_repetitions.
            - If number_repetitions is greater than 1 or infinite_repetitions is set to True, indicating that the event will repeat, timesteps_between_repetitions should be a positive integer interval.
            - Defaults to None.

        infinite_repetitions (bool, optional):
            - If set to True, the event will repeat indefinitely.
            - If True, the number_repetitions argument is ignored and timesteps_between_repetitions must be set to a positive integer.
            - Defaults to False.

    Raises:
        ValueError: if timesteps_between_repetitions is undefined when number_repetitions is used.

    Examples:
        >>> # replace emodpy with emodpy_hiv or emodpy_malaria based on the disease you are working on.
        >>> from emodpy.campaign.common import RepetitionConfig
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> repetition_config = RepetitionConfig(number_repetitions=2, timesteps_between_repetitions=365)
        >>> add_intervention_scheduled(repetition_config=repetition_config, ...)

    """
    def __init__(self, number_repetitions: int = 1, timesteps_between_repetitions: int = None,
                 infinite_repetitions: bool = False):
        self.number_repetitions = number_repetitions
        self.timesteps_between_repetitions = timesteps_between_repetitions
        self.infinite_repetitions = infinite_repetitions
        self._verify_repetitions()
        # Set number_repetitions to -1 if infinite_repetitions is set to True
        self.number_repetitions = -1 if self.infinite_repetitions else self.number_repetitions

    def _verify_repetitions(self):
        """
        A private function that verifies the values of number_repetitions, timesteps_between_repetitions and
        infinite_repetitions.
        """
        if self.infinite_repetitions:
            if self.number_repetitions != 1:  # if number_repetitions is set to a value other than 1(default value)
                warnings.warn("The number_repetitions is ignored when infinite_repetitions is set to True.")
            self._verify_timesteps()
        else:
            if self.number_repetitions < 0:  # if number_repetitions is set to a negative value
                raise ValueError(f"number_repetitions is set to a negative value: {self.number_repetitions}, "
                                 f"please set it to a positive integer.")
            elif self.number_repetitions in [0, 1]:
                warnings.warn("number_repetitions is set to 0 or 1, the event will not be repeated.")
            elif self.number_repetitions > 1:
                self._verify_timesteps()

    def _verify_timesteps(self):
        if self.timesteps_between_repetitions is None:
            raise ValueError("timesteps_between_repetitions must be set when number_repetitions is greater than 1 or "
                             "infinite_repetitions is set to True..")
        # timesteps_between_repetitions should be a positive integer
        if self.timesteps_between_repetitions <= 0:
            raise ValueError(f"timesteps_between_repetitions is set to a non positive value: "
                             f"{self.timesteps_between_repetitions}, please set it to a positive integer.")

    def _set_repetitions(self, campaign_object: s2c.ReadOnlyDict):
        """
        A function that configure the Number_Repetitions and Timesteps_Between_Repetitions for the campaign_object.
        This function is a private function that is used by the coordinator class and should not be called directly by
        user code.

        Args:
            campaign_object: an EventCoordinator object.

        Returns:
            This function does not return any value; instead, it modifies the campaign_object.

        """
        if self.number_repetitions:
            campaign_object.Number_Repetitions = self.number_repetitions
        if self.timesteps_between_repetitions:
            campaign_object.Timesteps_Between_Repetitions = self.timesteps_between_repetitions


class PropertyRestrictions:
    """
    A class that is used to configure the individual property restrictions and node property restrictions in the
    campaign object.

    Please refer to the Emod documentation for NodeProperties and IndividualProperties parameters for more
    information:

    - HIV Emod: :doc:`emod-hiv:emod/parameter-demographics`
    - Malaria Emod: :doc:`emod-malaria:emod/parameter-demographics`

    Args:
        individual_property_restrictions (List[List[str]], optional):
            - A 2D list contains lists of the IndividualProperty key:value pairs.
            - These are defined in the demographics.
            - Individuals must have these properties to be targeted by the intervention.
            - This parameter allows you to specify AND and OR combinations of key:value pairs. Please see example 1 and 2 for more information.
            - You can either use this parameter or node_property_restrictions, but not both.
            - Defaults to None.

        node_property_restrictions (List[List[str]], optional):
            - A 2D list contains lists of the NodeProperty key:value pairs.
            - These are defined in the demographics.
            - Nodes must have these properties to be targeted by the intervention.
            - You can specify AND and OR combinations of key:value pairs with this parameter. Please see example 3 section for more information.
            - You can either use this parameter or individual_property_restrictions, but not both.
            - Defaults to None.

    Raises:
        Warnings: if both individual_property_restrictions and node_property_restrictions are not defined.
        ValueError: if both individual_property_restrictions and node_property_restrictions are defined.
        ValueError: if individual_property_restrictions or node_property_restrictions is not a 2D list(List[List[str]]).
        ValueError: if the elements in the inner list are not strings that represent dictionaries key:value pairs with at least one alphanumeric character before and after ':'.

    Examples:
        Example 1: This example demonstrates how to specify individual restrictions for targeting specific groups of people who are high risk AND whose InterventionStatus is ARTStaging.

        >>> # replace emodpy with emodpy_hiv or emodpy_malaria based on the disease you are working on.
        >>> from emodpy.campaign.common import PropertyRestrictions
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> property_restrictions = PropertyRestrictions(individual_property_restrictions=[["Risk:HIGH", "InterventionStatus:ARTStaging"]])
        >>> add_intervention_scheduled(property_restrictions=property_restrictions, ...)
        >>> # the result json should look like this:
        >>> # {
        >>> #          "Property_Restrictions_Within_Node": [
        >>> #            {
        >>> #              "Risk": "HIGH",
        >>> #              "InterventionStatus": "ARTStaging"
        >>> #            }
        >>> #          ]
        >>> # }


        Example 2: This example demonstrates how to specify individual restrictions for targeting specific groups of people. In this case, we are targeting individuals whose InterventionStatus is set to ARTStaging and who have either HIGH or MEDIUM risk behavior. In other words, we aim to target individuals who meet either of the following conditions:

                    1. "InterventionStatus is set to ARTStaging and Risk is set to HIGH"
                    2. "InterventionStatus is set to ARTStaging AND Risk is set to MEDIUM"

        >>> # replace emodpy with emodpy_hiv or emodpy_malaria based on the disease you are working on.
        >>> from emodpy.campaign.common import PropertyRestrictions
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> property_restrictions_within_node = PropertyRestrictions(
        >>>                                       individual_property_restrictions=[
        >>>                                                 ["Risk:HIGH", "InterventionStatus:ARTStaging"],
        >>>                                                 ["Risk:MEDIUM", "InterventionStatus:ARTStaging"]])
        >>> add_intervention_scheduled(property_restrictions=property_restrictions, ...)
        >>> # the result json should look like this:
        >>> # {
        >>> #          "Property_Restrictions_Within_Node": [
        >>> #            {
        >>> #              "Risk": "HIGH",
        >>> #              "InterventionStatus": "ARTStaging"
        >>> #            },
        >>> #            {
        >>> #              "Risk": "MEDIUM",
        >>> #              "InterventionStatus": "ARTStaging"
        >>> #            }
        >>> #          ]
        >>> # }

        Example 3: This example demonstrates how to use 'node_property_restrictions' to specify the NodeProperty. In this case, we are targeting nodes that meet either of the following conditions:

                    1. "Risk is set to MEDIUM and Place is set to URBAN"
                    2. "Risk is set to LOW and Place is set to RURAL"

        >>> # replace emodpy with emodpy_hiv or emodpy_malaria based on the disease you are working on.
        >>> from emodpy.campaign.common import PropertyRestrictions
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> property_restrictions = PropertyRestrictions(
        >>>                            node_property_restrictions=[
        >>>                                                 ["Risk:MEDIUM", "Place:URBAN"],
        >>>                                                 ["Risk:LOW", "Place:RURAL"]])
        >>> add_intervention_scheduled(property_restrictions=property_restrictions, ...)
        >>> # the result json should look like this:
        >>> # {
        >>> #          "Node_Property_Restrictions": [
        >>> #            {
        >>> #              "Risk": "MEDIUM",
        >>> #              "Place": "URBAN"
        >>> #            },
        >>> #            {
        >>> #              "Risk": "LOW",
        >>> #              "Place": "RURAL"
        >>> #            }
        >>> #          ]
        >>> # }

    """
    def __init__(self, individual_property_restrictions: List[List[str]] = None,
                 node_property_restrictions: List[List[str]] = None):
        self.individual_property_restrictions = individual_property_restrictions
        self.node_property_restrictions = node_property_restrictions
        self._verify_property_restrictions()

    def _verify_property_restrictions(self):
        if not self.individual_property_restrictions and not self.node_property_restrictions:
            warnings.warn("No property restrictions are provided.")
        elif self.individual_property_restrictions and self.node_property_restrictions:
            raise ValueError("Both individual_property_restrictions and node_property_restrictions are provided. "
                             "Please provide only one of them.")
        elif self.individual_property_restrictions:
            self._validate_restrictions(self.individual_property_restrictions, "individual_property_restrictions")
        else:  # if self.node_property_restrictions:
            self._validate_restrictions(self.node_property_restrictions, "node_property_restrictions")

    @staticmethod
    def _validate_restrictions(restrictions_list, restrictions_name):
        # check if restrictions_list is a 2D list(List[List[str]])
        if not isinstance(restrictions_list, list) or not all(isinstance(restriction, list) for restriction in
                                                              restrictions_list):
            raise ValueError(f"The {restrictions_name} should be a 2D list(List[List[str]]). "
                             f"Got {restrictions_list}. Please check your input.")
        for restrictions in restrictions_list:
            for restriction in restrictions:
                if not re.match(r"\s*\w+\s*:\s*\w+\s*", restriction):
                    raise ValueError(f"The elements in the inner list of {restrictions_name} should be strings that "
                                     f"represent dictionaries key:value pairs with at least one alphanumeric character "
                                     f"before and after ':'. Got '{restriction}'. Please check your input.")

    def _set_property_restrictions(self, campaign_object: s2c.ReadOnlyDict):
        """
        A function that configure the Property_Restrictions_Within_Node and Node_Property_Restrictions
        for the campaign_object. This function is a private function that is used by the coordinator class and should
        not be called directly by user code.
        Args:
            campaign_object: An EventCoordinator or Intervention object.

        Returns:
            This function does not return any value; instead, it modifies the campaign_object.

        """
        def parse_to_dict(list_of_lists):
            """
            A helper function that parse the list of lists to a list of dictionaries of key-value-pairs where each dict
            can only contain a given key once.
            Args:
                list_of_lists:

            Returns:
                list of dictionaries of key-value-pairs where each dict can only contain a given key once.

            """
            result = []
            for inner_list in list_of_lists:
                dict_item = {}
                for item in inner_list:
                    key, value = item.split(':')
                    dict_item[key.strip()] = value.strip()
                result.append(dict_item)
            return result

        if self.individual_property_restrictions:
            campaign_object.Property_Restrictions_Within_Node = parse_to_dict(self.individual_property_restrictions)
            if hasattr(campaign_object, 'Property_Restrictions'):
                campaign_object.Property_Restrictions = []
        if self.node_property_restrictions:
            campaign_object.Node_Property_Restrictions = parse_to_dict(self.node_property_restrictions)


class ValueMap:
    """
    Create a ValueMap object to configure the Times and Values for ValueMap in the campaign_object. This is used,
    for example, in certain WaningConfig classes to configure Vaccine interventions.

    The ValueMap object is initialized with two lists: times and values. The times list represents specific points in
    time (in years), and the values list represents the corresponding values at those times. Depending on the type of
    campaign object used, the values are either interpolated linearly or remain constant between the specified times.

    Requirements:
    - The number of elements in the times and values lists must be the same.
    - The times list must be in ascending order.
    - Both times and values must be non-negative numbers.

    Args:
        times (List[float]):
            - A list of times (in years) at which the value changes.
            - The times should be in ascending order.

        values (List[float]):
            - A list of values that correspond to the times.
            - The list of values should have the same length as times.

    """
    def __init__(self, times: List[float], values: List[float]):
        if not isinstance(times, list) or not isinstance(values, list):
            raise ValueError("times and values should be lists.")
        if len(times) != len(values):
            raise ValueError("The length of times and values should be the same.")
        if times != sorted(times):
            raise ValueError("The times should be in ascending order.")
        # Times and values should be non-negative numbers
        if any(time < 0 for time in times) or any(value < 0 for value in values):
            raise ValueError("The times and values should be non-negative numbers.")
        self._times = times
        self._values = values

    def __eq__(self, other):
        if not isinstance(other, ValueMap):
            return False
        return self._times == other._times and self._values == other._values

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        A function that converts the ValueMap object to a schema dictionary.
        """
        value_map = s2c.get_class_with_defaults("idmType:InterpolatedValueMap", schema_json=campaign.get_schema())
        value_map.Times = self._times
        value_map.Values = self._values
        value_map.pop('schema', None)
        value_map.pop('explicits', None)
        return value_map
