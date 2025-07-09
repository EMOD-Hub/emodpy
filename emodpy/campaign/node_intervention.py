from emodpy.campaign.common import TargetDemographicsConfig, CommonInterventionParameters, PropertyRestrictions
from emodpy.campaign.base_intervention import (NodeIntervention, InterventionType)
from emodpy.campaign.individual_intervention import IndividualIntervention, MultiInterventionDistributor
from emodpy.utils.distributions import BaseDistribution
from emodpy.utils import validate_key_value_pair, validate_value_range
from emodpy.utils.targeting_config import AbstractTargetingConfig
from emodpy.campaign.utils import set_event, get_trigger_conditions
from emod_api import campaign as api_campaign

from typing import Union
import warnings


class MultiNodeInterventionDistributor(NodeIntervention):
    """
    The **MultiNodeInterventionDistributor** intervention class is a node-level intervention that distributes
    multiple other node-level interventions when the distributor only allows specifying one intervention.
    This class can be thought of as an "adapter", where it can adapt interventions or coordinators that were
    designed to distribute one intervention to instead distribute many.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        node_intervention_list(list[NodeIntervention], optional):
            A list of NodeIntervention objects for the multi-node-level interventions to be distributed by this
            intervention.

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, dont_allow_duplicates, new_property_value, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 node_intervention_list: list[NodeIntervention],
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MultiNodeInterventionDistributor', common_intervention_parameters)

        self._intervention.Node_Intervention_List = [node_intervention.to_schema_dict()
                                                     for node_intervention in node_intervention_list]

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the MultiNodeInterventionDistributor intervention.')


# This is included for internal use. 99% of all needs of this functionality should be handled by add_intervention_triggered()
class _NodeLevelHealthTriggeredIV(NodeIntervention):
    """
    The **NodeLevelHealthTriggeredIV** intervention class is a node-level intervention that distributes an
    intervention to individuals when a specific event occurs to those individuals. **NodeLevelHealthTriggeredIV**
    monitors for event triggers from individuals, and when found, will distribute the intervention. For example,
    **NodeLevelHealthTriggeredIV** can be configured such that all individuals will be given a diagnostic
    intervention when they transition from susceptible to infectious. During the simulation, when individuals
    become infected, they broadcast the 'NewInfectionEvent' trigger and **NodeLevelHealthTriggeredIV**
    distributes the diagnostic intervention to them.

    Notes and tips for this intervention:

        - This is the main tool for distributing an intervention to a person when an event happens to that person.
        Note that the intervention is distributed to all individuals in the node which experience the triggering
        event.
        - This is a node-level intervention and is not serialized. If interventions were distributed prior to
        serialization, in order to have those interventions continue after starting from the serialized file,
        they must be added to the new campaign file.
        - This can be used to distribute other node-level interventions. For example, it can be used to
        distribute emodpy.campaign.node_intervention.MigrateFamily to the node when someone becomes infected
        (e.g. by listening for for 'NewInfectionEvent' or an event from EMOD).
        - A powerful feature of this intervention is that it can target specific groups of individuals who
        broadcast the event. Individuals, and subgroups of individuals, can be targeted by age, gender, and
        Individual Property.
        - Note that when distributing a node-level intervention parameters associated with targeting an
        individual (such as  target_demographic, target_age_min, target_age_max, target_gender,
        property_restrictions_within_node,
        etc.) do not apply.
        - The blackout_event_trigger is a feature that can be useful when monitoring an event from the individual
        in a node. It enables reaction to some individuals experiencing an event but ignoring subsequent
        events for a period of time. For example, SpaceSpraying could be distributed to the node on the
        first occurrence of 'NewInfectionEvent', but after spraying has occurred all other infection events
        can be ignored for a specific period of time. Without blackout_period, each infection event would
        trigger another round of spraying.
        - The distribute_on_return_home feature causes **NodeLevelHealthTriggeredIV** to keep track of
        residents when they leave the node and then return. If a person leaves the node and an intervention
        is distributed while the person is gone, **NodeLevelHealthTriggeredIV** gives the person the
        intervention (such as a vaccine dose) when they return to the node.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_list(list[Union[NodeIntervention, IndividualIntervention], required):
            The configuration of an actual individual intervention to be distributed on the trigger. Selects a
            class for the intervention and configures the parameters specific for that intervention class.

        trigger_condition_list(list[str], required):
            A list of individual events that will trigger the distribution of the intervention. The events in the list
            must either be events already used in EMOD or custom events defined to be distributed elsewhere
            in the campaign. See :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD.

        target_demographics_config(TargetDemographicsConfig, optional):
            The TargetDemographicsConfig object that is used to configure the demographcs of the targeted individuals,
            for example: demographic_coverage, target_demographic, target_age_min, target_age_max, target_gender and
            target_residents_only in the coordinator class. Please refer to the
            emodpy.campaign.common.TargetDemographicsConfig for more information.
            Default value: None

        property_restrictions(PropertyRestrictions, optional):
            A PropertyRestrictions object that can be used to restrict the distribution of the intervention to
            individuals or nodes with specific properties. Please see the emodpy.common.PropertyRestrictions for more
            information.
            Default value: None

        targeting_config(AbstractTargetingConfig, optional):
            Be more selective of individuals by using the emodpy.utils.targeting_config classes. Please refer to the
            emodpy.utils.targeting_config for more information.

        duration(float, optional):
            The number of days to continue this intervention. It will listen and respond to events during this
            time. A value of -1 (the default) keeps the intervention running indefinitely.
            Minimum value: -1
            Maximum value: 3.40282e+38
            Default value: -1

        distribute_on_return_home(bool, optional):
            When set to True, individuals will receive an intervention upon returning home if that
            intervention was originally distributed while the individual was away.
            Default value: True

        blackout_period(float, optional):
            After the initial intervention distribution, the time, in days, to wait before distributing the
            intervention again. If it cannot distribute due to the blackout period, it will broadcast the
            user-defined blackout_event_trigger.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        blackout_on_first_occurrence(bool, optional):
            If set to True, individuals will enter the blackout period after the first occurrence of an
            event in the trigger_condition_list.
            Default value: True

        blackout_event_trigger(str, optional):
            The event to broadcast if an intervention cannot be distributed due to the blackout_period.See
            :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD or use your
            own custom event.
            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: intervention_name, dont_allow_duplicates, new_property_value, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: Union[list[NodeIntervention], list[IndividualIntervention]],
                 trigger_condition_list: list[str],
                 target_demographics_config: TargetDemographicsConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None,
                 duration: float = -1,
                 distribute_on_return_home: bool = False,
                 blackout_period: float = 0,  # hide? ask Svetlana
                 blackout_on_first_occurrence: bool = False,
                 blackout_event_trigger: str = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'NodeLevelHealthTriggeredIV', common_intervention_parameters)

        self._intervention.Trigger_Condition_List = get_trigger_conditions(campaign, trigger_condition_list)

        if not intervention_list:
            raise ValueError('intervention_list must contain at least one intervention.')
        # determine the type of interventions that we are dealing with
        intervention_type = InterventionType.IndividualIntervention \
            if isinstance(intervention_list[0], IndividualIntervention) else InterventionType.NodeIntervention
        # make sure that all interventions are of the same type
        if not all(intervention.intervention_type == intervention_type for intervention in intervention_list):
            raise ValueError('All interventions in the intervention_list must be of the same type.')

        if len(intervention_list) > 1:
            # handle multiple interventions with MultiInterventionDistributor or MultiNodeInterventionDistributor
            if intervention_type == InterventionType.IndividualIntervention:
                self._intervention.Actual_IndividualIntervention_Config = MultiInterventionDistributor(campaign,
                                                                                                       intervention_list=intervention_list).to_schema_dict()
            else:
                self._intervention.Actual_NodeIntervention_Config = MultiNodeInterventionDistributor(campaign,
                                                                                                     node_intervention_list=intervention_list).to_schema_dict()
        else:
            if intervention_type == InterventionType.IndividualIntervention:
                self._intervention.Actual_IndividualIntervention_Config = intervention_list[0].to_schema_dict()
            else:
                self._intervention.Actual_NodeIntervention_Config = intervention_list[0].to_schema_dict()

        # does not meet PEP8, but this is easier to read
        if (    (intervention_type == InterventionType.NodeIntervention) # noqa: E201
            and (   (target_demographics_config is not None)             # noqa: E201, E128
                 or (property_restrictions      is not None)             # noqa: E201, E128, E272
                 or (targeting_config           is not None))):          # noqa: E201, E128, E272
            iv_name = intervention_list[0]._intervention['class']
            msg = f"The intervention, {iv_name}, is a node-level intervention, so it will be distributed to nodes.\n"
            msg += "Hence, you cannot use individual targeting parameters like:\n"
            msg += " - target_demographics_config,\n"
            msg += " - property_restrictions, or\n"
            msg += " - targeting_config"
            raise ValueError(msg)

        if target_demographics_config is not None:
            target_demographics_config._set_target_demographics(self._intervention)

        if property_restrictions is not None:
            property_restrictions._set_property_restrictions(self._intervention)

        if targeting_config is not None:
            self._intervention.Targeting_Config = targeting_config.to_simple_dict(campaign)

        self._intervention.Duration = validate_value_range(duration, 'duration', -1, 3.40282e+38, float)
        self._intervention.Distribute_On_Return_Home = distribute_on_return_home
        self._intervention.Blackout_Period = validate_value_range(blackout_period, 'blackout_period', 0, 3.40282e+38, float)
        self._intervention.Blackout_On_First_Occurrence = blackout_on_first_occurrence
        if blackout_event_trigger is not None:
            self._intervention.Blackout_Event_Trigger = set_event(blackout_event_trigger, 'blackout_event_trigger', campaign, True)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the NodeLevelHealthTriggeredIV intervention.')


