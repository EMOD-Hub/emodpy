from typing import Union

from emod_api import campaign as api_campaign, schema_to_class as s2c

from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions
from emodpy.campaign.base_intervention import IndividualIntervention, NodeIntervention
from emodpy.campaign.individual_intervention import MultiInterventionDistributor
from emodpy.campaign.node_intervention import MultiNodeInterventionDistributor
from emodpy.campaign.utils import get_trigger_conditions
from emodpy.utils import validate_value_range
from emodpy.utils.distributions import BaseDistribution
from emodpy.utils.emod_enum import ThresholdType, EventType
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
        self._coordinator = s2c.get_class_with_defaults(event_coordinator_class_name, schema_json=campaign.get_schema())

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
            (ReadOnlyDict): StandardEventCoordinator
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


class NodeIdAndCoverage:
    """
    Defines a single (node ID, coverage) pair for use in
    :class:`CoverageByNodeEventCoordinator`. Each entry specifies a node and the fraction
    of its population that should receive the intervention.

    Args:
        node_id (int, required):
            The ID of the node as specified in the demographics file.
            Minimum value: 0.
            Maximum value: 999999.

        coverage (float, required):
            The fraction of individuals in the node that should be randomly selected to
            receive the intervention.
            Minimum value: 0.
            Maximum value: 1.
    """

    def __init__(self, node_id: int, coverage: float):
        self._node_id = validate_value_range(node_id, 'node_id', min_value=0, max_value=999999, param_type=int)
        self._coverage = float(validate_value_range(coverage, 'coverage', min_value=0, max_value=1, param_type=float))

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults("idmType:NodeIdAndCoverage", schema_json=campaign.get_schema())
        obj.Node_Id = self._node_id
        obj.Coverage = self._coverage
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class CoverageByNodeEventCoordinator(InterventionDistributorEventCoordinator):
    """
    The **CoverageByNodeEventCoordinator** distributes individual-level interventions with
    node-specific demographic coverage. It is similar to the
    :class:`StandardEventCoordinator` but allows specifying different coverage fractions
    for each node via the ``coverage_by_node`` parameter. If no coverage is specified for a
    particular node, coverage defaults to zero for that node.

    This coordinator can only be used with individual-level interventions. It supports the
    same demographic targeting, property restrictions, repetition, and targeting config
    options as :class:`StandardEventCoordinator`.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_list (Union[list[IndividualIntervention], list[NodeIntervention]], required):
            A list of either individual-level intervention objects to distribute.

        coverage_by_node (list[tuple[int, float]], required):
            A list of ``(node_id, coverage)`` tuples specifying the demographic coverage
            per node. Each tuple pairs a node ID (matching a node ID in the demographics
            file) with a coverage fraction between 0 and 1. Nodes not listed receive zero
            coverage. Duplicate node IDs are not allowed.

        target_demographics_config (TargetDemographicsConfig, optional):
            Demographic targeting configuration (age, gender, residency).
            Default value: None

        repetition_config (RepetitionConfig, optional):
            Repetition configuration for recurring distributions.
            Default value: None

        property_restrictions (PropertyRestrictions, optional):
            Individual and/or node property restrictions.
            Default value: None

        targeting_config (AbstractTargetingConfig, optional):
            Advanced targeting configuration.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]],
                 coverage_by_node: list[tuple[int, float]],
                 target_demographics_config: TargetDemographicsConfig = None,
                 repetition_config: RepetitionConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None):
        super().__init__(campaign, 'CoverageByNodeEventCoordinator',
                         intervention_list=intervention_list)

        if not coverage_by_node or not isinstance(coverage_by_node, list):
            raise ValueError("coverage_by_node must be a non-empty list of (node_id, coverage) tuples.")
        entries = []
        for item in coverage_by_node:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError(
                    f"Each item in coverage_by_node must be a (node_id, coverage) tuple, got {item!r}.")
            entries.append(NodeIdAndCoverage(node_id=item[0], coverage=item[1]))
        node_ids = [entry._node_id for entry in entries]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate node IDs in coverage_by_node are not allowed.")

        self._coordinator.Coverage_By_Node = [entry.to_schema_dict(campaign) for entry in entries]

        if target_demographics_config is not None:
            if target_demographics_config.demographic_coverage is not None:
                raise ValueError(
                    "demographic_coverage in target_demographics_config cannot be used with "
                    "CoverageByNodeEventCoordinator. Use coverage_by_node to set per-node coverage. "
                    "Set demographic_coverage=None in TargetDemographicsConfig to use other targeting options.")
            target_demographics_config._set_target_demographics(self._coordinator)
        if property_restrictions is not None:
            property_restrictions._set_property_restrictions(self._coordinator)
        if targeting_config is not None:
            self._coordinator.Targeting_Config = targeting_config.to_schema_dict(campaign)
        if repetition_config is not None:
            repetition_config._set_repetitions(self._coordinator)


class CommunityHealthWorkerEventCoordinator(InterventionDistributorEventCoordinator):
    """
    The **CommunityHealthWorkerEventCoordinator** simulates a community health worker (CHW)
    who distributes interventions to individuals or nodes that trigger specified events. When
    a trigger event occurs, the individual or node is added to a queue. The CHW processes the
    queue at a configurable rate, limited by available stock. Stock is replenished periodically
    via shipments.

    Individuals or nodes that have been in the queue longer than the **Waiting_Period** are
    removed. Individuals who die or emigrate are automatically removed from the queue. The
    coordinator expires after **Duration** days.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_list (Union[list[IndividualIntervention],list[NodeIntervention]], required):
            A list of intervention objects to distribute. Can be individual-level or
            node-level, but not both. Demographic restrictions do not apply when distributing
            node-level interventions.

        trigger_condition_list (list[str], required):
            A list of individual-level events that add the triggering individual or node to the
            CHW's queue. Events can be EMOD built-in (e.g., ``"NewInfectionEvent"``,
            ``"NewClinicalCase"``) or your own events used elsewhere in the campaign.

        initial_amount_distribution (BaseDistribution, required):
            The distribution used to determine the initial stock of interventions. Use
            any :class:`~emodpy.utils.distributions.BaseDistribution` subclass, e.g.,
            ``ConstantDistribution(500)`` or
            ``UniformDistribution(100, 1000)``.
            Default value: None

        duration (float, optional):
            The number of days the coordinator remains active before it expires.
            Minimum value: 0.
            Maximum value: 3.40282e+38.
            Default value: None (uses EMOD default: 3.40282e+38).

        max_distributed_per_day (int, required):
            The maximum number of interventions the CHW can distribute per day.
            Minimum value: 1.
            Maximum value: 2147480000.
            Default value: 2147480000.

        waiting_period (float, required):
            The number of days a person or node can remain in the queue. Entities in the
            queue will not be re-added if the trigger event occurs again, preserving their
            priority. Entities are removed from the queue if they exceed this waiting period.
            Minimum value: 0.
            Maximum value: 3.40282e+38.
            Default value: 3.40282e+38.

        days_between_shipments (float, required):
            The number of days between restocking shipments.
            Minimum value: 1.
            Maximum value: 3.40282e+38.
            Default value: 3.40282e+38.

        amount_in_shipment (int, required):
            The number of interventions received in each shipment.
            Minimum value: 0.
            Maximum value: 2147480000.
            Default value: 2147480000.

        max_stock (int, optional):
            The maximum inventory the CHW can hold. Excess stock from shipments is
            discarded.
            Minimum value: 0.
            Maximum value: 2147480000.
            Default value: None (uses EMOD default: 2147480000).

        target_demographics_config (TargetDemographicsConfig, optional):
            Demographic targeting configuration (age, gender, residency, coverage).
            Only applies when distributing individual-level interventions.
            Default value: None

        property_restrictions (PropertyRestrictions, optional):
            Individual and/or node property restrictions.
            Default value: None

        targeting_config (AbstractTargetingConfig, optional):
            Advanced targeting configuration.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: Union[list[IndividualIntervention], list[NodeIntervention]],
                 trigger_condition_list: list[str],
                 initial_amount_distribution: BaseDistribution,
                 max_distributed_per_day: int,
                 waiting_period: float,
                 days_between_shipments: float,
                 amount_in_shipment: int,
                 duration: float = None,
                 max_stock: int = None,
                 target_demographics_config: TargetDemographicsConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None):
        super().__init__(campaign, 'CommunityHealthWorkerEventCoordinator',
                         intervention_list=intervention_list)
        self._coordinator.Trigger_Condition_List = get_trigger_conditions(campaign, trigger_condition_list)

        if duration is not None:
            self._coordinator.Duration = validate_value_range(
                duration, 'duration', min_value=0, max_value=3.40282e+38, param_type=float)
        self._coordinator.Max_Distributed_Per_Day = validate_value_range(
            max_distributed_per_day, 'max_distributed_per_day', min_value=1, max_value=2147480000, param_type=int)
        self._coordinator.Waiting_Period = validate_value_range(
            waiting_period, 'waiting_period', min_value=0, max_value=3.40282e+38, param_type=float)
        self._coordinator.Days_Between_Shipments = validate_value_range(
            days_between_shipments, 'days_between_shipments', min_value=1, max_value=3.40282e+38, param_type=float)
        self._coordinator.Amount_In_Shipment = validate_value_range(
            amount_in_shipment, 'amount_in_shipment', min_value=0, max_value=2147480000, param_type=int)
        if max_stock is not None:
            self._coordinator.Max_Stock = validate_value_range(
                max_stock, 'max_stock', min_value=0, max_value=2147480000, param_type=int)
        if initial_amount_distribution is not None:
            if not isinstance(initial_amount_distribution, BaseDistribution):
                raise ValueError(
                    f"initial_amount_distribution must be a BaseDistribution instance, "
                    f"got {type(initial_amount_distribution).__name__}.")
            initial_amount_distribution.set_intervention_distribution(
                self._coordinator, "Initial_Amount")

        iv_name = self.intervention_list[0].to_schema_dict()['class']
        if isinstance(self.intervention_list[0], IndividualIntervention):
            if target_demographics_config is not None:
                target_demographics_config._set_target_demographics(self._coordinator)
            if property_restrictions is not None:
                property_restrictions._set_property_restrictions(self._coordinator)
            if targeting_config is not None:
                self._coordinator.Targeting_Config = targeting_config.to_schema_dict(campaign)
        else:
            if target_demographics_config is not None or targeting_config is not None:
                raise ValueError(
                    f"The intervention_list contains NodeIntervention: {iv_name}, so "
                    f"target_demographics_config and targeting_config do not apply.")
            if property_restrictions is not None:
                if property_restrictions.individual_property_restrictions:
                    raise ValueError(
                        f"The intervention_list contains NodeIntervention: {iv_name}, so "
                        f"individual_property_restrictions do not apply.")
                property_restrictions._set_property_restrictions(self._coordinator)


