from emodpy.campaign.common import ValueMap, CommonInterventionParameters
from emodpy.campaign.base_intervention import IndividualIntervention
from emodpy.utils import validate_value_range
from emodpy.campaign.utils import set_event
from emodpy.campaign.waning_config import AbstractWaningConfig
from emodpy.utils.emod_enum import NodeSelectionType, VaccineType, EventOrConfig
from emodpy.utils.distributions import BaseDistribution

from emod_api import campaign as api_campaign
from emod_api import schema_to_class as s2c

from typing import Union


class BroadcastEvent(IndividualIntervention):
    """
    The **BroadcastEvent** intervention class is an individual-level class that immediately broadcasts the event
    trigger you specify. This campaign event is typically used with other classes that monitor for a broadcast
    event.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        broadcast_event(str, required):
            The name of the event to be broadcasted. See
            :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: disqualifying_properties, new_property_value, intervention_name, dont_allow_duplicates.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 broadcast_event: str,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'BroadcastEvent', common_intervention_parameters)

        self._intervention.Broadcast_Event = set_event(broadcast_event, 'broadcast_event', campaign, False)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the BroadcastEvent intervention.')


class BroadcastEventToOtherNodes(IndividualIntervention):
    """
    The **BroadcastEventToOtherNodes** intervention class allows events to be sent from one node to another.
    For example, if an individual in one node has been diagnosed, drugs may be distributed to individuals in
    surrounding nodes.

    When this intervention is updated, the event to be broadcast is cached to be distributed to the nodes.
    After the people have migrated, the event information is distributed to the nodes - **NOTE: it does support
    multi-core**. During the next time step, the nodes will update their node-level interventions and then
    broadcast the events from other nodes to ALL the people in the node. This is different from interventions
    that only broadcast the event in the current node for the person who had the intervention. Distances between
    nodes use the Longitude and Latitude defined in the demographics file, and use the Haversine Formula for
    calculating the great-circle distance.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        broadcast_event(str, required):
            The name of the event to broadcast to the people of 'nearby' nodes. For example, if a house is
            found to have malarai, broadcast an event to the people in the nearby houses so that they can get
            treatment. For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria,
            :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.

        node_selection_type('NodeSelectionType', optional):
            The method by which to select nodes to receive the event. Possible values are:
            * DISTANCE_ONLY - Nodes located within the distance specified by **Max_Distance_To_Other_Nodes_Km**
            are selected.
            * MIGRATION_NODES_ONLY - Nodes that are local, regional, or connected in the migration file are
            selected.
            * DISTANCE_AND_MIGRATION - Nodes are selected using DISTANCE_ONLY and MIGRATION_NODES_ONLY criteria.
            Default value: DISTANCE_ONLY

        max_distance_to_other_nodes_km(float, optional):
            The maximum distance, in kilometers, to the destination node for the node to be selected. The
            location values used are those entered in the demographics file. Used only if
            **Node_Selection_Type** is either DISTANCE_ONLY or DISTANCE_AND_MIGRATION.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 3.40282e+38

        include_my_node(bool, optional):
            Set to True to broadcast the event to the current node.
            Default value: True

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 broadcast_event: str,
                 node_selection_type: 'NodeSelectionType' = NodeSelectionType.DISTANCE_ONLY,
                 max_distance_to_other_nodes_km: float = 3.40282e+38,
                 include_my_node: bool = False,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'BroadcastEventToOtherNodes', common_intervention_parameters)

        self._intervention.Node_Selection_Type = node_selection_type
        if node_selection_type in [NodeSelectionType.DISTANCE_ONLY, NodeSelectionType.DISTANCE_AND_MIGRATION]:
            self._intervention.Max_Distance_To_Other_Nodes_Km = validate_value_range(max_distance_to_other_nodes_km, 'max_distance_to_other_nodes_km', 0, 3.40282e+38, float)
        else:
            if max_distance_to_other_nodes_km != 3.40282e+38:
                raise ValueError(f"max_distance_to_other_nodes_km is used when node_selection_type is set to "
                                 f"DISTANCE_ONLY or DISTANCE_AND_MIGRATION, not {node_selection_type}.")
            self._intervention.pop('Max_Distance_To_Other_Nodes_Km')
        self._intervention.Include_My_Node = include_my_node
        self._intervention.Event_Trigger = set_event(broadcast_event, 'broadcast_event', campaign, False)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the BroadcastEventToOtherNodes intervention.')


