import unittest
import pytest

from emod_api import campaign as api_campaign

from emodpy.campaign.event_coordinator import (
    StandardEventCoordinator,
    CoverageByNodeEventCoordinator,
    CommunityHealthWorkerEventCoordinator,
    NodeIdAndCoverage,
    Action,
    Responder,
    IncidenceCounter,
    IncidenceEventCoordinator,
    IncidenceCounterSurveillance,
    ResponderSurveillance,
    SurveillanceEventCoordinator,
    BroadcastCoordinatorEvent,
)
from emodpy.campaign.individual_intervention import BroadcastEvent, SimpleVaccine
from emodpy.campaign.node_intervention import Outbreak
from emodpy.campaign.common import (
    TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions, TargetGender
)
from emodpy.campaign.waning_config import MapLinear
from emodpy.utils.distributions import ConstantDistribution, UniformDistribution
from emodpy.utils.emod_enum import ThresholdType, EventType
from emodpy.utils.targeting_config import IsPregnant

from base_test import TestHIV, TestMalaria, BaseTestClass


# ---------------------------------------------------------------------------
# StandardEventCoordinator
# ---------------------------------------------------------------------------
class BaseStandardEventCoordinatorTest(BaseTestClass):

    def test_individual_intervention_defaults(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        ec = StandardEventCoordinator(self.campaign, intervention_list=iv)
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'StandardInterventionDistributionEventCoordinator')
        self.assertEqual(d.Intervention_Config['class'], 'BroadcastEvent')
        self.assertEqual(d.Demographic_Coverage, 1)
        self.assertEqual(d.Target_Demographic, 'Everyone')

    def test_individual_intervention_with_options(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        ec = StandardEventCoordinator(
            self.campaign,
            intervention_list=iv,
            target_demographics_config=TargetDemographicsConfig(
                demographic_coverage=0.8, target_gender=TargetGender.FEMALE),
            repetition_config=RepetitionConfig(number_repetitions=3, timesteps_between_repetitions=10),
            property_restrictions=PropertyRestrictions(
                individual_property_restrictions=[["Risk:High"]]),
            targeting_config=~IsPregnant())
        d = ec.to_schema_dict()
        self.assertEqual(d.Demographic_Coverage, 0.8)
        self.assertEqual(d.Target_Gender, 'Female')
        self.assertEqual(d.Number_Repetitions, 3)
        self.assertEqual(d.Timesteps_Between_Repetitions, 10)
        self.assertEqual(d.Property_Restrictions_Within_Node, [{'Risk': 'High'}])
        self.assertEqual(d.Targeting_Config['class'], 'IsPregnant')

    def test_node_intervention(self):
        iv = [Outbreak(self.campaign, number_cases_per_node=5)]
        ec = StandardEventCoordinator(self.campaign, intervention_list=iv)
        d = ec.to_schema_dict()
        self.assertEqual(d.Intervention_Config['class'], 'Outbreak')

    def test_node_intervention_rejects_demographics_config(self):
        iv = [Outbreak(self.campaign, number_cases_per_node=5)]
        with self.assertRaises(ValueError):
            StandardEventCoordinator(
                self.campaign,
                intervention_list=iv,
                target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.5))

    def test_node_intervention_rejects_individual_property_restrictions(self):
        iv = [Outbreak(self.campaign, number_cases_per_node=5)]
        with self.assertRaises(ValueError):
            StandardEventCoordinator(
                self.campaign,
                intervention_list=iv,
                property_restrictions=PropertyRestrictions(
                    individual_property_restrictions=[["Risk:High"]]))

    def test_multi_individual_interventions(self):
        iv = [BroadcastEvent(self.campaign, "Evt1"),
              SimpleVaccine(self.campaign, waning_config=MapLinear([2010], [0.9]))]
        ec = StandardEventCoordinator(self.campaign, intervention_list=iv)
        d = ec.to_schema_dict()
        self.assertEqual(d.Intervention_Config['class'], 'MultiInterventionDistributor')

    def test_empty_intervention_list_raises(self):
        with self.assertRaises(ValueError):
            StandardEventCoordinator(self.campaign, intervention_list=[])

    def test_mixed_intervention_list_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1"),
              Outbreak(self.campaign, number_cases_per_node=5)]
        with self.assertRaises(ValueError):
            StandardEventCoordinator(self.campaign, intervention_list=iv)