class Action:
    """
    Defines a single threshold-action pair for use in a :class:`Responder`. When the incidence
    value (count or percentage) meets or exceeds the **threshold**, the specified event is
    broadcast. If multiple actions are defined, the one with the highest threshold that is still
    less than or equal to the incidence value is selected.

    Args:
        threshold (float, required):
            The threshold value that the incidence count or percentage must meet or exceed for
            this action to be selected. When multiple actions are defined, the action with the
            highest threshold that is still less than or equal to the sampled value is chosen.
            Thresholds must be unique across all actions in the same :class:`Responder`.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        event_to_broadcast (str, required):
            A string that will be broadcast as an event when this action's threshold is met. The level of the event
            broadcast depends on the value of the *event_type* parameter in the same action.

        event_type (Union[EventType, str], required):
            The type of event to broadcast. Use the
            :class:`~emodpy.utils.emod_enum.EventType` enum values:

            * ``EventType.INDIVIDUAL`` -- Broadcast to individuals in the nodes.
            * ``EventType.NODE`` -- Broadcast as a node-level event.
            * ``EventType.COORDINATOR`` -- Broadcast as a coordinator-level event.

    """

    def __init__(self,
                 threshold: float,
                 event_to_broadcast: str,
                 event_type: Union[EventType, str]):
        self._threshold = validate_value_range(
            threshold, 'threshold', min_value=0, max_value=3.40282e+38, param_type=float)
        if not event_to_broadcast or not isinstance(event_to_broadcast, str):
            raise ValueError("event_to_broadcast must be a non-empty string.")
        if not isinstance(event_type, EventType):
            try:
                event_type = EventType(event_type)
            except ValueError:
                raise ValueError(
                    f"event_type must be an EventType enum value, got {event_type!r}. "
                    f"Valid options: {list(EventType)}")
        self._event_to_broadcast = event_to_broadcast
        self._event_type = event_type

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults("idmType:Action", schema_json=campaign.get_schema())
        obj.Threshold = self._threshold
        if self._event_type == EventType.INDIVIDUAL:
            obj.Event_To_Broadcast = campaign.get_send_trigger(self._event_to_broadcast, old=True)
        elif self._event_type == EventType.NODE:
            campaign.set_broadcast_node_event(self._event_to_broadcast)
            obj.Event_To_Broadcast = self._event_to_broadcast
        elif self._event_type == EventType.COORDINATOR:
            campaign.set_broadcast_coordinator_event(self._event_to_broadcast)
            obj.Event_To_Broadcast = self._event_to_broadcast
        obj.Event_Type = self._event_type
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class Responder:
    """
    Defines how the :class:`IncidenceEventCoordinator` responds when the
    :class:`IncidenceCounter` finishes counting. The responder calculates the incidence as a
    raw count or percentage (based on ``threshold_type``), then selects the action from the
    ``action_list`` whose threshold is the highest value that is still less than or equal to
    the calculated incidence. The selected action's event is then broadcast.

    Args:
        action_list (list[Action], required):
            A list of :class:`Action` objects specifying possible responses. Each action defines
            a threshold and an event to broadcast. Actions are evaluated in descending threshold
            order; the action with the highest threshold that does not exceed the incidence
            value is selected. The list must not be empty, and thresholds must be unique.

        threshold_type (Union[ThresholdType, str], optional):
            How to interpret the incidence value and action thresholds. Use the
            :class:`~emodpy.utils.emod_enum.ThresholdType` enum values:

            * ``ThresholdType.COUNT`` -- Raw count of events. The
              **x_Base_Population** configuration parameter can indirectly affect the count
              by changing the population size.
            * ``ThresholdType.PERCENTAGE`` -- The event count divided by the number of
              individuals meeting the demographic restrictions. Note that an individual's
              demographic attributes may change between the time they emit an event and the
              time the denominator is counted.
            * ``ThresholdType.PERCENTAGE_EVENTS`` -- Only supported in
              **SurveillanceEventCoordinator**. Uses a separate list of events
              (**Percentage_Events_To_Count**) for the denominator.

            Default value: ThresholdType.COUNT
    """

    def __init__(self,
                 action_list: list[Action],
                 threshold_type: Union[ThresholdType, str] = ThresholdType.COUNT):
        if not action_list or not isinstance(action_list, list):
            raise ValueError("action_list must be a non-empty list of Action objects.")
        if not all(isinstance(a, Action) for a in action_list):
            raise ValueError("All items in action_list must be Action instances.")
        thresholds = [a._threshold for a in action_list]
        if len(thresholds) != len(set(thresholds)):
            raise ValueError("All thresholds in action_list must be unique.")
        if not isinstance(threshold_type, ThresholdType):
            try:
                threshold_type = ThresholdType(threshold_type)
            except ValueError:
                raise ValueError(
                    f"threshold_type must be a ThresholdType enum value, got {threshold_type!r}. "
                    f"Valid options: {list(ThresholdType)}")
        self._action_list = action_list
        self._threshold_type = threshold_type

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults("idmType:Responder", schema_json=campaign.get_schema())
        obj.Threshold_Type = self._threshold_type
        obj.Action_List = [a.to_schema_dict(campaign) for a in self._action_list]
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class IncidenceCounter:
    """
    Defines what events to count and which individuals qualify for counting in an
    :class:`IncidenceEventCoordinator`. The counter listens for specified individual events
    and counts them over a configurable number of timesteps. Only events from individuals
    matching the demographic and property restrictions are counted.

    Args:
        trigger_condition_list (list[str], required):
            A list of individual-level events to count. When an individual broadcasts one of these
            events and meets the demographic and property restrictions, the counter increments.
            Events can be built-in (e.g., ``"NewClinicalCase"``, ``"NewInfectionEvent"``) or
            custom events broadcast elsewhere in the campaign modules.

        count_events_for_num_timesteps (int, required):
            The number of simulation timesteps over which to count events before notifying
            the responder with the accumulated count.
            Minimum value: 1.
            Maximum value: 2147480000.

        target_demographics_config (TargetDemographicsConfig, optional):
            Demographic targeting configuration that controls which individuals' events
            are counted. Allows filtering by demographic coverage, age, gender, and
            residency status. When not specified, events from all individuals
            (``Target_Demographic: Everyone``) are counted.
            Default value: None

        property_restrictions (PropertyRestrictions, optional):
            Individual and/or node property restrictions that further filter which
            individuals' events are counted. You can specify individual property restrictions,
            node property restrictions, or both (using the appropriate parameter on the
            :class:`~emodpy.campaign.common.PropertyRestrictions` object).
            Default value: None

        targeting_config (AbstractTargetingConfig, optional):
            Advanced targeting configuration for more selective individual filtering using
            the targeting config system.
            Default value: None
    """

    def __init__(self,
                 trigger_condition_list: list[str],
                 count_events_for_num_timesteps: int,
                 target_demographics_config: TargetDemographicsConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None):
        self._trigger_condition_list = trigger_condition_list
        self._count_events_for_num_timesteps = validate_value_range(
            count_events_for_num_timesteps, 'count_events_for_num_timesteps',
            min_value=1, max_value=2147480000, param_type=int)
        self._target_demographics_config = target_demographics_config
        self._property_restrictions = property_restrictions
        self._targeting_config = targeting_config

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults("idmType:IncidenceCounter", schema_json=campaign.get_schema())
        obj.Trigger_Condition_List = get_trigger_conditions(campaign, self._trigger_condition_list)
        obj.Count_Events_For_Num_Timesteps = self._count_events_for_num_timesteps
        if self._target_demographics_config is not None:
            self._target_demographics_config._set_target_demographics(obj)
        if self._property_restrictions is not None:
            self._property_restrictions._set_property_restrictions(obj)
        if self._targeting_config is not None:
            obj.Targeting_Config = self._targeting_config.to_schema_dict(campaign)
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class IncidenceEventCoordinator(BaseEventCoordinator):
    """
    The **IncidenceEventCoordinator** monitors for individual-level events within a
    simulation and responds by broadcasting events when configurable thresholds are met.
    It does not distribute interventions directly; instead, it counts specified events
    using an :class:`IncidenceCounter` and evaluates the accumulated count or percentage
    against thresholds defined in a :class:`Responder`. The responder then broadcasts the
    appropriate event, which can trigger other campaign events or event coordinators.

    This coordinator is useful for implementing reactive strategies, such as deploying
    mass drug administration when disease incidence exceeds a threshold, or broadcasting
    alert events when case counts reach specified levels.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        incidence_counter (IncidenceCounter, required):
            An :class:`IncidenceCounter` defining the events to count and the demographic
            and property restrictions for qualifying individuals. The counter accumulates
            events over the specified number of timesteps before passing the count to the
            responder.

        responder (Responder, required):
            A :class:`Responder` defining the threshold type and the list of threshold-action
            pairs. After the counter finishes counting, the responder calculates the incidence
            value and selects the appropriate action to execute.

        coordinator_name (str, optional):
            The name of the event coordinator. Useful for identification in output reports
            such as ReportCoordinatorEventRecorder.csv and
            ReportSurveillanceEventRecorder.csv. EMOD does not enforce uniqueness.
            Default value: ""

        number_repetitions (int, optional):
            The number of times the count-respond cycle repeats. A value of ``-1`` means
            infinite repetitions. Used with ``timesteps_between_repetitions``.
            Minimum value: -1. Maximum value: 10000. Default value: 1.

        timesteps_between_repetitions (int, optional):
            The number of timesteps (not days) between repetitions. If the
            **Simulation_Timestep** is 30 days and this is set to 4, there will be 120 days
            between repetitions. A value of ``-1`` means the next repetition starts
            immediately after the previous one completes.
            Minimum value: -1. Maximum value: 10000. Default value: -1.
    """

    def __init__(self,
                 campaign: api_campaign,
                 incidence_counter: IncidenceCounter,
                 responder: Responder,
                 coordinator_name: str = "",
                 number_repetitions: int = 1,
                 timesteps_between_repetitions: int = -1):
        super().__init__(campaign, 'IncidenceEventCoordinator')

        if not isinstance(incidence_counter, IncidenceCounter):
            raise ValueError(
                f"incidence_counter must be an IncidenceCounter instance, "
                f"got {type(incidence_counter).__name__}.")
        if not isinstance(responder, Responder):
            raise ValueError(
                f"responder must be a Responder instance, "
                f"got {type(responder).__name__}.")
        number_repetitions = validate_value_range(
            number_repetitions, 'number_repetitions',
            min_value=-1, max_value=10000, param_type=int)
        timesteps_between_repetitions = validate_value_range(
            timesteps_between_repetitions, 'timesteps_between_repetitions',
            min_value=-1, max_value=10000, param_type=int)

        self._coordinator.Incidence_Counter = incidence_counter.to_schema_dict(campaign)
        self._coordinator.Responder = responder.to_schema_dict(campaign)
        if coordinator_name:
            self._coordinator.Coordinator_Name = coordinator_name
        self._coordinator.Number_Repetitions = number_repetitions
        self._coordinator.Timesteps_Between_Repetitions = timesteps_between_repetitions