class ControlledVaccine(IndividualIntervention):
    """
    The **ControlledVaccine** intervention class is a subclass of **SimpleVaccine** so it contains all
    functionality of **SimpleVaccine**, but provides more control over additional events and event triggers.
    This intervention can be configured so that specific events are broadcast when individuals receive an
    intervention or when the intervention expires. Further, individuals can be re-vaccinated, using a configurable
    wait time between vaccinations.

    Note that one of the controls of this intervention is to not allow a person to receive an additional dose
    if they received a dose within a certain amount of time. This applies only to **ControlledVaccine**
    interventions with the same **Intervention_Name**, so people can be given multiple vaccines as long as
    each vaccine has a different value for **Intervention_Name**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        waning_config(AbstractWaningConfig, required):
            The configuration of the vaccine's efficacy and waning over time. Specify how this effect decays
            over time using one of the Waning Config classes in emodpy.campaign.waninng_config.

        vaccine_type(VaccineType, optional):
            The type of vaccine to distribute in a vaccine intervention. Possible values are:
            * Generic - The vaccine can reduce transmission, acquisition, and mortality.
            * TransmissionBlocking - The vaccine will reduce pathogen transmission.
            * AcquisitionBlocking - The vaccine will reduce the acquisition of the pathogen by reducing the
            force of infection experienced by the vaccinated individual.
            * MortalityBlocking - The vaccine reduces the disease-mortality rate of a vaccinated individual.
            Default value: Generic

        vaccine_take(float, optional):
            The rate at which delivered vaccines will successfully stimulate an immune response and achieve the
            desired efficacy. For example, if it is set to 0.9, there will be a 90 percent chance that the
            vaccine will start with the specified efficacy, and a 10 percent chance that it will have no
            efficacy at all.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        expired_event_trigger(str, optional):
            The name of the event to be broadcast when the intervention expires. See
            :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.
            Default value: None

        efficacy_is_multiplicative(bool, optional):
            The overall vaccine efficacy when individuals receive more than one vaccine. When set to True,
            the vaccine efficacies are multiplied together; when set to False, the efficacies are additive.
            Default value: True

        duration_to_wait_before_revaccination(float, optional):
            The length of time, in days, to wait before revaccinating an individual. After this time has
            passed, the individual can be revaccinated. If the first vaccine has not expired, the individual
            can receive the effect from both doses of the vaccine.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 3.40282e+38

        distributed_event_trigger(str, optional):
            The name of the event to be broadcast when the intervention is distributed to an individual. See
            :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.

            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 waning_config: AbstractWaningConfig,
                 vaccine_type: VaccineType = VaccineType.Generic,
                 vaccine_take: float = 1,
                 expired_event_trigger: str = None,
                 efficacy_is_multiplicative: bool = True,
                 duration_to_wait_before_revaccination: float = 3.40282e+38,
                 distributed_event_trigger: str = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'ControlledVaccine', common_intervention_parameters)
        if not isinstance(waning_config, AbstractWaningConfig):
            raise ValueError(f"waning_config must be an instance of AbstractWaningConfig, not {type(waning_config)}.")
        self._intervention.Waning_Config = waning_config.to_schema_dict(campaign)
        self._intervention.Vaccine_Type = vaccine_type
        self._intervention.Vaccine_Take = validate_value_range(vaccine_take, 'vaccine_take', 0, 1, float)
        self._intervention.Expired_Event_Trigger = set_event(expired_event_trigger, 'expired_event_trigger', campaign, True)
        self._intervention.Efficacy_Is_Multiplicative = efficacy_is_multiplicative
        self._intervention.Duration_To_Wait_Before_Revaccination = validate_value_range(duration_to_wait_before_revaccination, 'duration_to_wait_before_revaccination', 0, 3.40282e+38, float)
        self._intervention.Distributed_Event_Trigger = set_event(distributed_event_trigger, 'distributed_event_trigger', campaign, True)


class DelayedIntervention(IndividualIntervention):
    """
    The **DelayedIntervention** intervention class introduces a delay between when the intervention is
    distributed to the individual and when they receive the actual intervention. This is due to the frequent
    occurrences of time delays as individuals seek care and receive treatment. This intervention allows
    configuration of the distribution type for the delay.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        delay_period_distribution(BaseDistribution, required):
            The distribution type to use for assigning the delay period for distributing interventions. Each
            assigned value is a random draw from the distribution. Please use the following distribution classes
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

        intervention_to_distribute_at_delay_completion(Union[IndividualIntervention, list[IndividualIntervention]], required):
            An Individual Intervention or an array of nested Individual Interventions to be distributed at the end of
            the delay period.
            Either intervention_to_broadcast_at_delay_completion or event_to_broadcast_at_delay_completion must be set.

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 delay_period_distribution: BaseDistribution,
                 intervention_to_distribute_at_delay_completion: Union[IndividualIntervention, list[IndividualIntervention]],
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'DelayedIntervention', common_intervention_parameters)

        # If intervention_to_broadcast_at_delay_completion is an IndividualIntervention, convert it to a schema
        # dict, and set it as the Actual_IndividualIntervention_Configs.
        if isinstance(intervention_to_distribute_at_delay_completion, IndividualIntervention):
            self._intervention.Actual_IndividualIntervention_Configs = [intervention_to_distribute_at_delay_completion.to_schema_dict()]
        # If intervention_to_broadcast_at_delay_completion is a list, convert each element to a schema dict.
        elif isinstance(intervention_to_distribute_at_delay_completion, list):
            # Check that all elements in the list are IndividualIntervention instances.
            if not all(isinstance(intervention, IndividualIntervention) for intervention
                       in intervention_to_distribute_at_delay_completion):
                raise ValueError("All elements in intervention_to_distribute_at_delay_completion must be instances "
                                 "of IndividualIntervention.")
            self._intervention.Actual_IndividualIntervention_Configs = [intervention.to_schema_dict()
                                                                        for intervention
                                                                        in intervention_to_distribute_at_delay_completion]
        else:
            raise ValueError(f"intervention_to_distribute_at_delay_completion must be an instance of "
                             f"IndividualIntervention or a list of IndividualIntervention, "
                             f"not {type(intervention_to_distribute_at_delay_completion)}.")
        self.set_distribution(delay_period_distribution, 'Delay_Period')
        self._intervention.Coverage = 1 # not allowing users to set this because it is a second demographic_coverage

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the DelayedIntervention intervention.')


class IVCalendar(IndividualIntervention):
    """
    The **IVCalendar** intervention class contains a list of ages when an individual will receive the
    actual intervention. In **IVCalendar**, there is a list of actual interventions where the distribution
    is dependent on whether the individual's age matches the next date in the calendar. This implies that
    at a certain age, the list of actual interventions will be distributed according to a given probability.
    While a typical use case might involve the distribution of calendars due to a **Births** event in the
    context of a routine vaccination schedule, calendars may also be distributed directly to individuals at
    at times other than birth.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_list(list[IndividualIntervention], required):
            An array of interventions that will be distributed as specified by the calendar. Each time the
            calendar says it is time for the intervention, this list of interventions will be distributed
            to the person with this intervention.

        dropout(bool, optional):
            If set to true, when an intervention distribution is missed, all subsequent interventions are
            also missed. If set to false, all calendar dates/doses are applied independently of each other.
            Default value: True

        calendar(list['AgeAndProbability'], optional):
            An array of JSON objects where each object specifies the age and probability of receiving the
            interventions.  The parameters of the Calendar objects are Age and Probability.
            Default value: None

        common_intervention_parameters (CommonInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 4 common
            parameters: intervention_name, new_property_value, disqualifying_properties, dont_allow_duplicates.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: list[IndividualIntervention],
                 dropout: bool = False,
                 calendar: list['AgeAndProbability'] = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'IVCalendar', common_intervention_parameters)

        schema_intervention_list = []
        for iv in intervention_list:
            if not isinstance(iv, IndividualIntervention):
                msg =   "Each element in 'intervention_list' must be an "     # Noqa: E222
                msg += f"instance of IndividualIntervention, not {type(iv)}."
                raise ValueError(msg)
            schema_intervention_list.append(iv.to_schema_dict())
        self._intervention.Actual_IndividualIntervention_Configs = schema_intervention_list
        self._intervention.Dropout = dropout
        if calendar is not None:
            self._intervention.Calendar = [aap.to_schema_dict(campaign) for aap in calendar]

    def _set_cost(self, cost: float) -> None:
        raise ValueError("Cost_To_Consumer is not a valid parameter for the 'IVCalendar' intervention.")

    class AgeAndProbability:
        """
        This class defines a single entry into the calendar of when an individual is to get a
        collection of interventions.  When **IVCalendar** is distributed to the individual, the
        'probability' is used to determine if the person will get the interventions as this age.
        If the person gets **IVCalendar** after 'age', they will not get the interventions.

        Args:
            age_days(float,optional):
                As a parameter of a Calendar object, this parameter determines the age (in days) that the
                individual must be in order to receive the list of actual interventions.
                Minimum value: 0
                Maximum value: 125 * 365 = 45,625
                Default value: 0

            probability(float,optional):
                As a parameter of a Calendar object, this parameter determines the probability of an
                individual receiving the list of actual interventions at the corresponding age.
                Minimum value: 0
                Maximum value: 1
                Default value: 1
        """
        def __init__(self,
                     age_days: float = 0.0,
                     probability: float = 1.0):
            self.age_days = validate_value_range(age_days, 'age_days', 0.0, (125.0 * 365.0), float)
            self.probability = validate_value_range(probability, 'probability', 0.0, 1.0, float)

        def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
            """
            A function that converts the Sigmoid object to a schema dictionary.
            """
            aap = s2c.get_class_with_defaults("idmType:AgeAndProbability", schema_json=campaign.get_schema())
            aap.Age = self.age_days
            aap.Probability = self.probability
            aap.finalize()
            return aap


class _ImmunityBloodTest(IndividualIntervention):  # make this class private until we have time to review and test it.
    """
    The **ImmunityBloodTest** intervention class identifies whether an individual's immunity meets a specified
    threshold (as set with the **positive_threshold_acquisition_immunity** campaign parameter) and then broadcasts
    an event based on the results; positive has immunity while negative does not. Note that **base_sensitivity**
    and **base_specificity** function whether or not the immunity is above the threshold.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        positive_diagnosis_event(str, required):
            If the test has a positive diagnosis, this parameter defines the event to be broadcast to potentially
            trigger separate interventions or events. For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`,
            and for malaria, :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or
            use your own custom event.

        treatment_fraction(float, optional):
            The fraction of positive diagnoses that have the positive_diagnosis_event sent out to trigger separate
            interventions or events.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        positive_threshold_acquisition_immunity(float, optional):
            Specifies the threshold for acquired immunity, where 1 equals 100% immunity and 0 equals 100%
            susceptible.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        negative_diagnosis_event(str, optional):
            If the test has a negative diagnosis, this parameter defines the event to be broadcast to potentially
            trigger separate interventions or events. For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`,
            and for malaria, :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or
            use your own custom event. If not set, no event will be sent out upon negative diagnosis.

            Default value: None

        enable_is_symptomatic(bool, optional):
            If True, requires an infection to be symptomatic to return a positive test.
            Default value: True

        days_to_diagnosis(float, optional):
            The number of days from the test, which is done when the intervention is distributed, until the
            positive_diagnosis_event is sent out if test had a positive diagnosis. The negative_diagnosis_event is sent
            out immediately if the test is negative.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        base_specificity(float, optional):
            The specificity of the diagnostic. This sets the proportion of the time that individuals without
            the condition being tested receive a negative diagnostic test. When set to 1, the diagnostic always
            accurately reflects the lack of having the condition. When set to zero, then individuals who do not
            have the condition always receive a false-positive diagnostic test.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        base_sensitivity(float, optional):
            The sensitivity of the diagnostic. This sets the proportion of the time that individuals with the
            condition being tested receive a positive diagnostic test. When set to 1, the diagnostic always
            accurately reflects the condition. When set to zero, then individuals who have the condition always
            receive a false-negative diagnostic test.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommonInterventionParameters, optional):
            The CommonInterventionParameters object that contains the 5 common
            parameters: cost, intervention_name, new_property_value, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 positive_diagnosis_event: str,
                 treatment_fraction: float = 1,
                 positive_threshold_acquisition_immunity: float = 1,
                 negative_diagnosis_event: str = None,
                 enable_is_symptomatic: bool = False,
                 days_to_diagnosis: float = 0,
                 base_specificity: float = 1,
                 base_sensitivity: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'ImmunityBloodTest', common_intervention_parameters)

        self._intervention.Treatment_Fraction = validate_value_range(treatment_fraction, 'treatment_fraction', 0, 1, float)
        self._intervention.Positive_Threshold_Acquisition_Immunity = validate_value_range(positive_threshold_acquisition_immunity, 'positive_threshold_acquisition_immunity', 0, 1, float)
        self._intervention.Positive_Diagnosis_Event = set_event(positive_diagnosis_event, 'positive_diagnosis_event', campaign, False)
        self._intervention.Negative_Diagnosis_Event = set_event(negative_diagnosis_event, 'negative_diagnosis_event', campaign, True)
        self._intervention.Enable_Is_Symptomatic = enable_is_symptomatic
        self._intervention.Days_To_Diagnosis = validate_value_range(days_to_diagnosis, 'days_to_diagnosis', 0, 3.40282e+38, float)
        self._intervention.Base_Specificity = validate_value_range(base_specificity, 'base_specificity', 0, 1, float)
        self._intervention.Base_Sensitivity = validate_value_range(base_sensitivity, 'base_sensitivity', 0, 1, float)