class _BirthTriggeredIV(NodeIntervention):
    """
    **DEPRECATED** - Use the **Births** event with **add_intervention_triggered()**.

    The ** BirthTriggeredIV** intervention class monitors for birth events and then distributes an actual
    intervention to the new individuals as specified in **Actual_IndividualIntervention_Config**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        actual_individualintervention_config(IndividualIntervention, required):
            The configuration of an actual individual intervention to be distributed on the trigger. Selects a
            class for the intervention and configures the parameters specific for that intervention class.

        target_demographics_config(TargetDemographicsConfig, optional):
            The TargetDemographicsConfig object that is used to configure the demographcs of the targeted individuals,
            for example: Demographics_Coverage, Target_Demographic, Target_Age_Min, Target_Age_Max, Target_Gender and
            Target_Residents_Only in the coordinator class. Please refer to the emodpy.campaign.common.TargetDemographicsConfig for more information.
            Default value: None

        property_restrictions(PropertyRestrictions, optional):
            A PropertyRestrictions object that can be used to restrict the distribution of the intervention to
            individuals with specific properties. Please see the emodpy.common.PropertyRestrictions for more
            information. This Intervention only allows individual properties, not node properties.
            Default value: None

        duration(float, optional):
            The number of days to continue this intervention. It will listen and respond to events during this
            time. A value of -1 (the default) keeps the intervention running indefinitely.
            Minimum value: -1
            Maximum value: 3.40282e+38
            Default value: -1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: disqualifying_properties, dont_allow_duplicates, intervention_name, new_property_value.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_config: IndividualIntervention,
                 target_demographics_config: TargetDemographicsConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 duration: float = -1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'BirthTriggeredIV', common_intervention_parameters)

        warnings.warn("The BirthTriggeredIV intervention is deprecated and will be removed in a future release. "
                      "Please use the NodeLevelHealthTriggeredIV intervention with the 'Births' trigger conditions instead.",
                      category=DeprecationWarning, stacklevel=2)

        self._intervention.Actual_IndividualIntervention_Config = intervention_config.to_schema_dict()
        if target_demographics_config is not None:
            target_demographics_config._set_target_demographics(self._intervention)

        if property_restrictions is not None:
            property_restrictions._set_property_restrictions(self._intervention)

        # ---------------------------------------------------------------------------------------------------
        # DanB - We want to deprecate BirthTriggeredIV so we don't want people using the new Targeting_Config
        # targeting_config(AbstractTargetingConfig, optional):
        #    Be more selective of individuals by using the Targeting_Config classes.  Please refer to the
        #    emodpy.utils.targeting_config for more information.
        #
        # if targeting_config is not None:
        #     self.intervention.Targeting_Config = targeting_config.to_schema_dict(campaign)
        # ---------------------------------------------------------------------------------------------------

        self._intervention.Duration = validate_value_range(duration, 'duration', -1, 3.40282e+38, float)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the BirthTriggeredIV intervention.')


# Make this function private until we can handle the Coordinator Event.
class _BroadcastCoordinatorEventFromNode(NodeIntervention):
    """
    The **BroadcastCoordinatorEventFromNode** is node-level intervention that broadcasts an event for coordinators.
    For example, if a death occurs in a node, an event can be broadcasted that will trigger some sort of response
    by the healthcare system. **NodeLevelHealthTriggeredIV** could be used to listen for the death of an individual
    and distribute this intervention to the node. The node intervention could then broadcast its event that a
    **TriggeredEventCoordinator** is listening for. One can use the **Report_Coordinator_Event_Recorder** to report
    on the events broadcasted by this intervention. Note, this coordinator class must be used with listeners that
    are operating on the same core. For more information, see Simulation core components.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        broadcast_event(str, optional):
            The Coordinator Event to be broadcasted by this node.  An Event Coordinator like
            **TriggeredEventCoordinator** could be activated from this event. Custom events may be defined in
            **Custom_Coordinator_Events** in the simulation configuration file.
            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: disqualifying_properties, dont_allow_duplicates, intervention_name, new_property_value.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 broadcast_event: str = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'BroadcastCoordinatorEventFromNode', common_intervention_parameters)

        # todo: This Broadcast_Event is of type CoorinatorEvent. It probably needs a different _set_event() function
        self._intervention.Broadcast_Event = set_event(broadcast_event, 'broadcast_event', campaign, True)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the BroadcastCoordinatorEventFromNode intervention.')