class IncidenceCounterSurveillance(IncidenceCounter):
    """
    Extends :class:`IncidenceCounter` for use with :class:`SurveillanceEventCoordinator`.
    Adds periodic counting with a configurable counter period and support for counting
    individual, node, or coordinator events.

    Events are counted for ``count_events_for_num_timesteps`` during each period
    (in days) as set by ``counter_period``. At the end of each period, the counter notifies
    the responder with the accumulated data and then starts listening again.

    Args:
        trigger_condition_list (list[str], required):
            The list of events to count. The type of events is determined by
            ``counter_event_type``. Events can be built-in (e.g., ``"NewClinicalCase"``, ``"NewInfectionEvent"``) or
            custom events broadcast by other campaign components.

        counter_event_type (Union[EventType, str], required):
            The type of events counted in ``trigger_condition_list``. Use the
            :class:`~emodpy.utils.emod_enum.EventType` enum values:

            * ``EventType.INDIVIDUAL`` -- Count individual-level events.
            * ``EventType.NODE`` -- Count node-level events.
            * ``EventType.COORDINATOR`` -- Count coordinator-level events.

        counter_period (float, required):
            The counting period in days. At the end of each period, accumulated counts are passed to the
            responder and counting restarts.
            Minimum value: 1.
            Maximum value: 1000.

        count_events_for_num_timesteps (int, required):
            The number of simulation timesteps over which to count events.
            Minimum value: 1.
            Maximum value: 2147480000.

        target_demographics_config (TargetDemographicsConfig, optional):
            Demographic targeting configuration including demographic coverage. See
            :class:`TargetDemographicsConfig` for details. Only applies when counting
            individual-level events.
            Default value: None

        property_restrictions (PropertyRestrictions, optional):
            Individual and/or node property restrictions.
            Default value: None

        targeting_config (AbstractTargetingConfig, optional):
            Advanced targeting configuration. See :class:`AbstractTargetingConfig` for details.
            Default value: None
    """

    def __init__(self,
                 trigger_condition_list: list[str],
                 counter_event_type: Union[EventType, str],
                 counter_period: float,
                 count_events_for_num_timesteps: int,
                 target_demographics_config: TargetDemographicsConfig = None,
                 property_restrictions: PropertyRestrictions = None,
                 targeting_config: AbstractTargetingConfig = None):
        super().__init__(
            trigger_condition_list=trigger_condition_list,
            count_events_for_num_timesteps=count_events_for_num_timesteps,
            target_demographics_config=target_demographics_config,
            property_restrictions=property_restrictions,
            targeting_config=targeting_config)
        counter_period = validate_value_range(
            counter_period, 'counter_period',
            min_value=1, max_value=1000, param_type=float)
        if not isinstance(counter_event_type, EventType):
            try:
                counter_event_type = EventType(counter_event_type)
            except ValueError:
                raise ValueError(
                    f"counter_event_type must be an EventType enum value, got {counter_event_type!r}. "
                    f"Valid options: {list(EventType)}")
        self._counter_period = counter_period
        self._counter_event_type = counter_event_type
        # Currently there only one counter type, so this parameter does not affect behavior,
        # but it is included for future extensibility.
        # self._counter_type = counter_type

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults(
            "idmType:IncidenceCounterSurveillance", schema_json=campaign.get_schema())
        if self._counter_event_type == EventType.INDIVIDUAL:
            obj.Trigger_Condition_List = get_trigger_conditions(campaign, self._trigger_condition_list)
        elif self._counter_event_type == EventType.NODE:
            obj.Trigger_Condition_List = [campaign.set_listened_node_event(t) for t in self._trigger_condition_list]
        elif self._counter_event_type == EventType.COORDINATOR:
            obj.Trigger_Condition_List = [campaign.set_listened_coordinator_event(t) for t in self._trigger_condition_list]
        obj.Count_Events_For_Num_Timesteps = self._count_events_for_num_timesteps
        obj.Counter_Period = self._counter_period
        obj.Counter_Event_Type = self._counter_event_type
        if self._target_demographics_config is not None:
            self._target_demographics_config._set_target_demographics(obj)
        if self._property_restrictions is not None:
            self._property_restrictions._set_property_restrictions(obj)
        if self._targeting_config is not None:
            obj.Targeting_Config = self._targeting_config.to_schema_dict(campaign)
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class ResponderSurveillance(Responder):
    """
    Extends :class:`Responder` for use with :class:`SurveillanceEventCoordinator`.
    Adds support for a responded event (broadcast when any action is taken) and
    percentage-based event counting for the ``ThresholdType.PERCENTAGE_EVENTS``
    threshold type.

    Args:
        action_list (list[Action], required):
            A list of :class:`Action` objects specifying possible responses.

        threshold_type (Union[ThresholdType, str], required):
            How to interpret the incidence value and action thresholds. Use the
            :class:`~emodpy.utils.emod_enum.ThresholdType` enum values:

            * ``ThresholdType.COUNT`` -- Raw count of events. The
              **x_Base_Population** configuration parameter can indirectly affect the count
              by changing the population size.
            * ``ThresholdType.PERCENTAGE`` -- The event count divided by the number of
              individuals meeting the demographic restrictions. Note that an individual's
              demographic attributes may change between the time they emit an event and the
              time the denominator is counted.
            * ``ThresholdType.PERCENTAGE_EVENTS`` -- Only supported in
              **SurveillanceEventCoordinator**. Uses a separate list of events
              (**Percentage_Events_To_Count**) for the denominator.

        responded_event (str, optional):
            A coordinator-level event that is broadcast
            when the responder takes any action. At the end of a counting period, if an action
            is selected, the action events are broadcast first, then the responded event is
            also broadcast. This allows other event coordinators to react to the action.
            Default value: None

        percentage_events_to_count (list[str], optional):
            When ``threshold_type`` is ``ThresholdType.PERCENTAGE_EVENTS``, this lists the
            events counted for the denominator. The numerator comes from the
            ``trigger_condition_list`` in the :class:`IncidenceCounterSurveillance`. The
            event types must match the ``counter_event_type`` of the counter.
            Default value: None

        counter_event_type (Union[EventType, str], optional):
            The type of events in ``percentage_events_to_count``. Required when
            ``threshold_type`` is ``ThresholdType.PERCENTAGE_EVENTS``. Must match the
            ``counter_event_type`` of the associated :class:`IncidenceCounterSurveillance`.
            Default value: None
    """

    def __init__(self,
                 action_list: list[Action],
                 threshold_type: Union[ThresholdType, str] = ThresholdType.COUNT,
                 responded_event: str = None,
                 percentage_events_to_count: list[str] = None,
                 counter_event_type: Union[EventType, str] = None):
        super().__init__(action_list=action_list, threshold_type=threshold_type)
        if (self._threshold_type == ThresholdType.PERCENTAGE_EVENTS
                and not percentage_events_to_count):
            raise ValueError(
                "percentage_events_to_count must be provided when threshold_type "
                "is PERCENTAGE_EVENTS.")
        if percentage_events_to_count and self._threshold_type != ThresholdType.PERCENTAGE_EVENTS:
            raise ValueError(
                "percentage_events_to_count should only be provided when threshold_type "
                "is PERCENTAGE_EVENTS.")
        if counter_event_type is not None and not isinstance(counter_event_type, EventType):
            try:
                counter_event_type = EventType(counter_event_type)
            except ValueError:
                raise ValueError(
                    f"counter_event_type must be an EventType enum value, got {counter_event_type!r}. "
                    f"Valid options: {list(EventType)}")
        if (self._threshold_type == ThresholdType.PERCENTAGE_EVENTS
                and counter_event_type is None):
            raise ValueError(
                "counter_event_type must be provided when threshold_type "
                "is PERCENTAGE_EVENTS.")
        self._responded_event = responded_event
        self._percentage_events_to_count = percentage_events_to_count or None
        self._counter_event_type = counter_event_type

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        obj = s2c.get_class_with_defaults(
            "idmType:ResponderSurveillance", schema_json=campaign.get_schema())
        obj.Threshold_Type = self._threshold_type
        obj.Action_List = [a.to_schema_dict(campaign) for a in self._action_list]
        if self._responded_event:
            obj.Responded_Event = campaign.set_broadcast_coordinator_event(self._responded_event)
        if self._percentage_events_to_count:
            if self._counter_event_type == EventType.INDIVIDUAL:
                obj.Percentage_Events_To_Count = get_trigger_conditions(campaign, self._percentage_events_to_count)
            elif self._counter_event_type == EventType.NODE:
                obj.Percentage_Events_To_Count = [campaign.set_listened_node_event(t) for t in self._percentage_events_to_count]
            elif self._counter_event_type == EventType.COORDINATOR:
                obj.Percentage_Events_To_Count = [campaign.set_listened_coordinator_event(t) for t in self._percentage_events_to_count]
        obj.pop("schema", None)
        obj.pop("explicits", None)
        return obj