@pytest.mark.unit
class TestStandardECHIV(TestHIV, BaseStandardEventCoordinatorTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestStandardECMalaria(TestMalaria, BaseStandardEventCoordinatorTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# NodeIdAndCoverage
# ---------------------------------------------------------------------------
class BaseNodeIdAndCoverageTest(BaseTestClass):

    def test_valid(self):
        nic = NodeIdAndCoverage(node_id=1, coverage=0.5)
        d = nic.to_schema_dict(self.campaign)
        self.assertEqual(d.Node_Id, 1)
        self.assertEqual(d.Coverage, 0.5)

    def test_invalid_node_id(self):
        with self.assertRaises(ValueError):
            NodeIdAndCoverage(node_id=-1, coverage=0.5)

    def test_invalid_coverage(self):
        with self.assertRaises(ValueError):
            NodeIdAndCoverage(node_id=1, coverage=1.5)


@pytest.mark.unit
class TestNodeIdAndCoverageHIV(TestHIV, BaseNodeIdAndCoverageTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestNodeIdAndCoverageMalaria(TestMalaria, BaseNodeIdAndCoverageTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# CoverageByNodeEventCoordinator
# ---------------------------------------------------------------------------
class BaseCoverageByNodeECTest(BaseTestClass):

    def test_basic(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        ec = CoverageByNodeEventCoordinator(
            self.campaign, intervention_list=iv, coverage_by_node=[(1, 0.8), (2, 0.5)])
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'CoverageByNodeEventCoordinator')
        self.assertEqual(len(d.Coverage_By_Node), 2)
        self.assertEqual(d.Coverage_By_Node[0].Node_Id, 1)
        self.assertEqual(d.Coverage_By_Node[0].Coverage, 0.8)
        self.assertEqual(d.Coverage_By_Node[1].Node_Id, 2)
        self.assertEqual(d.Coverage_By_Node[1].Coverage, 0.5)

    def test_empty_coverage_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(self.campaign, intervention_list=iv, coverage_by_node=[])

    def test_duplicate_node_ids_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(1, 0.8), (1, 0.5)])

    def test_invalid_tuple_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(1,)])
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=["bad"])

    def test_invalid_node_id_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(-1, 0.5)])

    def test_invalid_coverage_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError):
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(1, 1.5)])

    def test_demographic_coverage_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError) as ctx:
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(1, 0.8)],
                target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.5))
        self.assertIn("demographic_coverage", str(ctx.exception))

    def test_demographic_coverage_default_raises(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        with self.assertRaises(ValueError) as ctx:
            CoverageByNodeEventCoordinator(
                self.campaign, intervention_list=iv, coverage_by_node=[(1, 0.8)],
                target_demographics_config=TargetDemographicsConfig())
        self.assertIn("demographic_coverage", str(ctx.exception))

    def test_demographics_without_coverage_allowed(self):
        iv = [BroadcastEvent(self.campaign, "Evt1")]
        ec = CoverageByNodeEventCoordinator(
            self.campaign, intervention_list=iv, coverage_by_node=[(1, 0.8)],
            target_demographics_config=TargetDemographicsConfig(
                demographic_coverage=None, target_gender=TargetGender.FEMALE))
        d = ec.to_schema_dict()
        self.assertEqual(d.Target_Gender, "Female")


@pytest.mark.unit
class TestCoverageByNodeECHIV(TestHIV, BaseCoverageByNodeECTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestCoverageByNodeECMalaria(TestMalaria, BaseCoverageByNodeECTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# CommunityHealthWorkerEventCoordinator
# ---------------------------------------------------------------------------
class BaseCHWEventCoordinatorTest(BaseTestClass):

    def _make_chw(self, **overrides):
        defaults = dict(
            campaign=self.campaign,
            intervention_list=[BroadcastEvent(self.campaign, "CHW_Event")],
            trigger_condition_list=["NewClinicalCase"],
            initial_amount_distribution=ConstantDistribution(500),
            max_distributed_per_day=10,
            waiting_period=30,
            days_between_shipments=7,
            amount_in_shipment=100,
        )
        defaults.update(overrides)
        return CommunityHealthWorkerEventCoordinator(**defaults)

    def test_basic(self):
        ec = self._make_chw()
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'CommunityHealthWorkerEventCoordinator')
        self.assertEqual(d.Max_Distributed_Per_Day, 10)
        self.assertEqual(d.Waiting_Period, 30)
        self.assertEqual(d.Days_Between_Shipments, 7)
        self.assertEqual(d.Amount_In_Shipment, 100)
        self.assertEqual(d.Trigger_Condition_List, ["NewClinicalCase"])

    def test_with_duration_and_max_stock(self):
        ec = self._make_chw(duration=365.0, max_stock=1000)
        d = ec.to_schema_dict()
        self.assertEqual(d.Duration, 365.0)
        self.assertEqual(d.Max_Stock, 1000)

    def test_node_intervention(self):
        ec = self._make_chw(
            intervention_list=[Outbreak(self.campaign, number_cases_per_node=5)],
            property_restrictions=PropertyRestrictions(
                node_property_restrictions=[["Place:Urban"]]))
        d = ec.to_schema_dict()
        self.assertEqual(d.Intervention_Config['class'], 'Outbreak')
        self.assertEqual(d.Node_Property_Restrictions, [{'Place': 'Urban'}])

    def test_node_intervention_rejects_demographics(self):
        with self.assertRaises(ValueError):
            self._make_chw(
                intervention_list=[Outbreak(self.campaign, number_cases_per_node=5)],
                target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.5))

    def test_invalid_max_distributed_per_day(self):
        with self.assertRaises(ValueError):
            self._make_chw(max_distributed_per_day=0)

    def test_invalid_waiting_period(self):
        with self.assertRaises(ValueError):
            self._make_chw(waiting_period=-1)

    def test_invalid_days_between_shipments(self):
        with self.assertRaises(ValueError):
            self._make_chw(days_between_shipments=0)


@pytest.mark.unit
class TestCHWECHIV(TestHIV, BaseCHWEventCoordinatorTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestCHWECMalaria(TestMalaria, BaseCHWEventCoordinatorTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------
class BaseActionTest(BaseTestClass):

    def test_individual_event_type(self):
        action = Action(threshold=10.0, event_to_broadcast="MyEvent", event_type=EventType.INDIVIDUAL)
        d = action.to_schema_dict(self.campaign)
        self.assertEqual(d.Threshold, 10.0)
        self.assertEqual(d.Event_To_Broadcast, "MyEvent")
        self.assertEqual(d.Event_Type, "INDIVIDUAL")

    def test_node_event_type(self):
        action = Action(threshold=5.0, event_to_broadcast="NodeEvt", event_type=EventType.NODE)
        d = action.to_schema_dict(self.campaign)
        self.assertEqual(d.Event_To_Broadcast, "NodeEvt")
        self.assertEqual(d.Event_Type, "NODE")

    def test_coordinator_event_type(self):
        action = Action(threshold=1.0, event_to_broadcast="CoordEvt", event_type=EventType.COORDINATOR)
        d = action.to_schema_dict(self.campaign)
        self.assertEqual(d.Event_To_Broadcast, "CoordEvt")
        self.assertEqual(d.Event_Type, "COORDINATOR")

    def test_string_event_type(self):
        action = Action(threshold=10.0, event_to_broadcast="MyEvent", event_type="INDIVIDUAL")
        d = action.to_schema_dict(self.campaign)
        self.assertEqual(d.Event_Type, "INDIVIDUAL")

    def test_invalid_event_type(self):
        with self.assertRaises(ValueError) as ctx:
            Action(threshold=10.0, event_to_broadcast="MyEvent", event_type="INVALID")
        self.assertIn("EventType", str(ctx.exception))

    def test_empty_event_to_broadcast(self):
        with self.assertRaises(ValueError):
            Action(threshold=10.0, event_to_broadcast="", event_type=EventType.INDIVIDUAL)

    def test_none_event_to_broadcast(self):
        with self.assertRaises(ValueError):
            Action(threshold=10.0, event_to_broadcast=None, event_type=EventType.INDIVIDUAL)

    def test_negative_threshold(self):
        with self.assertRaises(ValueError):
            Action(threshold=-1.0, event_to_broadcast="MyEvent", event_type=EventType.INDIVIDUAL)


@pytest.mark.unit
class TestActionHIV(TestHIV, BaseActionTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestActionMalaria(TestMalaria, BaseActionTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# Responder
# ---------------------------------------------------------------------------
class BaseResponderTest(BaseTestClass):

    def test_basic(self):
        actions = [Action(threshold=0.0, event_to_broadcast="Evt1", event_type=EventType.INDIVIDUAL)]
        resp = Responder(action_list=actions, threshold_type=ThresholdType.COUNT)
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Threshold_Type, "COUNT")
        self.assertEqual(len(d.Action_List), 1)

    def test_multiple_actions(self):
        actions = [
            Action(threshold=0.0, event_to_broadcast="Low", event_type=EventType.INDIVIDUAL),
            Action(threshold=50.0, event_to_broadcast="High", event_type=EventType.INDIVIDUAL),
        ]
        resp = Responder(action_list=actions)
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(len(d.Action_List), 2)

    def test_string_threshold_type(self):
        actions = [Action(threshold=0.0, event_to_broadcast="Evt1", event_type=EventType.INDIVIDUAL)]
        resp = Responder(action_list=actions, threshold_type="PERCENTAGE")
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Threshold_Type, "PERCENTAGE")

    def test_empty_action_list(self):
        with self.assertRaises(ValueError):
            Responder(action_list=[])

    def test_duplicate_thresholds(self):
        actions = [
            Action(threshold=10.0, event_to_broadcast="Evt1", event_type=EventType.INDIVIDUAL),
            Action(threshold=10.0, event_to_broadcast="Evt2", event_type=EventType.INDIVIDUAL),
        ]
        with self.assertRaises(ValueError):
            Responder(action_list=actions)

    def test_invalid_threshold_type(self):
        actions = [Action(threshold=0.0, event_to_broadcast="Evt1", event_type=EventType.INDIVIDUAL)]
        with self.assertRaises(ValueError):
            Responder(action_list=actions, threshold_type="INVALID")


@pytest.mark.unit
class TestResponderHIV(TestHIV, BaseResponderTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestResponderMalaria(TestMalaria, BaseResponderTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# IncidenceCounter
# ---------------------------------------------------------------------------
class BaseIncidenceCounterTest(BaseTestClass):

    def test_basic(self):
        counter = IncidenceCounter(
            trigger_condition_list=["NewClinicalCase"],
            count_events_for_num_timesteps=5)
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Trigger_Condition_List, ["NewClinicalCase"])
        self.assertEqual(d.Count_Events_For_Num_Timesteps, 5)
        self.assertEqual(d.Demographic_Coverage, 1.0)

    def test_with_demographics(self):
        counter = IncidenceCounter(
            trigger_condition_list=["NewClinicalCase"],
            count_events_for_num_timesteps=3,
            target_demographics_config=TargetDemographicsConfig(
                demographic_coverage=0.7,
                target_gender=TargetGender.MALE))
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Demographic_Coverage, 0.7)
        self.assertEqual(d.Target_Gender, "Male")

    def test_with_all_demographics_options(self):
        counter = IncidenceCounter(
            trigger_condition_list=["NewClinicalCase"],
            count_events_for_num_timesteps=3,
            target_demographics_config=TargetDemographicsConfig(
                demographic_coverage=0.8,
                target_age_min=15,
                target_age_max=49,
                target_gender=TargetGender.FEMALE,
                target_residents_only=True))
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Demographic_Coverage, 0.8)
        self.assertEqual(d.Target_Age_Min, 15)
        self.assertEqual(d.Target_Age_Max, 49)
        self.assertEqual(d.Target_Gender, "Female")
        self.assertEqual(d.Target_Residents_Only, True)
        self.assertEqual(d.Target_Demographic, "ExplicitAgeRangesAndGender")

    def test_invalid_count_events_for_num_timesteps(self):
        with self.assertRaises(ValueError):
            IncidenceCounter(
                trigger_condition_list=["NewClinicalCase"],
                count_events_for_num_timesteps=0)


@pytest.mark.unit
class TestIncidenceCounterHIV(TestHIV, BaseIncidenceCounterTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestIncidenceCounterMalaria(TestMalaria, BaseIncidenceCounterTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# IncidenceEventCoordinator
# ---------------------------------------------------------------------------
class BaseIncidenceECTest(BaseTestClass):

    def _make_incidence_ec(self, **overrides):
        defaults = dict(
            campaign=self.campaign,
            incidence_counter=IncidenceCounter(
                trigger_condition_list=["NewClinicalCase"],
                count_events_for_num_timesteps=5),
            responder=Responder(
                action_list=[Action(threshold=0.0, event_to_broadcast="Alert",
                                    event_type=EventType.INDIVIDUAL)]),
        )
        defaults.update(overrides)
        return IncidenceEventCoordinator(**defaults)

    def test_basic(self):
        ec = self._make_incidence_ec()
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'IncidenceEventCoordinator')
        self.assertEqual(d.Number_Repetitions, 1)
        self.assertEqual(d.Timesteps_Between_Repetitions, -1)

    def test_with_options(self):
        ec = self._make_incidence_ec(
            coordinator_name="TestCoordinator",
            number_repetitions=5,
            timesteps_between_repetitions=10)
        d = ec.to_schema_dict()
        self.assertEqual(d.Coordinator_Name, "TestCoordinator")
        self.assertEqual(d.Number_Repetitions, 5)
        self.assertEqual(d.Timesteps_Between_Repetitions, 10)

    def test_invalid_counter_type(self):
        with self.assertRaises(ValueError):
            self._make_incidence_ec(incidence_counter="not_a_counter")

    def test_invalid_responder_type(self):
        with self.assertRaises(ValueError):
            self._make_incidence_ec(responder="not_a_responder")

    def test_invalid_number_repetitions(self):
        with self.assertRaises(ValueError):
            self._make_incidence_ec(number_repetitions=-2)


@pytest.mark.unit
class TestIncidenceECHIV(TestHIV, BaseIncidenceECTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestIncidenceECMalaria(TestMalaria, BaseIncidenceECTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# IncidenceCounterSurveillance
# ---------------------------------------------------------------------------
class BaseIncidenceCounterSurveillanceTest(BaseTestClass):

    def test_individual_event_type(self):
        counter = IncidenceCounterSurveillance(
            trigger_condition_list=["NewClinicalCase"],
            counter_period=30.0,
            counter_event_type=EventType.INDIVIDUAL,
            count_events_for_num_timesteps=5)
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Trigger_Condition_List, ["NewClinicalCase"])
        self.assertEqual(d.Counter_Period, 30.0)
        self.assertEqual(d.Counter_Event_Type, "INDIVIDUAL")
        self.assertEqual(d.Count_Events_For_Num_Timesteps, 5)

    def test_node_event_type(self):
        counter = IncidenceCounterSurveillance(
            trigger_condition_list=["NodeEvent1"],
            counter_period=30.0,
            counter_event_type=EventType.NODE,
            count_events_for_num_timesteps=5)
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Trigger_Condition_List, ["NodeEvent1"])
        self.assertEqual(d.Counter_Event_Type, "NODE")

    def test_coordinator_event_type(self):
        counter = IncidenceCounterSurveillance(
            trigger_condition_list=["CoordEvent1"],
            counter_period=30.0,
            counter_event_type=EventType.COORDINATOR,
            count_events_for_num_timesteps=5)
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Trigger_Condition_List, ["CoordEvent1"])
        self.assertEqual(d.Counter_Event_Type, "COORDINATOR")

    def test_string_event_type(self):
        counter = IncidenceCounterSurveillance(
            trigger_condition_list=["NewClinicalCase"],
            counter_period=30.0,
            counter_event_type="NODE",
            count_events_for_num_timesteps=5)
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Counter_Event_Type, "NODE")

    def test_invalid_event_type(self):
        with self.assertRaises(ValueError):
            IncidenceCounterSurveillance(
                trigger_condition_list=["NewClinicalCase"],
                counter_period=30.0,
                counter_event_type="INVALID",
                count_events_for_num_timesteps=5)

    def test_invalid_counter_period(self):
        with self.assertRaises(ValueError):
            IncidenceCounterSurveillance(
                trigger_condition_list=["NewClinicalCase"],
                counter_period=0.0,
                counter_event_type=EventType.INDIVIDUAL,
                count_events_for_num_timesteps=5)

    def test_with_demographics(self):
        counter = IncidenceCounterSurveillance(
            trigger_condition_list=["NewClinicalCase"],
            counter_period=30.0,
            counter_event_type=EventType.INDIVIDUAL,
            count_events_for_num_timesteps=5,
            target_demographics_config=TargetDemographicsConfig(
                demographic_coverage=0.6,
                target_age_min=15, target_age_max=49))
        d = counter.to_schema_dict(self.campaign)
        self.assertEqual(d.Demographic_Coverage, 0.6)
        self.assertEqual(d.Target_Age_Min, 15)
        self.assertEqual(d.Target_Age_Max, 49)
        self.assertEqual(d.Target_Demographic, "ExplicitAgeRanges")


@pytest.mark.unit
class TestIncidenceCounterSurvHIV(TestHIV, BaseIncidenceCounterSurveillanceTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestIncidenceCounterSurvMalaria(TestMalaria, BaseIncidenceCounterSurveillanceTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# ResponderSurveillance
# ---------------------------------------------------------------------------
class BaseResponderSurveillanceTest(BaseTestClass):

    def _make_actions(self):
        return [Action(threshold=0.0, event_to_broadcast="Alert", event_type=EventType.INDIVIDUAL)]

    def test_basic(self):
        resp = ResponderSurveillance(action_list=self._make_actions())
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Threshold_Type, "COUNT")
        self.assertEqual(len(d.Action_List), 1)

    def test_with_responded_event(self):
        resp = ResponderSurveillance(
            action_list=self._make_actions(),
            responded_event="RespondedEvt")
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Responded_Event, "RespondedEvt")

    def test_percentage_events_individual(self):
        resp = ResponderSurveillance(
            action_list=self._make_actions(),
            threshold_type=ThresholdType.PERCENTAGE_EVENTS,
            percentage_events_to_count=["DenominatorEvt"],
            counter_event_type=EventType.INDIVIDUAL)
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Threshold_Type, "PERCENTAGE_EVENTS")
        self.assertEqual(d.Percentage_Events_To_Count, ["DenominatorEvt"])

    def test_percentage_events_node(self):
        resp = ResponderSurveillance(
            action_list=self._make_actions(),
            threshold_type=ThresholdType.PERCENTAGE_EVENTS,
            percentage_events_to_count=["NodeDenomEvt"],
            counter_event_type=EventType.NODE)
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Percentage_Events_To_Count, ["NodeDenomEvt"])

    def test_percentage_events_coordinator(self):
        resp = ResponderSurveillance(
            action_list=self._make_actions(),
            threshold_type=ThresholdType.PERCENTAGE_EVENTS,
            percentage_events_to_count=["CoordDenomEvt"],
            counter_event_type=EventType.COORDINATOR)
        d = resp.to_schema_dict(self.campaign)
        self.assertEqual(d.Percentage_Events_To_Count, ["CoordDenomEvt"])

    def test_percentage_events_missing_list(self):
        with self.assertRaises(ValueError) as ctx:
            ResponderSurveillance(
                action_list=self._make_actions(),
                threshold_type=ThresholdType.PERCENTAGE_EVENTS)
        self.assertIn("percentage_events_to_count", str(ctx.exception))

    def test_percentage_events_missing_counter_event_type(self):
        with self.assertRaises(ValueError) as ctx:
            ResponderSurveillance(
                action_list=self._make_actions(),
                threshold_type=ThresholdType.PERCENTAGE_EVENTS,
                percentage_events_to_count=["Evt1"])
        self.assertIn("counter_event_type", str(ctx.exception))

    def test_percentage_events_to_count_without_percentage_events_type(self):
        with self.assertRaises(ValueError) as ctx:
            ResponderSurveillance(
                action_list=self._make_actions(),
                threshold_type=ThresholdType.COUNT,
                percentage_events_to_count=["Evt1"])
        self.assertIn("percentage_events_to_count", str(ctx.exception))

    def test_invalid_counter_event_type(self):
        with self.assertRaises(ValueError):
            ResponderSurveillance(
                action_list=self._make_actions(),
                threshold_type=ThresholdType.PERCENTAGE_EVENTS,
                percentage_events_to_count=["Evt1"],
                counter_event_type="INVALID")


