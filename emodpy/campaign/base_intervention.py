import warnings

from emodpy.campaign.common import CommonInterventionParameters
from emodpy.utils.emod_enum import StrEnum
from emodpy.utils import is_valid_key_value_pair
from emodpy.utils.distributions import BaseDistribution

from emod_api import schema_to_class as s2c
from emod_api import campaign as api_campaign

from typing import Union


class InterventionType(StrEnum):
    NodeIntervention = 'NodeIntervention'
    IndividualIntervention = 'IndividualIntervention'


class _BaseIntervention:
    """
    This is the base class for interventions. It is not intended for direct use.

    Args:
        campaign (campaign): An instance of the emod_api.campaign module.
        intervention_class_name (str): The name of the intervention class to be used. This should match the schema.
        intervention_type (InterventionType): The type of intervention to be used. This should be either NodeIntervention
            or IndividualIntervention.
        common_intervention_parameters (CommonInterventionParameters): The CommonInterventionParameters object that
            contains the 5 common parameters: cost, disqualifying_properties, dont_allow_duplicates, intervention_name,
            and new_property_value for the intervention.
    """
    def __init__(self,
                 campaign: api_campaign,
                 intervention_class_name: str,
                 intervention_type: InterventionType,
                 common_intervention_parameters: CommonInterventionParameters = None):

        self._intervention = s2c.get_class_with_defaults(intervention_class_name, campaign.schema_path)
        self.intervention_class_name = intervention_class_name
        self.intervention_type = intervention_type
        if common_intervention_parameters is not None:
            self._set_common_intervention_parameters(common_intervention_parameters)

    def _set_common_intervention_parameters(self, common_intervention_parameters: CommonInterventionParameters) -> None:
        """
        Set the common parameters of the intervention.
        Args:
            common_intervention_parameters(CommonInterventionParameters): The common parameters of the intervention.

        Returns:
            None, modifies the intervention in place.

        """
        if not isinstance(common_intervention_parameters, CommonInterventionParameters):
            raise ValueError(f'common_intervention_parameters must be an instance of CommomInterventionParameters, not '
                             f'{type(common_intervention_parameters)}')
        if common_intervention_parameters.cost is not None:
            self._set_cost(common_intervention_parameters.cost)
        if common_intervention_parameters.disqualifying_properties is not None:
            self._set_disqualifying_properties(common_intervention_parameters.disqualifying_properties)
        if common_intervention_parameters.dont_allow_duplicates is not None:
            self._set_dont_allow_duplicates(common_intervention_parameters.dont_allow_duplicates)
        if common_intervention_parameters.intervention_name is not None:
            self._set_intervention_name(common_intervention_parameters.intervention_name)
        if common_intervention_parameters.new_property_value is not None:
            self._set_new_property_value(common_intervention_parameters.new_property_value)

    def _set_cost(self, cost: float) -> None:
        """
        Set the Cost_To_Consumer of the intervention.
        Args:
            cost(float): The cost of getting the intervention each time it is distributed.

        Returns:
            None, modifies the intervention in place.

        """
        if cost < 0 or cost > 999999:
            raise ValueError('cost must be a float between 0 and 999999.')
        self._intervention.Cost_To_Consumer = cost

    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:
        """
        Set the Disqualifying_Properties of the intervention.
        Args:
            disqualifying_properties(Union[dict[str, str], list[str]]): A list or dictionary that represents the
                IndividualProperty key:value pairs that cause an intervention to be aborted.

        Returns:
            None, modifies the intervention in place.

        """
        if disqualifying_properties is not None:
            if isinstance(disqualifying_properties, list):
                for i in range(len(disqualifying_properties)):
                    if not isinstance(disqualifying_properties[i], str):
                        raise ValueError(f'Item {disqualifying_properties[i]} in disqualifying_properties is not a '
                                         f'string.')

                    if is_valid_key_value_pair(disqualifying_properties[i]) is False:
                        raise ValueError(f'Item {disqualifying_properties[i]} in disqualifying_properties is not a '
                                         f'valid key:value pair.')
                    # Remove leading and trailing whitespaces in the key:value pair
                    disqualifying_properties[i] = ":".join([word.strip() for word in disqualifying_properties[i].split(":")])
            else:
                raise ValueError(f'disqualifying_properties must be a list, not '
                                 f'{type(disqualifying_properties)}')
            self._intervention.Disqualifying_Properties = disqualifying_properties

    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:
        """
        Set the Dont_Allow_Duplicates of the intervention.
        Args:
            dont_allow_duplicates(bool): If an individual's container has an intervention, set to true (1) to prevent
                them from receiving another copy of the intervention.

        Returns:
            None, modifies the intervention in place.

        """
        self._intervention.Dont_Allow_Duplicates = dont_allow_duplicates

    def _set_intervention_name(self, intervention_name: str) -> None:
        """
        Set the Intervention_Name of the intervention.
        Args:
            intervention_name(str): The optional name used to refer to this intervention as a means to differentiate it
                from others that use the same class.

        Returns:
            None, modifies the intervention in place.

        """
        self._intervention.Intervention_Name = intervention_name

    def _set_new_property_value(self, new_property_value: str) -> None:
        """
        Set the New_Property_Value of the intervention.
        Args:
            new_property_value(str): An optional IndividualProperty key:value pair that will be assigned when the
                intervention is distributed.

        Returns:
            None, modifies the intervention in place.
        """
        if not isinstance(new_property_value, str):
            raise ValueError(f'new_property_value must be a string, not {type(new_property_value)}')
        if is_valid_key_value_pair(new_property_value) is False:
            raise ValueError(f'new_property_value must be a key:value pair, not {new_property_value}')
        new_property_value = ":".join([word.strip() for word in new_property_value.split(":")])
        self._intervention.New_Property_Value = new_property_value

    def set_distribution(self, distrbution: BaseDistribution, pre_fix: str):
        if distrbution is not None:
            if not isinstance(distrbution, BaseDistribution):
                raise ValueError(f"distribution must be an instance of BaseDistribution, "
                                 f"not {type(distrbution)}.")
            distrbution.set_intervention_distribution(self._intervention, pre_fix)

    def to_schema_dict(self) -> s2c.ReadOnlyDict:
        """
        Return the intervention as a dictionary that matches the schema and can be used in the campaign.

        Returns:
            s2c.ReadOnlyDict: The intervention.
        """
        return self._intervention

    def get_intervention_name(self) -> str:
        """
        Return the intervention name if the intervention supports `Intervention_Name` as a parameter. Otherwise, return
        None.
        If the user did not set the intervention name explicitly, the default `Intervention_Name` is the class name of
        the intervention.

        Returns:
            str: The intervention name.
        """
        try:
            return self._intervention.Intervention_Name
        except AttributeError:
            warnings.warn(f"Intervention_Name is supported in this Intervention: {self.intervention_class_name}.")
            return None


class IndividualIntervention(_BaseIntervention):
    def __init__(self,
                 campaign: api_campaign,
                 intervention_class_name: str,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign,
                         intervention_class_name=intervention_class_name,
                         intervention_type=InterventionType.IndividualIntervention,
                         common_intervention_parameters=common_intervention_parameters)


class NodeIntervention(_BaseIntervention):
    def __init__(self,
                 campaign: api_campaign,
                 intervention_class_name: str,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign,
                         intervention_class_name=intervention_class_name,
                         intervention_type=InterventionType.NodeIntervention,
                         common_intervention_parameters=common_intervention_parameters)