class BroadcastNodeEvent(NodeIntervention):
    """
    The **BroadcastNodeEvent** node intervention class broadcasts node-level events. This can be used with the campaign
    class, **SurveillanceEventCoordinator**, that can monitor and listen for events received from
    **BroadcastNodeEvent** and then perform an action based on the broadcasted event. You can also use this for
    the reporting, by recording broadcasted events with :class:`emodpy.reporters.common.ReportNodeEventRecorder` or
    :class:`emodpy.reporters.common.ReportSurveillanceEventRecorder`.
    You must use this coordinator class with listeners that are operating on the same core. You can
    also use **NLHTIVNode**. For more information, see Simulation core components.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        broadcast_event(str, optional):
            The name of the Node Event to broadcast.
            configuration parameter.
            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 5 common
            parameters: intervention_name, new_property_value, disqualifying_properties, dont_allow_duplicates, cost.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 broadcast_event: str = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'BroadcastNodeEvent', common_intervention_parameters)

        self._intervention.Broadcast_Event = set_event(broadcast_event, 'broadcast_event', campaign, True)


class ImportPressure(NodeIntervention):
    """
    The **ImportPressure** intervention class extends the **ImportCases** outbreak event. Rather than importing
    a deterministic number of cases on a scheduled day, **ImportPressure** applies a set of per-day rates of
    importation of infected individuals, over a corresponding set of durations. **ImportPressure** inherits
    from **Outbreak**; the **Antigen** and **Genome** parameters are defined as they are for all Outbreak events.

    **WARNING**

    Be careful when configuring import pressure in multi-node simulations. **Daily_Import_Pressures** defines a
    rate of per-day importation for each node that the intervention is distributed to. In a 10 node simulation
    with **Daily_Import_Pressures** = [0.1, 5.0], the total importation rate summed over all nodes will be 1/day
    and 50/day during the two time periods. You must divide the per-day importation rates by the number of nodes.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        import_age(float, optional):
            The age (in days) of infected import cases.
            Minimum value: 0
            Maximum value: 43800
            Default value: 365

        genome(int, optional):
            The genetic substrain ID of the outbreak infection. Together with **Antigen**, they are a unitary
            object representing a strain of infection, which allows for differentiation among infections.
            Minimum value: -1
            Maximum value: 16777200.0
            Default value: 0

        durations(list[int], optional):
            The durations over which to apply import pressure.
            Default value: None

        daily_import_pressures(list[float], optional):
            The rate of per-day importation for each node that the intervention is distributed to.
            Default value: None

        antigen(int, optional):
            The antigenic base strain ID of the outbreak infection.
            Minimum value: 0
            Maximum value: 10
            Default value: 0

    """

    def __init__(self,
                 campaign: api_campaign,
                 import_age: float = 365,
                 genome: int = 0,
                 durations: list[int] = None,
                 daily_import_pressures: list[float] = None,
                 antigen: int = 0):
        super().__init__(campaign, 'ImportPressure')

        self._intervention.Import_Age = validate_value_range(import_age, 'import_age', 0, 43800, float)
        self._intervention.Genome = validate_value_range(genome, 'genome', -1, 16777200.0, int)
        self._intervention.Durations = durations.copy() if durations is not None else []
        self._intervention.Daily_Import_Pressures = daily_import_pressures.copy() if daily_import_pressures is not None else []
        if antigen is not None:  # antigen is not in Generic model, workaround for Generic model
            self._intervention.Antigen = validate_value_range(antigen, 'antigen', 0, 10, int)

    def _set_intervention_name(self, intervention_name: str) -> None:
        raise ValueError('Intervention_Name is not a valid parameter for the ImportPressure intervention.')

    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:
        raise ValueError('Dont_Allow_Duplicates is not a valid parameter for the ImportPressure intervention.')

    def _set_new_property_value(self, new_property_value: str) -> None:
        raise ValueError('New_Property_Value is not a valid parameter for the ImportPressure intervention.')

    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:
        raise ValueError('Disqualifying_Properties is not a valid parameter for the ImportPressure intervention.')

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the ImportPressure intervention.')


class MigrateFamily(NodeIntervention):
    """
    The **MigrateFamily** intervention class tells family groups of residents of the targeted node to go on a
    round trip migration ("family trip"). The duration of time residents wait before migration and the time
    spent at the destination node can be configured; the pre-migration waiting timer does not start until all
    residents are at the home node.

    Use of this intervention does require that human migration be enabled by setting the configuration parameters
    **Migration_Model** to **FIXED_RATE_MIGRATION** and **Migration_Pattern** to **SINGLE_ROUND_TRIP**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        duration_before_leaving_distribution(BaseDistribution, required):
            The distribution type to use for assigning the duration of time a family waits before migrating to
            the destination node after all residents are home. Each assigned value is a random draw from the
            distribution. Please use the following distribution classes
            from emodpy.utils.distributions to define the distribution:
            * ConstantDistribution
            * UniformDistribution
            * GaussianDistribution
            * ExponentialDistribution
            * PoissonDistribution
            * LogNormalDistribution
            * DualConstantDistribution
            * WeibullDistribution
            * DualExponentialDistribution

        duration_at_node_distribution(BaseDistribution, required):
            The distribution type to use for assigning the duration of time an individual or family spends at a
            destination node after intervention-based migration. Each assigned value is a random draw from the
            distribution. Please use the following distribution classes
            from emodpy.utils.distributions to define the distribution:
            * ConstantDistribution
            * UniformDistribution
            * GaussianDistribution
            * ExponentialDistribution
            * PoissonDistribution
            * LogNormalDistribution
            * DualConstantDistribution
            * WeibullDistribution
            * DualExponentialDistribution

        nodeid_to_migrate_to(int, optional):
            The destination node ID for intervention-based migration.
            Minimum value: 0
            Maximum value: 4294970000.0
            Default value: 0

        is_moving(bool, optional):
            Set to true (1) to indicate all the individuals of the family are permanently moving to a new home
            node for intervention-based migration. Once at the new home node, trips will be made with this node
            as the root (i.e. round trips come back to this node).
            Default value: True

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: disqualifying_properties, dont_allow_duplicates, intervention_name, new_property_value.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 duration_before_leaving_distribution: BaseDistribution,
                 duration_at_node_distribution: BaseDistribution,
                 nodeid_to_migrate_to: int = 0,
                 is_moving: bool = False,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MigrateFamily', common_intervention_parameters)

        self._intervention.NodeID_To_Migrate_To = validate_value_range(nodeid_to_migrate_to, 'nodeid_to_migrate_to', 0, 4294970000.0, int)
        self._intervention.Is_Moving = is_moving
        self.set_distribution(duration_before_leaving_distribution, 'Duration_Before_Leaving')
        self.set_distribution(duration_at_node_distribution, 'Duration_At_Node')

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the MigrateFamily intervention.')