@pytest.mark.unit
class TestResponderSurvHIV(TestHIV, BaseResponderSurveillanceTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestResponderSurvMalaria(TestMalaria, BaseResponderSurveillanceTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# SurveillanceEventCoordinator
# ---------------------------------------------------------------------------
class BaseSurveillanceECTest(BaseTestClass):

    def _make_counter(self, event_type=EventType.INDIVIDUAL):
        return IncidenceCounterSurveillance(
            trigger_condition_list=["NewClinicalCase"],
            counter_period=30.0,
            counter_event_type=event_type,
            count_events_for_num_timesteps=5)

    def _make_responder(self):
        actions = [Action(threshold=0.0, event_to_broadcast="Alert", event_type=EventType.INDIVIDUAL)]
        return ResponderSurveillance(action_list=actions)

    def _make_surveillance_ec(self, **overrides):
        defaults = dict(
            campaign=self.campaign,
            incidence_counter=self._make_counter(),
            responder=self._make_responder(),
            start_trigger_condition_list=["StartCounting"],
        )
        defaults.update(overrides)
        return SurveillanceEventCoordinator(**defaults)

    def test_basic(self):
        ec = self._make_surveillance_ec()
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'SurveillanceEventCoordinator')
        self.assertEqual(d.Start_Trigger_Condition_List, ["StartCounting"])
        self.assertEqual(d.Coordinator_Name, "SurveillanceEventCoordinator")
        self.assertEqual(d.Duration, -1)

    def test_with_stop_triggers(self):
        ec = self._make_surveillance_ec(
            stop_trigger_condition_list=["StopCounting"])
        d = ec.to_schema_dict()
        self.assertEqual(d.Stop_Trigger_Condition_List, ["StopCounting"])

    def test_with_options(self):
        ec = self._make_surveillance_ec(
            coordinator_name="MyCoordinator",
            duration=365.0)
        d = ec.to_schema_dict()
        self.assertEqual(d.Coordinator_Name, "MyCoordinator")
        self.assertEqual(d.Duration, 365.0)

    def test_invalid_counter_type(self):
        with self.assertRaises(ValueError):
            self._make_surveillance_ec(
                incidence_counter=IncidenceCounter(
                    trigger_condition_list=["Evt"], count_events_for_num_timesteps=5))

    def test_invalid_responder_type(self):
        with self.assertRaises(ValueError):
            resp = Responder(
                action_list=[Action(threshold=0.0, event_to_broadcast="Evt",
                                    event_type=EventType.INDIVIDUAL)])
            self._make_surveillance_ec(responder=resp)

    def test_empty_start_trigger_list(self):
        with self.assertRaises(ValueError):
            self._make_surveillance_ec(start_trigger_condition_list=[])

    def test_invalid_duration(self):
        with self.assertRaises(ValueError):
            self._make_surveillance_ec(duration=-2.0)


@pytest.mark.unit
class TestSurveillanceECHIV(TestHIV, BaseSurveillanceECTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestSurveillanceECMalaria(TestMalaria, BaseSurveillanceECTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


# ---------------------------------------------------------------------------
# BroadcastCoordinatorEvent
# ---------------------------------------------------------------------------
class BaseBroadcastCoordinatorEventTest(BaseTestClass):

    def test_defaults(self):
        ec = BroadcastCoordinatorEvent(self.campaign, broadcast_event="MyCoordEvent")
        d = ec.to_schema_dict()
        self.assertEqual(d['class'], 'BroadcastCoordinatorEvent')
        self.assertEqual(d.Broadcast_Event, "MyCoordEvent")
        self.assertEqual(d.Coordinator_Name, "BroadcastCoordinatorEvent")
        self.assertEqual(d.Cost_To_Consumer, 0)

    def test_with_options(self):
        ec = BroadcastCoordinatorEvent(
            self.campaign,
            broadcast_event="StartSurveillance",
            coordinator_name="MyBroadcaster",
            cost_to_consumer=5.0)
        d = ec.to_schema_dict()
        self.assertEqual(d.Broadcast_Event, "StartSurveillance")
        self.assertEqual(d.Coordinator_Name, "MyBroadcaster")
        self.assertEqual(d.Cost_To_Consumer, 5.0)

    def test_empty_broadcast_event(self):
        with self.assertRaises(ValueError):
            BroadcastCoordinatorEvent(self.campaign, broadcast_event="")

    def test_none_broadcast_event(self):
        with self.assertRaises(ValueError):
            BroadcastCoordinatorEvent(self.campaign, broadcast_event=None)

    def test_invalid_cost(self):
        with self.assertRaises(ValueError):
            BroadcastCoordinatorEvent(self.campaign, broadcast_event="Evt", cost_to_consumer=-1)


@pytest.mark.unit
class TestBroadcastCoordinatorEventHIV(TestHIV, BaseBroadcastCoordinatorEventTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


@pytest.mark.unit
class TestBroadcastCoordinatorEventMalaria(TestMalaria, BaseBroadcastCoordinatorEventTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)


if __name__ == '__main__':
    unittest.main()