class SurveillanceEventCoordinator(BaseEventCoordinator):
    """
    The **SurveillanceEventCoordinator** extends the functionality of
    :class:`IncidenceEventCoordinator` by adding start/stop trigger events, a configurable
    duration, and periodic counting. It monitors for coordinator-level start events, begins
    counting individual/node/coordinator events using an
    :class:`IncidenceCounterSurveillance`, and responds via a
    :class:`ResponderSurveillance` when counting periods complete.

    The coordinator remains dormant until it receives a start trigger event. Once started, it
    counts events during each counter period and passes results to the responder. It can be
    stopped by a stop trigger event and restarted by a subsequent start event. The coordinator
    expires when its duration has elapsed.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        incidence_counter (IncidenceCounterSurveillance, required):
            An :class:`IncidenceCounterSurveillance` defining the events to count, the
            counter period, and demographic restrictions.

        responder (ResponderSurveillance, required):
            A :class:`ResponderSurveillance` defining the threshold type, action list, and
            optional responded event.

        start_trigger_condition_list (list[str], required):
            A list of coordinator events that start the counter. When one of these events is
            heard, the incidence counter begins counting. The list must not be empty. Events
            must be broadcast by other campaign components to be valid triggers.

        stop_trigger_condition_list (list[str], optional):
            A list of coordinator events that stop the counter. The coordinator can restart
            if it receives a new start trigger event. The coordinator does not expire until
            the duration has elapsed.
            Default value: None (the coordinator will not stop until duration elapses)

        coordinator_name (str, optional):
            The name of the event coordinator for identification in output reports.
            Default value: "SurveillanceEventCoordinator"

        duration (float, optional):
            The number of days the coordinator remains active after creation. Once elapsed,
            the coordinator unregisters for events and expires. A value of ``-1`` keeps the
            coordinator running indefinitely.
            Minimum value: -1.
            Maximum value: 3.40282e+38.
            Default value: -1. (run indefinitely)
    """

    def __init__(self,
                 campaign: api_campaign,
                 incidence_counter: IncidenceCounterSurveillance,
                 responder: ResponderSurveillance,
                 start_trigger_condition_list: list[str],
                 stop_trigger_condition_list: list[str] = None,
                 coordinator_name: str = "SurveillanceEventCoordinator",
                 duration: float = -1):
        super().__init__(campaign, 'SurveillanceEventCoordinator')

        if not isinstance(incidence_counter, IncidenceCounterSurveillance):
            raise ValueError(
                f"incidence_counter must be an IncidenceCounterSurveillance instance, "
                f"got {type(incidence_counter).__name__}.")
        if not isinstance(responder, ResponderSurveillance):
            raise ValueError(
                f"responder must be a ResponderSurveillance instance, "
                f"got {type(responder).__name__}.")
        if not start_trigger_condition_list or not isinstance(start_trigger_condition_list, list):
            raise ValueError(
                "start_trigger_condition_list must be a non-empty list of event strings.")
        duration = validate_value_range(
            duration, 'duration',
            min_value=-1, max_value=3.40282e+38, param_type=float)

        self._coordinator.Incidence_Counter = incidence_counter.to_schema_dict(campaign)
        self._coordinator.Responder = responder.to_schema_dict(campaign)
        self._coordinator.Start_Trigger_Condition_List = [campaign.set_listened_coordinator_event(x) for x in start_trigger_condition_list]
        if stop_trigger_condition_list:
            self._coordinator.Stop_Trigger_Condition_List = [campaign.set_listened_coordinator_event(x) for x in stop_trigger_condition_list]
        if coordinator_name:
            self._coordinator.Coordinator_Name = coordinator_name
        self._coordinator.Duration = duration