class IndividualImmunityChanger(IndividualIntervention):
    """
    The **IndividualImmunityChanger** intervention class acts essentially as a **MultiEffectVaccine**,
    with the exception of how the behavior is implemented. Rather than attaching a persistent vaccine
    intervention object to an individual's intervention list (as a campaign-individual-multieffectboostervaccine
    does), the **IndividualImmunityChanger** directly alters the immune modifiers of the individual's
    susceptibility object and is then immediately disposed of. Any immune waning is not governed by
    Waning effect classes, as **MultiEffectVaccine** is, but rather by the immunity waning parameters
    in the configuration file.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        prime_transmit(float, optional):
            Specifies the priming effect on transmission immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        prime_mortality(float, optional):
            Specifies the priming effect on mortality immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        prime_acquire(float, optional):
            Specifies the priming effect on acquisition immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_transmit(float, optional):
            Specifies the boosting effect on transmission immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_transmit(float, optional):
            Specifies how much transmission immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_mortality(float, optional):
            Specifies how much mortality immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_acquire(float, optional):
            Specifies how much acquisition immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_mortality(float, optional):
            Specifies the boosting effect on mortality immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_acquire(float, optional):
            Specifies the boosting effect on acquisition immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 1 common
            parameters: cost.
            The following parameters are not valid for this intervention:
            intervention_name
            dont_allow_duplicates
            new_property_value
            disqualifying_properties
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 prime_transmit: float = 0,
                 prime_mortality: float = 0,
                 prime_acquire: float = 0,
                 boost_transmit: float = 0,
                 boost_threshold_transmit: float = 0,
                 boost_threshold_mortality: float = 0,
                 boost_threshold_acquire: float = 0,
                 boost_mortality: float = 0,
                 boost_acquire: float = 0,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'IndividualImmunityChanger', common_intervention_parameters)

        self._intervention.Prime_Transmit = validate_value_range(prime_transmit, 'prime_transmit', 0, 1, float)
        self._intervention.Prime_Mortality = validate_value_range(prime_mortality, 'prime_mortality', 0, 1, float)
        self._intervention.Prime_Acquire = validate_value_range(prime_acquire, 'prime_acquire', 0, 1, float)
        self._intervention.Boost_Transmit = validate_value_range(boost_transmit, 'boost_transmit', 0, 1, float)
        self._intervention.Boost_Threshold_Transmit = validate_value_range(boost_threshold_transmit, 'boost_threshold_transmit', 0, 1, float)
        self._intervention.Boost_Threshold_Mortality = validate_value_range(boost_threshold_mortality, 'boost_threshold_mortality', 0, 1, float)
        self._intervention.Boost_Threshold_Acquire = validate_value_range(boost_threshold_acquire, 'boost_threshold_acquire', 0, 1, float)
        self._intervention.Boost_Mortality = validate_value_range(boost_mortality, 'boost_mortality', 0, 1, float)
        self._intervention.Boost_Acquire = validate_value_range(boost_acquire, 'boost_acquire', 0, 1, float)

    def _set_intervention_name(self, intervention_name: str) -> None:
        raise ValueError('Intervention_Name is not a valid parameter for the IndividualImmunityChanger intervention.')

    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:
        raise ValueError('Dont_Allow_Duplicates is not a valid parameter for the IndividualImmunityChanger intervention.')

    def _set_new_property_value(self, new_property_value: str) -> None:
        raise ValueError('New_Property_Value is not a valid parameter for the IndividualImmunityChanger intervention.')

    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:
        raise ValueError('Disqualifying_Properties is not a valid parameter for the IndividualImmunityChanger intervention.')


class IndividualNonDiseaseDeathRateModifier(IndividualIntervention):
    """
    The **IndividualNonDiseaseDeathRateModifier** intervention class provides a method of modifying an
    individual's non-disease mortality rate over time, until an expiration event is reached. For example,
    this intervention could be given to people who have access to health care to model that they have a
    different life expectancy than those who do not. Different distribution patterns can be designated,
    and linear interpolation will be used to calculate values between time points.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        duration_to_modifier(ValueMap, required):
            An array of Times and Values used to specify different modifiers over the duration of the
            intervention. Linear interpolation is used to find the values between time points. If the duration
            exceeds the max time, then the last modifier value will be used.

        expiration_event(str, optional):
            When the person stops using the intervention (intervetion expires), this event will be broadcasted. See
            :doc:`emod-hiv:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.
            Default value: None

        expiration_duration_distribution(BaseDistribution, optional):
            For the distribution of each intervention, a randomly selected duration from this distribution will
            determine when the person stops using the intervention. This is independent of how long the
            intervention is effective. Please use the following distribution classes
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
            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 duration_to_modifier: ValueMap,
                 expiration_event: str = None,
                 expiration_duration_distribution: BaseDistribution = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'IndividualNonDiseaseDeathRateModifier', common_intervention_parameters)

        self._intervention.Duration_To_Modifier = duration_to_modifier.to_schema_dict(campaign)
        self._intervention.Expiration_Event = set_event(expiration_event, 'expiration_event', campaign, True)
        if expiration_duration_distribution:
            self.set_distribution(expiration_duration_distribution, 'Expiration_Duration')


class MigrateIndividuals(IndividualIntervention):
    """
    The **MigrateIndividuals** intervention class is an individual-level intervention used to force migration
    and is separate from the normal migration system. However, it does require that human migration is enabled
    by setting the configuration parameters **Migration_Model** to **FIXED_RATE_MIGRATION** and
    **Migration_Pattern** to **SINGLE_ROUND_TRIP**.

    As individuals migrate, there are three ways to categorize nodes:

        - `Home`: the node where the individuals reside; each individual has a single home node.
        - `Origin`: the "starting point" node for each leg of the migration. The origin updates
          as individuals move between nodes.
        - `Destination`: the node the individual is traveling to. The destination updates as
          individuals move between nodes.

    For example, Individual 1 has a home node of Node A. They migrate from Node A to Node B.
    Node A is both the home node and the origin node, and Node B is the destination node.
    If Individual 1 migrates from Node B to Node C, Node A remains the home node, but now
    Node B is the origin node, and Node C is the destination node. If Individual 1 migrates
    from Node C back to Node A, Node C is the origin node, and Node A becomes the destination
    node and still remains the home node.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        nodeid_to_migrate_to(int, optional):
            The destination node ID for intervention-based migration.
            Minimum value: 0
            Maximum value: 4294970000.0
            Default value: 0

        is_moving(bool, optional):
            Set to True to indicate the individual is permanently moving to a new home node for
            intervention-based migration. Once at the new home node, trips will be made with this node as the
            root (i.e. round trips come back to this node).
            Default value: True

        duration_before_leaving_distribution(BaseDistribution, optional):
            The distribution type to use for assigning the duration of time an individual waits before
            migrating to the destination node after intervention-based migration. Each assigned value is a
            random draw from the distribution. Please use the following distribution classes
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
            Default value: None

        duration_at_node_distribution(BaseDistribution, optional):
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
            Default value: None

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 nodeid_to_migrate_to: int = 0,
                 is_moving: bool = False,
                 duration_before_leaving_distribution: BaseDistribution = None,
                 duration_at_node_distribution: BaseDistribution = None,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MigrateIndividuals', common_intervention_parameters)

        self._intervention.NodeID_To_Migrate_To = validate_value_range(nodeid_to_migrate_to, 'nodeid_to_migrate_to', 0, 4294970000.0, int)
        self._intervention.Is_Moving = is_moving
        if duration_before_leaving_distribution:
            self.set_distribution(duration_before_leaving_distribution, 'Duration_Before_Leaving')
        if duration_at_node_distribution:
            self.set_distribution(duration_at_node_distribution, 'Duration_At_Node')

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the MigrateIndividuals intervention.')


class MultiEffectBoosterVaccine(IndividualIntervention):
    """
    The **MultiEffectBoosterVaccine** intervention class is derived from **MultiEffectVaccine** and preserves
    many of the same parameters. Upon distribution and successful take, the vaccine's effect in each immunity
    compartment (acquisition, transmission, and mortality) is determined by the recipient's immune state.
    If the recipient's immunity modifier in the corresponding compartment is above a user-specified threshold,
    then the vaccine's initial effect will be equal to the corresponding priming parameter. If the recipient's
    immune modifier is below this threshold, then the vaccine's initial effect will be equal to the corresponding
    boost parameter. After distribution, the effect wanes, just like a **MultiEffectVaccine**. The behavior is
    intended to mimic biological priming and boosting.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        transmit_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine transmission. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        mortality_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine mortality. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        acquire_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine acquisition. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        vaccine_take(float, optional):
            The rate at which delivered vaccines will successfully stimulate an immune response and achieve the
            desired efficacy. For example, if it is set to 0.9, there will be a 90 percent chance that the
            vaccine will start with the specified efficacy, and a 10 percent chance that it will have no
            efficacy at all.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        prime_transmit(float, optional):
            Specifies the priming effect on transmission immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        prime_mortality(float, optional):
            Specifies the priming effect on mortality immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        prime_acquire(float, optional):
            Specifies the priming effect on acquisition immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_transmit(float, optional):
            Specifies the boosting effect on transmission immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_transmit(float, optional):
            Specifies how much transmission immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_mortality(float, optional):
            Specifies how much mortality immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_threshold_acquire(float, optional):
            Specifies how much acquisition immunity is required before the vaccine changes from a prime to a
            boost.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_mortality(float, optional):
            Specifies the boosting effect on mortality immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_acquire(float, optional):
            Specifies the boosting effect on acquisition immunity for naive individuals (without natural or
            vaccine-derived immunity) for a multi-effect booster vaccine. This does not replace current
            immunity, it builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 transmit_config: AbstractWaningConfig,
                 mortality_config: AbstractWaningConfig,
                 acquire_config: AbstractWaningConfig,
                 vaccine_take: float = 1,
                 prime_transmit: float = 0,
                 prime_mortality: float = 0,
                 prime_acquire: float = 0,
                 boost_transmit: float = 0,
                 boost_threshold_transmit: float = 0,
                 boost_threshold_mortality: float = 0,
                 boost_threshold_acquire: float = 0,
                 boost_mortality: float = 0,
                 boost_acquire: float = 0,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MultiEffectBoosterVaccine', common_intervention_parameters)
        if not isinstance(transmit_config, AbstractWaningConfig):
            raise ValueError(f"transmit_config must be an instance of AbstractWaningConfig, not {type(transmit_config)}.")
        if not isinstance(mortality_config, AbstractWaningConfig):
            raise ValueError(f"mortality_config must be an instance of AbstractWaningConfig, not {type(mortality_config)}.")
        if not isinstance(acquire_config, AbstractWaningConfig):
            raise ValueError(f"acquire_config must be an instance of AbstractWaningConfig, not {type(acquire_config)}.")

        self._intervention.Transmit_Config = transmit_config.to_schema_dict(campaign)
        self._intervention.Mortality_Config = mortality_config.to_schema_dict(campaign)
        self._intervention.Acquire_Config = acquire_config.to_schema_dict(campaign)
        self._intervention.Vaccine_Take = validate_value_range(vaccine_take, 'vaccine_take', 0, 1, float)
        self._intervention.Prime_Transmit = validate_value_range(prime_transmit, 'prime_transmit', 0, 1, float)
        self._intervention.Prime_Mortality = validate_value_range(prime_mortality, 'prime_mortality', 0, 1, float)
        self._intervention.Prime_Acquire = validate_value_range(prime_acquire, 'prime_acquire', 0, 1, float)
        self._intervention.Boost_Transmit = validate_value_range(boost_transmit, 'boost_transmit', 0, 1, float)
        self._intervention.Boost_Threshold_Transmit = validate_value_range(boost_threshold_transmit, 'boost_threshold_transmit', 0, 1, float)
        self._intervention.Boost_Threshold_Mortality = validate_value_range(boost_threshold_mortality, 'boost_threshold_mortality', 0, 1, float)
        self._intervention.Boost_Threshold_Acquire = validate_value_range(boost_threshold_acquire, 'boost_threshold_acquire', 0, 1, float)
        self._intervention.Boost_Mortality = validate_value_range(boost_mortality, 'boost_mortality', 0, 1, float)
        self._intervention.Boost_Acquire = validate_value_range(boost_acquire, 'boost_acquire', 0, 1, float)


class MultiEffectVaccine(IndividualIntervention):
    """
    The **MultiEffectVaccine** intervention class implements vaccine campaigns in the simulation.
    Vaccines can effect all of the following:

        - Reduce the likelihood of acquiring an infection
        - Reduce the likelihood of transmitting an infection
        - Reduce the likelihood of death

    After distribution, the effect wanes over time.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        transmit_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine transmission. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        mortality_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine mortality. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        acquire_config(AbstractWaningConfig, required):
            The configuration for multi-effect vaccine acquisition. Specify how this effect decays over time
            using one of the Waning Config classes in emodpy.campaign.waninng_config.

        vaccine_take(float, optional):
            The rate at which delivered vaccines will successfully stimulate an immune response and achieve the
            desired efficacy. For example, if it is set to 0.9, there will be a 90 percent chance that the
            vaccine will start with the specified efficacy, and a 10 percent chance that it will have no
            efficacy at all.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 transmit_config: AbstractWaningConfig,
                 mortality_config: AbstractWaningConfig,
                 acquire_config: AbstractWaningConfig,
                 vaccine_take: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MultiEffectVaccine', common_intervention_parameters)
        if not isinstance(transmit_config, AbstractWaningConfig):
            raise ValueError(f"transmit_config must be an instance of AbstractWaningConfig, not {type(transmit_config)}.")
        if not isinstance(mortality_config, AbstractWaningConfig):
            raise ValueError(f"mortality_config must be an instance of AbstractWaningConfig, not {type(mortality_config)}.")
        if not isinstance(acquire_config, AbstractWaningConfig):
            raise ValueError(f"acquire_config must be an instance of AbstractWaningConfig, not {type(acquire_config)}.")

        self._intervention.Transmit_Config = transmit_config.to_schema_dict(campaign)
        self._intervention.Mortality_Config = mortality_config.to_schema_dict(campaign)
        self._intervention.Acquire_Config = acquire_config.to_schema_dict(campaign)
        self._intervention.Vaccine_Take = validate_value_range(vaccine_take, 'vaccine_take', 0, 1, float)


class MultiInterventionDistributor(IndividualIntervention):
    """
    The **MultiInterventionDistributor** intervention class allows you to input a list of interventions,
    rather than just a single intervention, to be distributed simultaneously to the same individuals.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_list(list[IndividualIntervention], required):
            The list of individual interventions that is distributed by **MultiInterventionDistributor**.

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_list: list[IndividualIntervention],
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'MultiInterventionDistributor', common_intervention_parameters)

        self._intervention.Intervention_List = [i.to_schema_dict() for i in intervention_list]

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the MultiInterventionDistributor intervention.')


class OutbreakIndividual(IndividualIntervention):
    """
    The **OutbreakIndividual** intervention class introduces contagious diseases that are compatible with the
    simulation type to existing individuals using the individual targeted features configured in the appropriate
    event coordinator. To instead add new infection individuals, use **Outbreak**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        incubation_period_override(int, optional):
            The incubation period, in days, that infected individuals will go through before becoming
            infectious. This value overrides the incubation period set in the configuration file. Note for HIV
            simulations only: If set to 0, infection is assumed to be part of an outbreak event and a random
            duration until death is determined. For all other simulation types: Set to -1 to honor the
            configuration parameter settings.
            Minimum value: -1
            Maximum value: 2147480000.0
            Default value: -1

        ignore_immunity(bool, optional):
            Individuals will be force-infected (with a specific strain) regardless of actual immunity level
            when set to True.
            Default value: True

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
                 incubation_period_override: int = -1,
                 ignore_immunity: bool = True,
                 genome: int = 0,
                 antigen: int = 0):
        super().__init__(campaign, 'OutbreakIndividual')

        self._intervention.Incubation_Period_Override = validate_value_range(incubation_period_override, 'incubation_period_override', -1, 2147480000.0, int)
        self._intervention.Ignore_Immunity = ignore_immunity
        self._intervention.Genome = validate_value_range(genome, 'genome', -1, 16777200.0, int)
        if antigen is not None:  # antigen is not in Generic model, workaround for generic simulation
            self._intervention.Antigen = validate_value_range(antigen, 'antigen', 0, 10, int)

    def _set_intervention_name(self, intervention_name: str) -> None:
        raise ValueError('Intervention_Name is not a valid parameter for the OutbreakIndividual intervention.')

    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:
        raise ValueError('Dont_Allow_Duplicates is not a valid parameter for the OutbreakIndividual intervention.')

    def _set_new_property_value(self, new_property_value: str) -> None:
        raise ValueError('New_Property_Value is not a valid parameter for the OutbreakIndividual intervention.')

    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:
        raise ValueError('Disqualifying_Properties is not a valid parameter for the OutbreakIndividual intervention.')

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the OutbreakIndividual intervention.')


class PropertyValueChanger(IndividualIntervention):
    """
    The **PropertyValueChanger** intervention class assigns new individual property values to individuals
    You must update one property value and have the option to update another using **New_Property_Value**.
    This parameter is generally used to move patients from one intervention state in the health care cascade
    (InterventionStatus/CascadeState) to another, though it can be used for any individual property.
    Individual property values are user-defined in the demographics file (see **NodeProperties** and
    **IndividualProperties** for more information). Note that the HINT feature does not need to be enabled
    to use this intervention. To instead change node properties, use **NodePropertyValueChanger**.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        target_property_value(str, required):
            The user-defined value of the individual property that will be assigned to the individual.

        target_property_key(str, required):
            The name of the individual property type whose value will be updated by the intervention.

        revert(float, optional):
            The number of days to keep the value (**Target_Property_Value**) of the property
            (**Target_Property_Key**) set by the intervenion for the individual. When the time has expired, the
            intervention will reset the property back to the value it had when the intervention was first
            applied.
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        maximum_duration(float, optional):
            The maximum amount of time individuals have to move to a new group. This timing works in
            conjunction with **Daily_Probability**.
            Minimum value: -1
            Maximum value: 3.40282e+38
            Default value: 3.40282e+38

        daily_probability(float, optional):
            The daily probability that an individual's property value changes to the **Target_Property_Value**.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 target_property_value: str,
                 target_property_key: str,
                 revert: float = 0,
                 maximum_duration: float = 3.40282e+38,
                 daily_probability: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'PropertyValueChanger', common_intervention_parameters)

        self._intervention.Target_Property_Value = target_property_value
        self._intervention.Target_Property_Key = target_property_key
        self._intervention.Revert = validate_value_range(revert, 'revert', 0, 3.40282e+38, float)
        self._intervention.Maximum_Duration = validate_value_range(maximum_duration, 'maximum_duration', -1, 3.40282e+38, float)
        self._intervention.Daily_Probability = validate_value_range(daily_probability, 'daily_probability', 0, 1, float)

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the PropertyValueChanger intervention.')


class SimpleBoosterVaccine(IndividualIntervention):
    """
    The **SimpleBoosterVaccine** intervention class is derived from **SimpleVaccine** and preserves many of the
    same parameters. The behavior is much like **SimpleVaccine**, except that upon distribution and successful
    take, the vaccine's effect is determined by the recipient's immune state. If the recipient’s immunity
    modifier in the corresponding channel (acquisition, transmission, or mortality) is above a user-specified
    threshold, then the vaccine's initial effect will be equal to the corresponding priming parameter. If the
    recipient's immune modifier is below this threshold, then the vaccine's initial effect will be equal to the
    corresponding boosting parameter. After distribution, the effect wanes, just like **SimpleVaccine**.
    In essence, this intervention provides a SimpleVaccine intervention with one effect to all naive
    (below- threshold) individuals, and another effect to all primed (above-threshold) individuals;
    this behavior is intended to mimic biological priming and boosting.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        waning_config(AbstractWaningConfig, required):
            The configuration of the vaccine's efficacy and waning over time. Specify how this effect decays
            over time using one of the Waning Config classes in emodpy.campaign.waninng_config.

        vaccine_type(VaccineType, optional):
            The type of vaccine to distribute in a vaccine intervention. Possible values are:
            * Generic - The vaccine can reduce transmission, acquisition, and mortality.
            * TransmissionBlocking - The vaccine will reduce pathogen transmission.
            * AcquisitionBlocking - The vaccine will reduce the acquisition of the pathogen by reducing the
            force of infection experienced by the vaccinated individual.
            * MortalityBlocking - The vaccine reduces the disease-mortality rate of a vaccinated individual.
            Default value: Generic

        vaccine_take(float, optional):
            The rate at which delivered vaccines will successfully stimulate an immune response and achieve the
            desired efficacy. For example, if it is set to 0.9, there will be a 90 percent chance that the
            vaccine will start with the specified efficacy, and a 10 percent chance that it will have no
            efficacy at all.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        prime_effect(float, optional):
            Specifies the priming effect on [acquisition/transmission/mortality] immunity for naive individuals
            (without natural or vaccine-derived immunity).
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        efficacy_is_multiplicative(bool, optional):
            The overall vaccine efficacy when individuals receive more than one vaccine. When set to True,
            the vaccine efficacies are multiplied together; when set to False, the efficacies are additive.
            Default value: True

        boost_threshold(float, optional):
            Specifies how much immunity is required before the vaccine changes from a priming effect to a
            boosting effect.
            Minimum value: 0
            Maximum value: 1
            Default value: 0

        boost_effect(float, optional):
            Specifies the boosting effect on [acquisition/transmission/mortality] immunity for previously
            exposed individuals (either natural or vaccine-derived). This does not replace current immunity, it
            builds multiplicatively on top of it.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 waning_config: AbstractWaningConfig,
                 vaccine_type: VaccineType = VaccineType.Generic,
                 vaccine_take: float = 1,
                 prime_effect: float = 1,
                 efficacy_is_multiplicative: bool = True,
                 boost_threshold: float = 0,
                 boost_effect: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'SimpleBoosterVaccine', common_intervention_parameters)
        if not isinstance(waning_config, AbstractWaningConfig):
            raise ValueError(f"waning_config must be an instance of AbstractWaningConfig, not {type(waning_config)}.")

        self._intervention.Waning_Config = waning_config.to_schema_dict(campaign)
        self._intervention.Vaccine_Type = vaccine_type
        self._intervention.Vaccine_Take = validate_value_range(vaccine_take, 'vaccine_take', 0, 1, float)
        self._intervention.Prime_Effect = validate_value_range(prime_effect, 'prime_effect', 0, 1, float)
        self._intervention.Efficacy_Is_Multiplicative = efficacy_is_multiplicative
        self._intervention.Boost_Threshold = validate_value_range(boost_threshold, 'boost_threshold', 0, 1, float)
        self._intervention.Boost_Effect = validate_value_range(boost_effect, 'boost_effect', 0, 1, float)


# DanB - Making SimpleDiagnostic private because users should use StandardDiagnostic instead.  It is the same thing
# but adds the negative diagnosis.

class _SimpleDiagnostic(IndividualIntervention):
    """
    The **SimpleDiagnostic** intervention class identifies infected individuals, regardless of disease state,
    based on specified diagnostic sensitivity and specificity. Diagnostics are a key component of modern disease
    control efforts, whether used to identify high-risk individuals, infected individuals, or drug resistance.
    This intervention class distributes a specified intervention to a fraction of individuals who test positive.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        positive_diagnosis_config(IndividualIntervention, optional):
            The intervention distributed to individuals if they test positive. Must be defined if not using
            postive_diagnosis_event. Cannot have both positive_diagnosis_config and positive_diagnosis_event.
            Default value: None

        positive_diagnosis_event(str, optional):
            If the test is positive, this specifies an event that can trigger another intervention when the event occurs.
            Must be defined if not using positive_diagnosis_config. Cannot have both positive_diagnosis_config and
            positive_diagnosis_event. For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria,
            :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own custom event.
            Default value: None

        treatment_fraction(float, optional):
            The fraction of positive diagnoses that are given the positive_diagnosis_config or
            positive_diagnosis_event, whichever is defined.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        enable_is_symptomatic(bool, optional):
            If True, requires an infection to be symptomatic to return a positive test.
            Default value: True

        days_to_diagnosis(float, optional):
            The number of days from diagnosis (which is done when the intervention is distributed) until a
            positive response is performed. The response to a negative diagnosis is done immediately when the
            diagnosis is made (at distribution of the intervention).
            Minimum value: 0
            Maximum value: 3.40282e+38
            Default value: 0

        base_specificity(float, optional):
            The specificity of the diagnostic. This sets the proportion of the time that individuals without
            the condition being tested receive a negative diagnostic test. When set to 1, the diagnostic always
            accurately reflects the lack of having the condition. When set to zero, then individuals who do not
            have the condition always receive a false-positive diagnostic test.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        base_sensitivity(float, optional):
            The sensitivity of the diagnostic. This sets the proportion of the time that individuals with the
            condition being tested receive a positive diagnostic test. When set to 1, the diagnostic always
            accurately reflects the condition. When set to zero, then individuals who have the condition always
            receive a false-negative diagnostic test.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 positive_diagnosis_config: IndividualIntervention = None,
                 positive_diagnosis_event: str = None,
                 treatment_fraction: float = 1,
                 enable_is_symptomatic: bool = False,
                 days_to_diagnosis: float = 0,
                 base_specificity: float = 1,
                 base_sensitivity: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'SimpleDiagnostic', common_intervention_parameters)
        if bool(positive_diagnosis_event) == bool(positive_diagnosis_config):
            raise ValueError("Either 'positive_diagnosis_config' or 'positive_diagnosis_event' must be defined, "
                             "but not both.")
        if positive_diagnosis_config:
            if not isinstance(positive_diagnosis_config, IndividualIntervention):
                raise ValueError('positive_diagnosis_config must be a Intervention instance.')
            self._intervention.Positive_Diagnosis_Config = positive_diagnosis_config.to_schema_dict()
            self._intervention.Event_Or_Config = EventOrConfig.Config
            self._intervention.pop("Positive_Diagnosis_Event")
        else:
            self._intervention.Positive_Diagnosis_Event = set_event(positive_diagnosis_event,
                                                                    'positive_diagnosis_event', campaign, False)
            self._intervention.pop("Positive_Diagnosis_Config")
            self._intervention.Event_Or_Config = EventOrConfig.Event

        self._intervention.Treatment_Fraction = validate_value_range(treatment_fraction, 'treatment_fraction', 0, 1, float)
        self._intervention.Enable_Is_Symptomatic = enable_is_symptomatic
        self._intervention.Days_To_Diagnosis = validate_value_range(days_to_diagnosis, 'days_to_diagnosis', 0, 3.40282e+38, float)
        self._intervention.Base_Specificity = validate_value_range(base_specificity, 'base_specificity', 0, 1, float)
        self._intervention.Base_Sensitivity = validate_value_range(base_sensitivity, 'base_sensitivity', 0, 1, float)


# DanB - Making this private because I have not seen people use it.  It is also just a specialized
# DelayedIntervention with an exponential delay.

class _SimpleHealthSeekingBehavior(IndividualIntervention):
    """
    The **SimpleHealthSeekingBehavior** intervention class models the time delay that typically occurs between
    when an individual experiences onset of symptoms and when they seek help from a health care provider.
    Several factors may contribute to such delays including accessibility, cost, and trust in the health care
    system. This intervention models this time delay as an exponential process; at every time step, the model
    draws randomly to determine if the individual will receive the specified intervention. As an example, this
    intervention can be distributed using **add_intervention_triggered()** so that when an individual is
    infected, he or she receives a **SimpleHealthSeekingBehavior**, representing that the individual will now
    seek care. The individual subsequently seeks care with an exponentially distributed delay and ultimately
    receives the specified intervention or sents out an event that triggers them receiving an intervention.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        intervention_config(IndividualIntervention, optional):
            The configuration for the IndividualIntervention that the individual will receive after the delay.
            Default value: None

        intervention_event(str, optional):
            The name of the event to broadcast when individual has been selected to receive care after the delay.
            For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria,
            :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own
            custom event.
            Default value: None

        tendency(float, optional):
            The probability of seeking healthcare.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        single_use(bool, optional):
            If set to True, the health-seeking behavior gets used once and discarded. If set to False,
            it remains indefinitely.
            Default value: True

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 4 common
            parameters: intervention_name, new_property_value, dont_allow_duplicates, disqualifying_properties.
            The following parameters are not valid for this intervention:
            cost
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 intervention_config: IndividualIntervention = None,
                 intervention_event: str = None,
                 tendency: float = 1,
                 single_use: bool = True,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'SimpleHealthSeekingBehavior', common_intervention_parameters)
        if bool(intervention_event) == bool(intervention_config):
            raise ValueError("Either 'intervention_config' or 'intervention_event' must be defined, but not both.")

        if intervention_config:
            if not isinstance(intervention_config, IndividualIntervention):
                raise ValueError('intervention_config must be a IndividualIntervention instance.')
            self._intervention.Actual_IndividualIntervention_Config = intervention_config.to_schema_dict()
            self._intervention.Event_Or_Config = EventOrConfig.Config
            self._intervention.pop("Actual_IndividualIntervention_Event")
        else: # it's an event!
            self._intervention.Actual_IndividualIntervention_Event = set_event(intervention_event,
                                                                               'intervention_event',
                                                                               campaign, False)
            self._intervention.Event_Or_Config = EventOrConfig.Event
            self._intervention.pop("Actual_IndividualIntervention_Config")
        self._intervention.Tendency = validate_value_range(tendency, 'tendency', 0, 1, float)
        self._intervention.Single_Use = single_use

    def _set_cost(self, cost: float) -> None:
        raise ValueError('Cost_To_Consumer is not a valid parameter for the SimpleHealthSeekingBehavior intervention.')


class SimpleVaccine(IndividualIntervention):
    """
    The **SimpleVaccine** intervention class implements vaccine campaigns in the simulation.
    Vaccines can have an effect on one of the following:

        - Reduce the likelihood of acquiring an infection
        - Reduce the likelihood of transmitting an infection
        - Reduce the likelihood of death

    To configure vaccines that have an effect on more than one of these, use **MultiEffectVaccine** instead.

    Args:
        campaign (api_campaign, required):
            An instance of the emod_api.campaign module.

        waning_config(AbstractWaningConfig, required):
            The configuration of the vaccine's efficacy and waning over time. Specify how this effect decays
            over time using one of the Waning Config classes in emodpy.campaign.waning_config.

        vaccine_type(VaccineType, optional):
            The type of vaccine to distribute in a vaccine intervention. Possible values are:
            * Generic - The vaccine can reduce transmission, acquisition, and mortality.
            * TransmissionBlocking - The vaccine will reduce pathogen transmission.
            * AcquisitionBlocking - The vaccine will reduce the acquisition of the pathogen by reducing the
            force of infection experienced by the vaccinated individual.
            * MortalityBlocking - The vaccine reduces the disease-mortality rate of a vaccinated individual.
            Default value: Generic

        vaccine_take(float, optional):
            The rate at which delivered vaccines will successfully stimulate an immune response and achieve the
            desired efficacy. For example, if it is set to 0.9, there will be a 90 percent chance that the
            vaccine will start with the specified efficacy, and a 10 percent chance that it will have no
            efficacy at all.
            Minimum value: 0
            Maximum value: 1
            Default value: 1

        efficacy_is_multiplicative(bool, optional):
            The overall vaccine efficacy when individuals receive more than one vaccine. When set to True,
            the vaccine efficacies are multiplied together; when set to False, the efficacies are additive.
            Default value: True

        common_intervention_parameters (CommomInterventionParameters, optional):
            The CommonInterventionParameters object that Additional parameters that contains the 5 common
            parameters: cost, new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 waning_config: AbstractWaningConfig,
                 vaccine_type: VaccineType = VaccineType.Generic,
                 vaccine_take: float = 1,
                 efficacy_is_multiplicative: bool = True,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'SimpleVaccine', common_intervention_parameters)
        if not isinstance(waning_config, AbstractWaningConfig):
            raise ValueError(f"waning_config must be an instance of AbstractWaningConfig, not {type(waning_config)}.")

        self._intervention.Waning_Config = waning_config.to_schema_dict(campaign)
        self._intervention.Vaccine_Type = vaccine_type
        self._intervention.Vaccine_Take = validate_value_range(vaccine_take, 'vaccine_take', 0, 1, float)
        self._intervention.Efficacy_Is_Multiplicative = efficacy_is_multiplicative


class StandardDiagnostic(IndividualIntervention):
    """
    The **StandardDiagnostic** intervention class identifies infected individuals, regardless of disease state,
    based on specified diagnostic sensitivity and specificity. Diagnostics are a key component of modern disease
    control efforts, whether used to identify high-risk individuals, infected individuals, or drug resistance.
    The individual receives the diagnostic test immediately when the intervention is distributed, but there may
    be a delay in receiving a positive result. This intervention class distributes a specified intervention to a
    fraction of individuals who test positive.

        - You can use either the XXX_diagnosis_config or XXX_diagnosis_event parameters, but not both.
        - You must specifiy a response for a postive diagnosis, but not for a negative diagnosis.

    Args:
        campaign (api_campaign, required):
            - An instance of the emod_api.campaign module.

        positive_diagnosis_config(IndividualIntervention, optional):
            - The intervention distributed to individuals if they test positive.
            - Must be defined if not using postive_diagnosis_event.
            - Cannot have both positive_diagnosis_config and positive_diagnosis_event.
            - Default value: None

        negative_diagnosis_config(IndividualIntervention, optional):
            - The intervention distributed to individuals if they test negative.
            - If using postive_diagnosis_config, you can use negative_diagnosis_config, but not negative_diagnosis_event.
            - Can use this or negative_diagnosis_event, but not both.
            - Default value: None

        positive_diagnosis_event(str, optional):
            - If the test is positive, this specifies an event that can trigger another intervention when the event occurs.
            - Must be defined if not using positive_diagnosis_config.
            - Cannot have both positive_diagnosis_config and positive_diagnosis_event.
            - For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria, :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own custom event.
            - Default value: None

        negative_diagnosis_event(str, optional):
            - This parameter defines the event to be broadcasted on a negative test result.
            - Cannot have both negative_diagnosis_config and negative_diagnosis_event.
            - if using positive_diagnosis_config, you can use negative_diagnosis_config, but not negative_diagnosis_event.
            - For HIV, see :doc:`emod-hiv:emod/parameter-campaign-event-list`, and for malaria, :doc:`emod-malaria:emod/parameter-campaign-event-list` for events already used in EMOD or use your own custom event.
            - Default value: None

        treatment_fraction(float, optional):
            - The fraction of positive diagnoses that are given the positive_diagnosis_config or
              positive_diagnosis_event, whichever is defined. This does not affect the distribution of the negative
              diagnosis.
            - Minimum value: 0
            - Maximum value: 1
            - Default value: 1

        enable_is_symptomatic(bool, optional):
            - If True, requires an infection to be symptomatic to return a positive test.
            - Default value: True

        days_to_diagnosis(float, optional):
            - The number of days from the test, which is done when the intervention is distributed, until the
              positive_diagnosis_config or positive_diagnosis_event (whichever is defined) are distributed if the test
              had a positive diagnosis. The negative_diagnosis_config or negative_diagnosis_event is distributed
              immediately if the test is negative.
            - Minimum value: 0
            - Maximum value: 3.40282e+38
            - Default value: 0

        base_specificity(float, optional):
            - The specificity of the diagnostic. This sets the proportion of the time that individuals without
              the condition being tested receive a negative diagnostic test. When set to 1, the diagnostic always
              accurately reflects the lack of having the condition. When set to zero, then individuals who do not
              have the condition always receive a false-positive diagnostic test.
            - Minimum value: 0
            - Maximum value: 1
            - Default value: 1

        base_sensitivity(float, optional):
            - The sensitivity of the diagnostic. This sets the proportion of the time that individuals with the
              condition being tested receive a positive diagnostic test. When set to 1, the diagnostic always
              accurately reflects the condition. When set to zero, then individuals who have the condition always
              receive a false-negative diagnostic test.
            - Minimum value: 0
            - Maximum value: 1
            - Default value: 1

        common_intervention_parameters (CommomInterventionParameters, optional):
            - The CommonInterventionParameters object that contains the 5 common additional parameters: cost,
              new_property_value, intervention_name, disqualifying_properties, dont_allow_duplicates.
            - Default value: None
    """

    def __init__(self,
                 campaign: api_campaign,
                 positive_diagnosis_config: IndividualIntervention = None,
                 negative_diagnosis_config: IndividualIntervention = None,
                 positive_diagnosis_event: str = None,
                 negative_diagnosis_event: str = None,
                 treatment_fraction: float = 1,
                 enable_is_symptomatic: bool = False,
                 days_to_diagnosis: float = 0,
                 base_specificity: float = 1,
                 base_sensitivity: float = 1,
                 common_intervention_parameters: CommonInterventionParameters = None):
        super().__init__(campaign, 'StandardDiagnostic', common_intervention_parameters)

        if positive_diagnosis_config is None and positive_diagnosis_event is None:
            raise ValueError("Either 'positive_diagnosis_config' or 'positive_diagnosis_event' must be defined, but not both.")
        if positive_diagnosis_config is not None and positive_diagnosis_event is not None:
            raise ValueError("Either 'positive_diagnosis_config' or 'positive_diagnosis_event' must be defined, but not both.")
        if negative_diagnosis_config is not None and negative_diagnosis_event is not None:
            raise ValueError("Either 'negative_diagnosis_config' or 'negative_diagnosis_event' can be defined, but not both.")
        if positive_diagnosis_config is not None and negative_diagnosis_event is not None:
            raise ValueError("If using 'positive_diagnosis_config', you can use 'negative_diagnosis_config', but not 'negative_diagnosis_event'.")
        if positive_diagnosis_event is not None and negative_diagnosis_config is not None:
            raise ValueError("If using 'positive_diagnosis_event', you can use 'negative_diagnosis_event', but not 'negative_diagnosis_config'.")

        if positive_diagnosis_config is not None:
            if not isinstance(positive_diagnosis_config, IndividualIntervention):
                raise ValueError("'positive_diagnosis_config' must be an IndividualIntervention instance.")
            self._intervention.Event_Or_Config = EventOrConfig.Config
            self._intervention.Positive_Diagnosis_Config = positive_diagnosis_config.to_schema_dict()

            if negative_diagnosis_config is not None:
                if not isinstance(negative_diagnosis_config, IndividualIntervention):
                    raise ValueError('negative_diagnosis_config must be an IndividualIntervention instance.')
                self._intervention.Negative_Diagnosis_Config = negative_diagnosis_config.to_schema_dict()
            self._intervention.pop("Positive_Diagnosis_Event")
            self._intervention.pop("Negative_Diagnosis_Event")
        else:
            self._intervention.Event_Or_Config = EventOrConfig.Event
            self._intervention.Positive_Diagnosis_Event = set_event(positive_diagnosis_event, 'positive_diagnosis_event', campaign, False)
            self._intervention.Negative_Diagnosis_Event = set_event(negative_diagnosis_event, 'negative_diagnosis_event', campaign, True)
            self._intervention.pop("Positive_Diagnosis_Config")
            self._intervention.pop("Negative_Diagnosis_Config")

        self._intervention.Treatment_Fraction = validate_value_range(treatment_fraction, 'treatment_fraction', 0, 1,
                                                                     float)
        self._intervention.Enable_Is_Symptomatic = enable_is_symptomatic
        self._intervention.Days_To_Diagnosis = validate_value_range(days_to_diagnosis, 'days_to_diagnosis', 0, 3.40282e+38, float)
        self._intervention.Base_Specificity = validate_value_range(base_specificity, 'base_specificity', 0, 1, float)
        self._intervention.Base_Sensitivity = validate_value_range(base_sensitivity, 'base_sensitivity', 0, 1, float)
