from emod_api import campaign as api_campaign

from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions
from emodpy.campaign.event_coordinator import StandardEventCoordinator
from emodpy.campaign.base_intervention import IndividualIntervention, NodeIntervention
from emodpy.campaign.individual_intervention import DelayedIntervention
from emodpy.campaign.node_intervention import _NodeLevelHealthTriggeredIV
from emodpy.campaign.event import create_campaign_event

from emodpy.utils.distributions import BaseDistribution
from emodpy.utils.targeting_config import AbstractTargetingConfig

from typing import List, Optional, Union


def add_intervention_scheduled(campaign: api_campaign,
                               intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]],
                               start_day: float = None,
                               start_year: float = None,
                               event_name: str = None,
                               node_ids: List[int] = None,
                               target_demographics_config: TargetDemographicsConfig = None,
                               delay_distribution: BaseDistribution = None,
                               repetition_config: RepetitionConfig = None,
                               property_restrictions: PropertyRestrictions = None,
                               targeting_config: AbstractTargetingConfig = None) -> None:
    """
    Add the intervention(s) to the campaign at scheduled time with the given parameters.

    This function distributes **individual-level or node-level interventions** to a specified fraction of individuals
    or nodes within a node set using **node_ids** argument.

    When distributing individual-level interventions, users can target specific demographics using the
    **target_demographics_config** and specify the `individual_property_restrictions` in the **PropertyRestrictions**
    object. Users can further refine the selection of individuals by using the **targeting_config** argument to target
    criteria such as whether they have a particular intervention or are in a relationship.

    The **target_demographics_config**, **property_restrictions** with `individual_property_restrictions`, and
    **targeting_config** do not apply when distributing node-level interventions.

    Recurring campaigns can be created by specifying the number of times distributions should
    occur and the time between repetitions using **repetition_config** argument.

    It can add a delay between when the individual-level interventions are distributed to the individual and when they
    receive the actual intervention using **delay_distribution** argument.

    Args:
        campaign (api_campaign, required):
            - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.
        intervention_list (Union[list[IndividualIntervention], list[NodeIntervention]], required):
            - A list of IndividualIntervention or NodeIntervention objects. It should contain only one type of intervention.
            - Refer to the emodpy(_'disease').campaign.individual_intervention module for available IndividualIntervention derived classes.
            - Refer to the emodpy(_'disease').campaign.node_intervention module for available NodeIntervention derived classes.
        start_day (float, optional):
            - The day when the event starts.
            - Either start_day or start_year is required, but not both.
            - Defaults to None.
        start_year (float, optional):
            - The year when the event starts.
            - Either start_day or start_year is required, but not both.
            - Defaults to None.
        event_name (str, optional):
            - The name of the event.
            - Defaults to None.
        node_ids (Optional[List[int]], optional):
            - A list of node IDs where the event will be applied.
            - If None, the event applies to all nodes.
            - Defaults to None.
        target_demographics_config (TargetDemographicsConfig, optional):
            - a TargetDemographicsConfig to define the demographics related parameters.
            - Defaults to None which target everyone with 100% coverage.
        delay_distribution (BaseDistribution, optional):
            - a Distribution to define the delay distribution for the IndividualIntervention.
            - It only applies when intervention_list contains IndividualIntervention.
            - Defaults to None which has no delay.
        repetition_config (RepetitionConfig, optional):
            - a RepetitionConfig to define the Number_Repetitions and Timesteps_Between_Repetitions parameters.
            - If None (default), then there is no repetition.
        property_restrictions (PropertyRestrictions, optional):
            - a PropertyRestrictions to define the Individual or Node Property_Restrictions in the coordinator.
            - If None (default), then there is no property restrictions.
        targeting_config (AbstractTargetingConfig, optional):
            - a TargetingConfig to targeting individuals.
            - Please refer to the emodpy.utils.targeting_config module for more information.
            - If None (default), then there is not extra targeting.

    Returns:
        None, add the configuration to the campaign.

    Example:
        >>> from emodpy.campaign.distributor import add_intervention_scheduled
        >>> from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions, TargetGender
        >>> from emodpy.campaign.individual_intervention import BroadcastEvent, OutbreakIndividual
        >>> from emodpy.utils.distributions import UniformDistribution
        >>> from emodpy.utils.targeting_config import IsPregnant
        >>> from emod_api import campaign as api_campaign
        >>> my_campaign = api_campaign
        >>> my_campaign.set_schema('path_to_schema.json')
        >>> # Create a list of interventions containing a BroadcastEvent and an OutbreakIndividual
        >>> my_intervention_list = [BroadcastEvent(my_campaign, broadcast_event="received_outbreak"),
        >>>                         OutbreakIndividual(my_campaign)]
        >>> # Create a UniformDistribution for the delay_distribution
        >>> uniform_distribution = UniformDistribution(0, 365)
        >>> # Create an IsPregnant targeting config
        >>> is_pregnant = IsPregnant()
        >>> # Add the event to the campaign, please note that only the first 2 arguments and start_day or start_year are required.
        >>> add_intervention_scheduled(
        >>>     campaign=my_campaign,
        >>>     intervention_list=my_intervention_list,
        >>>     # Distribute the interventions on January 1st, 1990.
        >>>     start_year=1990,
        >>>     event_name="test_event",
        >>>     # Distribute the interventions to nodes (or the people there in) 1, 2, 3
        >>>     node_ids=[1, 2, 3],
        >>>     # Distribute the interventions twice with 365 timesteps between repetitions
        >>>     repetition_config=RepetitionConfig(number_repetitions=2, timesteps_between_repetitions=365),
        >>>     # Target 70% of female individuals whose Risk is High and are pregnant
        >>>     target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7, target_gender=TargetGender.FEMALE),
        >>>     property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]]),
        >>>     targeting_config=is_pregnant,
        >>>     # Add a uniform delay (from 0 to 365 days) before the actual intervention is distributed
        >>>     delay_distribution=uniform_distribution
        >>> )
    """
    # Create a DelayedIntervention with the intervention if a delay_distribution is provided
    intervention_list = _add_delay(campaign, delay_distribution, intervention_list)

    # Create a StandardEventCoordinator with the intervention
    coordinator = StandardEventCoordinator(campaign,
                                           intervention_list=intervention_list,
                                           target_demographics_config=target_demographics_config,
                                           repetition_config=repetition_config,
                                           property_restrictions=property_restrictions,
                                           targeting_config=targeting_config)

    # Create a CampaignEvent or CampaignEventByYear with the coordinator
    event = create_campaign_event(campaign, coordinator=coordinator, event_name=event_name, node_ids=node_ids,
                                  start_day=start_day, start_year=start_year)

    # Add the event to the campaign
    campaign.add(event.to_schema_dict(campaign))


