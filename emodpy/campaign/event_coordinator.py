from typing import Union

from emod_api import campaign as api_campaign, schema_to_class as s2c

from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions
from emodpy.campaign.base_intervention import IndividualIntervention, NodeIntervention
from emodpy.campaign.individual_intervention import MultiInterventionDistributor
from emodpy.campaign.node_intervention import MultiNodeInterventionDistributor
from emodpy.utils.targeting_config import AbstractTargetingConfig


class BaseEventCoordinator:
    """
    The EventCoordinator class is the base class for all event coordinators. It is not intended for direct use.
    """
    def __init__(self, campaign: api_campaign,
                 event_coordinator_class_name: str):
        """
        Initializes an EventCoordinator object with the given parameters.

        Args:
            campaign (api_campaign):
                - The campaign object to which the event will be added. This should be the emod_api.campaign module.
            event_coordinator_class_name (str):
                - The name of the event coordinator class to be used. This should match the schema.
        """
        self._coordinator = s2c.get_class_with_defaults(event_coordinator_class_name, campaign.schema_path)

    def to_schema_dict(self) -> s2c.ReadOnlyDict:
        """
        Returns the EventCoordinator object as a dictionary that match the schema and can be used in the campaign.
        """
        return self._coordinator


class InterventionDistributorEventCoordinator(BaseEventCoordinator):
    """
    The InterventionDistributorEventCoordinator class is a base class for all event coordinators that distribute
    list of interventions and has a parameter Intervention_Config.
    """
    def __init__(self, campaign: api_campaign,
                 event_coordinator_class_name: str,
                 intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]]):
        super().__init__(campaign, event_coordinator_class_name)
        self.intervention_list = intervention_list
        self.validate_intervention_list()
        self.set_intervention_list(campaign)

    def validate_intervention_list(self):
        """
        Check that the intervention_list is not empty and should be a list of IndividualIntervention or NodeIntervention
        """
        if not self.intervention_list or not isinstance(self.intervention_list, list):
            raise ValueError("intervention_list should not be empty.")
        if not (all(isinstance(intervention, IndividualIntervention) for intervention in self.intervention_list)
                or all(isinstance(intervention, NodeIntervention) for intervention in self.intervention_list)):
            individual_interventions = []
            node_interventions = []
            for intervention in self.intervention_list:
                if isinstance(intervention, IndividualIntervention):
                    individual_interventions.append(intervention.__class__.__name__)
                else:
                    node_interventions.append(intervention.__class__.__name__)
            raise ValueError(f"intervention_list should contain only IndividualIntervention "
                             f"or only NodeIntervention objects, but you have IndividualInterventions"
                             f": {individual_interventions} and NodeInterventions: {node_interventions}")

    def set_intervention_list(self, campaign):
        """
        Set the intervention list in the coordinator using the MultiInterventionDistributor or MultiNodeInterventionDistributor
        """
        if len(self.intervention_list) > 1:
            if isinstance(self.intervention_list[0], IndividualIntervention):
                self._coordinator.Intervention_Config = MultiInterventionDistributor(campaign, self.intervention_list).to_schema_dict()
            else:
                self._coordinator.Intervention_Config = MultiNodeInterventionDistributor(campaign, self.intervention_list).to_schema_dict()
        else:
            self._coordinator.Intervention_Config = self.intervention_list[0].to_schema_dict()


class StandardEventCoordinator(InterventionDistributorEventCoordinator):
    """
    The StandardEventCoordinator coordinator class distributes an individual-level or node-level
    intervention to a specified fraction of individuals or nodes within a node set. Recurring campaigns can be created
    by specifying the number of times distributions should occur and the time between repetitions.

    Demographic restrictions such as Demographic_Coverage and Target_Gender do not apply when distributing node-level
    interventions. The node-level intervention must handle the demographic restrictions.
    """
    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]],
                 target_demographics_config: TargetDemographicsConfig = None,
                 repetition_config: RepetitionConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None):
        """
        StandardEventCoordinator class to create a StandardEventCoordinator with given parameters and return the coordinator.

        NOTE: The actual object in EMOD is StandardInterventionDistributionEventCoordinator, but we use StandardEventCoordinator here for short.

        Args:
            campaign (api_campaign): The campaign object to which the event will be added. This should be an instance of the
                emod_api.campaign class.
            intervention_list(list): A list of intervention objects. The intervention_list should contain only
                IndividualIntervention or only NodeIntervention objects.
            target_demographics_config (TargetDemographicsConfig, optional): a TargetDemographicsConfig to define the
                demographics related parameters.
            repetition_config (RepetitionConfig, optional): a RepetitionConfig to define the Number_Repetitions and
                Timesteps_Between_Repetitions parameters.
            property_restrictions (PropertyRestrictions, optional): a PropertyRestrictions to define the
                Property_Restrictions, Property_Restrictions_Within_Node and Node_Property_Restrictions in the coordinator.

        Returns:
            s2c.ReadOnlyDict: StandardEventCoordinator
        """
        super().__init__(campaign, "StandardInterventionDistributionEventCoordinator",
                         intervention_list=intervention_list)
        self.target_demographics_config = target_demographics_config
        self.repetition_config = repetition_config
        self.property_restrictions = property_restrictions
        self.targeting_config = targeting_config

        iv_name = self.intervention_list[0].to_schema_dict()['class']
        if isinstance(self.intervention_list[0], IndividualIntervention):
            if self.target_demographics_config is not None:
                self.target_demographics_config._set_target_demographics(self._coordinator)
            if self.property_restrictions is not None:
                self.property_restrictions._set_property_restrictions(self._coordinator)
            if targeting_config is not None:
                self._coordinator.Targeting_Config = self.targeting_config.to_schema_dict(campaign)
        else:
            if (self.target_demographics_config is not None
                    or self.targeting_config is not None):
                raise ValueError(f"The intervention_list contains NodeIntervention: {iv_name}, so the "
                                 f"target_demographics_config and targeting_config which targeting an individual "
                                 f"do not apply here.")
            if self.property_restrictions is not None:
                if self.property_restrictions.individual_property_restrictions:
                    raise ValueError(f"The intervention_list contains NodeIntervention: {iv_name}, so the "
                                     f"individual_property_restrictions in property_restrictions do not apply here.")
                self.property_restrictions._set_property_restrictions(self._coordinator)

        if self.repetition_config is not None:
            self.repetition_config._set_repetitions(self._coordinator)