class BroadcastCoordinatorEvent(BaseEventCoordinator):
    """
    The **BroadcastCoordinatorEvent** coordinator broadcasts a coordinator-level event. It does
    not distribute interventions. Instead, it broadcasts a single coordinator event that other
    coordinators (such as :class:`SurveillanceEventCoordinator`) can listen for and respond to.

    This coordinator is useful for triggering coordinator-level event chains. For example, it
    can be used to start a :class:`SurveillanceEventCoordinator` by broadcasting its start
    trigger event. You can use the **Report_Coordinator_Event_Recorder** to report on the events
    broadcasted by this coordinator.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        broadcast_event (str, required):
            The name of the Coordinator Event to broadcast. This cannot be an empty string.

        coordinator_name (str, optional):
            The name of the event coordinator, which is useful in output reports such as
            ReportCoordinatorEventRecorder.csv and ReportSurveillanceEventRecorder.csv.
            EMOD does not ensure that this name is unique.
            Default value: "BroadcastCoordinatorEvent"

        cost_to_consumer (float, optional):
            The unit cost per each of these event coordinators created.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0
    """

    def __init__(self,
                 campaign: api_campaign,
                 broadcast_event: str,
                 coordinator_name: str = "BroadcastCoordinatorEvent",
                 cost_to_consumer: float = 0):
        super().__init__(campaign, 'BroadcastCoordinatorEvent')

        if not broadcast_event or not isinstance(broadcast_event, str):
            raise ValueError("broadcast_event must be a non-empty string.")

        self._coordinator.Broadcast_Event = campaign.set_broadcast_coordinator_event(broadcast_event)
        if coordinator_name:
            self._coordinator.Coordinator_Name = coordinator_name
        self._coordinator.Cost_To_Consumer = validate_value_range(
            cost_to_consumer, 'cost_to_consumer', min_value=0, max_value=3.40282e+38, param_type=float)