def add_intervention_triggered(campaign: api_campaign,
                               intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]],
                               triggers_list: list[str],
                               start_day: int = None,
                               start_year: float = None,
                               duration: float = -1,
                               event_name: str = None,
                               node_ids: Optional[List[int]] = None,
                               delay_distribution: BaseDistribution = None,
                               target_demographics_config: TargetDemographicsConfig = None,
                               property_restrictions: PropertyRestrictions = None,
                               targeting_config: AbstractTargetingConfig = None) -> None:
    """
    Configure the campaign to distribute an intervention to an individual when that individual broadcasts an event.
    For example, you might want to distribute a vaccine to an individual when they broadcast the EighteenMonthsOld event.
    The triggered events are specified as **triggers_list**.

    When distributing individual-level interventions, users can target specific demographics using the
    **target_demographics_config** and specify the `individual_property_restrictions` in the **PropertyRestrictions**
    object. Users can further refine the selection of individuals by using the **targeting_config** argument to target
    criteria such as whether they have a particular intervention or are in a relationship.

    The **target_demographics_config**, **property_restrictions** with `individual_property_restrictions`, and
    **targeting_config** do not apply when distributing node-level interventions.

    It can add a delay between when the individual-level interventions are distributed to the individual and when they
    receive the actual intervention using **delay_distribution** argument.

    Args:
        campaign (api_campaign, required):
            - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.
        intervention_list (Union[list[IndividualIntervention], list[NodeIntervention]], required):
            - A list of IndividualIntervention or NodeIntervention objects. It should contain only one type of intervention.
            - Refer to the emodpy(_'disease').campaign.individual_intervention module for available IndividualIntervention derived classes.
            - Refer to the emodpy(_'disease').campaign.node_intervention module for available NodeIntervention derived classes.
        triggers_list (list[str], required):
            - A list of individual-level events that trigger the distribution of the intervention_list.
            - For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria, :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own custom from elsewhere in the campaign.
            - It can not be an empty list.
        start_day (int, optional):
            - The day when the event starts.
            - Either start_day or start_year is required, but not both.
            - Defaults to None.
        start_year (float, optional):
            - The year when the event starts.
            - Either start_day or start_year is required, but not both.
            - Defaults to None.
        duration (float, optional):
            - The duration of days to listen for the events in the "triggers_list".
            - A value of -1 (the default) listens for the events and distributes the intervention until the simulation ends.
            - Minimum value: -1
            - Maximum value: 3.40282e+38
        event_name (str, optional):
            - The name of the event.
            - Defaults to None.
        node_ids (Optional[List[int]], optional):
            - A list of node IDs where the node will be listening for the events from the people in that node.
            - If None, then all nodes will be listening for the events and distributing the intervention.
            - Defaults to None.
        delay_distribution (BaseDistribution, optional):
            - a Distribution to define the delay distribution for the intervention.
            - It only applies when intervention_list contains IndividualIntervention.
            - If None (defalt), there is no delay.
        target_demographics_config (TargetDemographicsConfig, optional):
            - a TargetDemographicsConfig to define the demographics related parameters.
            - Defaults to None which target everyone with 100% coverage.
        property_restrictions (PropertyRestrictions, optional):
            - a PropertyRestrictions to define the Individual or Node Property_Restrictions in the coordinator.
            - Defaults to None which has no restrictions.
        targeting_config (AbstractTargetingConfig, optional):
            - a TargetingConfig to targeting individuals.
            - Please refer to the emodpy.utils.targeting_config module for more information.
            - If None (default), then there is not extra targeting.

    Example:
        >>> from emodpy.campaign.distributor import add_intervention_triggered
        >>> from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions, TargetGender
        >>> from emodpy.campaign.individual_intervention import BroadcastEvent, OutbreakIndividual
        >>> from emodpy.utils.distributions import ExponentialDistribution
        >>> from emodpy.utils.targeting_config import IsPregnant
        >>> from emod_api import campaign as api_campaign
        >>> my_campaign = api_campaign
        >>> my_campaign.set_schema('path_to_schema.json')
        >>> # Create a list of interventions containing a BroadcastEvent and an OutbreakIndividual
        >>> my_intervention_list = [BroadcastEvent(my_campaign, broadcast_event="received_outbreak"),
        >>>                         OutbreakIndividual(my_campaign)]
        >>> # Create an ExponentialDistribution for the delay_distribution with a mean of 10 timesteps
        >>> exponential_distribution = ExponentialDistribution(10)
        >>> # Create an is not pregnant targeting config
        >>> is_not_pregnant = ~IsPregnant()
        >>> # Add the event to the campaign, please note that only the first 3 arguments and start_day or start_year are required.
        >>> add_intervention_triggered(my_campaign,
        >>>                            my_intervention_list,
        >>>                            # Trigger the distribution of the intervention when either of the events: "trigger1" or "trigger2" are broadcast.
        >>>                            triggers_list=["trigger1", "trigger2"],
        >>>                            # Listen to the triggers for 30 days.
        >>>                            duration=30,
        >>>                            # Start the event at the 730th timestep.
        >>>                            start_day=730,
        >>>                            event_name="test_event",
        >>>                            # Have nodes 1, 2, 3 listen for the event and distribute the intervention to the people in those nodes.
        >>>                            node_ids=[1, 2, 3],
        >>>                            # Add a delay between the trigger and the actual intervention
        >>>                            delay_distribution=exponential_distribution,
        >>>                            # Target 70% of female individual from age 10 to 20 whose Risk is High and are not pregnant
        >>>                            target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
        >>>                                                                                target_gender=TargetGender.FEMALE,
        >>>                                                                                target_age_min=10,
        >>>                                                                                target_age_max=20),
        >>>                            property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]])
        >>>                            targeting_config=is_not_pregnant
        >>> )

    Returns:
        None, add the configuration to the campaign.
    """
    # Create a DelayedIntervention with the intervention if a delay_distribution is provided
    intervention_list = _add_delay(campaign, delay_distribution, intervention_list)

    # Create a NLHTI intervention with the intervention list and triggers list
    nlhti = _NodeLevelHealthTriggeredIV(campaign,
                                        intervention_list=intervention_list,
                                        trigger_condition_list=triggers_list,
                                        duration=duration,
                                        target_demographics_config=target_demographics_config,
                                        property_restrictions=property_restrictions,
                                        targeting_config=targeting_config)

    # Create a StandardEventCoordinator with the NLHTI intervention
    coordinator = StandardEventCoordinator(campaign,
                                           intervention_list=[nlhti])

    # Create a CampaignEvent or CampaignEventByYear with the coordinator
    event = create_campaign_event(campaign, coordinator=coordinator, event_name=event_name, node_ids=node_ids,
                                  start_day=start_day, start_year=start_year)

    # Add the event to the campaign
    campaign.add(event.to_schema_dict(campaign))


def _add_delay(campaign: api_campaign,
               delay_distribution: BaseDistribution,
               intervention_list: list[IndividualIntervention]) -> list[IndividualIntervention]:
    """
    Add a DelayedIntervention to each intervention if a delay_distribution is provided. It's a helper function for
    add_intervention_** functions.
    """
    if delay_distribution is not None:
        if isinstance(intervention_list[0], IndividualIntervention):
            intervention_list = [DelayedIntervention(campaign,
                                                     intervention_to_distribute_at_delay_completion=intervention_list,
                                                     delay_period_distribution=delay_distribution)]
        else:
            raise NotImplementedError("Node-level interventions do not support delay_distribution.")
    return intervention_list