class NodePropertyValueChanger(NodeIntervention):
    """
    The **NodePropertyValueChanger** intervention class sets a given node property to a new value. You can also
    define a duration in days before the node property reverts back to its original value, the probability that
    a node will change its node property to the target value, and the number of days over which nodes will
    attempt to change their individual properties to the target value. This node-level intervention functions
    in a similar manner as the individual-level intervention, **PropertyValueChanger**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        target_np_key_value(str, required):
            The **NodeProperty** key:value pair, as defined in the demographics file, to assign to the node.

        revert(float, optional):
            The number of days to keep the value of the property/key, specified in **Target_NP_Key_Value** and
            set by the intervenion, for the node. When the time has expired, the intervention will reset the
            property/key back to the value it had when the intervention was first applied.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        maximum_duration(float, optional):
            The maximum amount of time in days nodes have to update the property value. This timing works in
            conjunction with **Daily_Probability**.
            Minimum value: -1
            Maximum value: 3.40282e+38
            Default value: 3.40282e+38

        daily_probability(float, optional):
            The daily probability that the node's property value changes to the **Target_NP_Key_Value**.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: disqualifying_properties, dont_allow_duplicates, intervention_name, new_property_value.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 target_np_key_value: str,
                 revert: float = 0,
                 maximum_duration: float = 3.40282e+38,
                 daily_probability: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'NodePropertyValueChanger', common_intervention_parameters)

        self._intervention.Target_NP_Key_Value = validate_key_value_pair(target_np_key_value)
        self._intervention.Revert = validate_value_range(revert, 'revert', 0, 3.40282e+38, float)
        self._intervention.Maximum_Duration = validate_value_range(maximum_duration, 'maximum_duration', -1, 3.40282e+38, float)
        self._intervention.Daily_Probability = validate_value_range(daily_probability, 'daily_probability', 0, 1, float)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the NodePropertyValueChanger intervention.')


class Outbreak(NodeIntervention):
    """
    The **Outbreak** class allows the introduction of a disease outbreak event by the addition of new infected
    or susceptible individuals to a node. **Outbreak** is a node-level intervention; to distribute an outbreak
    to specific categories of existing individuals within a node, use **OutbreakIndividual**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        probability_of_infection(float, optional):
            The probability that new individuals are infected. 1.0 implies all new individuals are infected
            while 0.0 adds all of the people as susceptible individuals.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        number_cases_per_node(int, optional):
            The number of new imported individuals.
            .. note:: This will increase the population with demographics of 50/50 male/female and user-defined
            ages
            Minimum value: 0
            Maximum value: 2147480000.0
            Default value: 1

        import_age(float, optional):
            The age (in days) of infected import cases.
            Minimum value: 0
            Maximum value: 43800
            Default value: 365

        genome(int, optional):
            The genetic substrain ID of the outbreak infection. Together with **Antigen**, they are a unitary
            object representing a strain of infection, which allows for differentiation among infections.
            Minimum value: -1
            Maximum value: 16777200.0
            Default value: 0

        antigen(int, optional):
            The antigenic base strain ID of the outbreak infection.
            Minimum value: 0
            Maximum value: 10
            Default value: 0

    """

    def __init__(self,
                 campaign: api_campaign,
                 probability_of_infection: float = 1,
                 number_cases_per_node: int = 1,
                 import_age: float = 365,
                 genome: int = 0,
                 antigen: int = 0):
        super().__init__(campaign, 'Outbreak')

        self._intervention.Probability_Of_Infection = validate_value_range(probability_of_infection, 'probability_of_infection', 0, 1, float)
        self._intervention.Number_Cases_Per_Node = validate_value_range(number_cases_per_node, 'number_cases_per_node', 0, 2147480000.0, int)
        self._intervention.Import_Age = validate_value_range(import_age, 'import_age', 0, 43800, float)
        self._intervention.Genome = validate_value_range(genome, 'genome', -1, 16777200.0, int)
        self._intervention.Antigen = validate_value_range(antigen, 'antigen', 0, 10, int)

    def _set_intervention_name(self, intervention_name: str) -> None:
        raise ValueError('Intervention_Name is not a valid parameter for the Outbreak intervention.')

    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:
        raise ValueError('Dont_Allow_Duplicates is not a valid parameter for the Outbreak intervention.')

    def _set_new_property_value(self, new_property_value: str) -> None:
        raise ValueError('New_Property_Value is not a valid parameter for the Outbreak intervention.')

    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:
        raise ValueError('Disqualifying_Properties is not a valid parameter for the Outbreak intervention.')

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the Outbreak intervention.')
