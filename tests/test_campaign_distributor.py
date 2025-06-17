import os
import sys
import json
from pathlib import Path
import unittest
import pytest
from emod_api import campaign as api_campaign
from emodpy.campaign.individual_intervention import BroadcastEvent, SimpleVaccine
from emodpy.campaign.node_intervention import Outbreak

from emodpy.campaign.distributor import add_intervention_triggered, add_intervention_scheduled
from emodpy.campaign.common import TargetDemographicsConfig, RepetitionConfig, PropertyRestrictions, TargetGender
from emodpy.utils.distributions import UniformDistribution, ExponentialDistribution
from emodpy.utils.targeting_config import IsPregnant
from emodpy.campaign.waning_config import MapLinear


parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
from base_test import TestHIV, TestMalaria, BaseTestClass
import manifest
import helpers

regression_folder = os.path.join(manifest.inputs_folder, 'campaigns', 'distributor_regression')
output_folder = os.path.join(manifest.output_folder, 'campaign_distributor')
if not os.path.exists(output_folder):
    os.makedirs(output_folder, exist_ok=True)


def compare_to_regression_json(campaign, filename):
    regression_file = os.path.join(regression_folder, filename)
    tmp_filename = os.path.join(output_folder, filename)
    campaign.save(tmp_filename)
    # Make sure the campaign file match regression file.
    # Load the json files into dictionaries and compare them.
    with open(os.path.join(output_folder, filename), 'r') as f:
        output = json.load(f)
    with open(regression_file, 'r') as f:
        regression = json.load(f)
    assert output == regression
    helpers.delete_existing_file(tmp_filename)


class BaseScheduledDistributorTest(BaseTestClass):

    def test_add_individual_intervention_scheduled_default(self):
        # Test the default parameters for add_intervention_scheduled with one individual intervention
        interventions = [BroadcastEvent(self.campaign, "Test_Event")]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year)
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year, default=True)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event, default=True)

        # Verify that the correct intervention was added to the event coordinator
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_Event')

    def test_add_individual_intervention_scheduled(self):
        # Test add_intervention_scheduled with one individual intervention without delay
        interventions = [BroadcastEvent(self.campaign, "Test_Event")]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Target 70% of female individuals
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.FEMALE),
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct intervention was added to the event coordinator
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_Event')

    def test_add_individual_intervention_scheduled_with_delay(self):
        # Test the add_intervention_scheduled with one individual intervention with delay
        interventions = [BroadcastEvent(self.campaign, "BroadcastEvent")]
        uniform_distribution = UniformDistribution(0, 365)
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Target 70% of female individuals
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.FEMALE),
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]]),
                                   delay_distribution=uniform_distribution,
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct intervention was added to the event coordinator with delay distribution
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'DelayedIntervention')
        self.assertEqual(intervention_config.Delay_Period_Distribution, 'UNIFORM_DISTRIBUTION')
        self.assertEqual(intervention_config.Delay_Period_Min, 0)
        self.assertEqual(intervention_config.Delay_Period_Max, 365)
        self.assertDictEqual(intervention_config.Actual_IndividualIntervention_Configs[0], interventions[0].to_schema_dict())

    def test_add_individual_intervention_scheduled_with_multi_iv(self):
        # Test the add_intervention_scheduled with multiple individual interventions without delay
        interventions = [BroadcastEvent(self.campaign, "Test_Event"),
                         SimpleVaccine(self.campaign, waning_config=MapLinear([2010, 2020], [0.9, 0.95]))]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Target 70% of female individuals
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.FEMALE),
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]]),
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct intervention was added to the event coordinator with delay distribution
        multi_interventions = coordinator.Intervention_Config
        self.assertEqual(multi_interventions['class'], 'MultiInterventionDistributor')
        actual_interventions = multi_interventions.Intervention_List
        for i, iv in enumerate(actual_interventions):
            self.assertDictEqual(iv, interventions[i].to_schema_dict())

    def test_add_individual_intervention_scheduled_with_delay_multi_iv(self):
        # Test the add_intervention_scheduled with multiple individual interventions with delay
        interventions = [BroadcastEvent(self.campaign, "Test_Event"),
                         SimpleVaccine(self.campaign, waning_config=MapLinear([2010, 2020], [0.9, 0.95]))]
        uniform_distribution = UniformDistribution(0, 365)
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Target 70% of female individuals
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.FEMALE),
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]]),
                                   delay_distribution=uniform_distribution,
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct intervention was added to the event coordinator with delay distribution
        delayed_intervention_config = coordinator.Intervention_Config
        self.assertEqual(delayed_intervention_config['class'], 'DelayedIntervention')
        self.assertEqual(delayed_intervention_config.Delay_Period_Distribution, 'UNIFORM_DISTRIBUTION')
        self.assertEqual(delayed_intervention_config.Delay_Period_Min, 0)
        self.assertEqual(delayed_intervention_config.Delay_Period_Max, 365)

        actual_interventions = delayed_intervention_config.Actual_IndividualIntervention_Configs
        for i, iv in enumerate(actual_interventions):
            self.assertDictEqual(iv, interventions[i].to_schema_dict())

    def test_add_node_intervention_scheduled(self):
        # Test the add_intervention_scheduled with one node intervention
        interventions = [Outbreak(self.campaign, number_cases_per_node=10)]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   node_ids=[1, 2, 3],
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                        timesteps_between_repetitions=365),
                                   property_restrictions=PropertyRestrictions(node_property_restrictions=[["Risk:High"]]))
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event, node_intervention=True)

        # Verify that the correct intervention was added to the event coordinator
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'Outbreak')
        self.assertEqual(intervention_config.Number_Cases_Per_Node, 10)

    def test_add_node_intervention_scheduled_with_multi_iv(self):
        # Test the add_intervention_scheduled with multiple node interventions
        interventions = [Outbreak(self.campaign, number_cases_per_node=10),
                         Outbreak(self.campaign, number_cases_per_node=30)]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(node_property_restrictions=[["Risk:High"]]))
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event, node_intervention=True)

        # Verify that the correct intervention was added to the event coordinator with delay distribution
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'MultiNodeInterventionDistributor')
        intervention_list = intervention_config.Node_Intervention_List
        for iv, intervention in zip(intervention_list, interventions):
            self.assertDictEqual(iv,
                                 intervention.to_schema_dict())

    def test_add_node_intervention_scheduled_exception(self):
        # Test the add_intervention_scheduled with one node intervention and TargetDemographicsConfig
        interventions = [Outbreak(self.campaign, number_cases_per_node=10)]
        with self.assertRaises(ValueError) as context_1:
            add_intervention_scheduled(campaign=self.campaign,
                                       intervention_list=interventions,
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                           target_gender=TargetGender.FEMALE))
        self.assertTrue('target_demographics_config' in str(context_1.exception))

        # Test the add_intervention_scheduled with one node intervention and targeting_config
        with self.assertRaises(ValueError) as context_2:
            add_intervention_scheduled(campaign=self.campaign,
                                       intervention_list=interventions,
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       targeting_config=~IsPregnant())
        self.assertTrue('targeting_config' in str(context_2.exception))

        # Test the add_intervention_scheduled with one node intervention and individual_property_restrictions
        with self.assertRaises(ValueError) as context_3:
            add_intervention_scheduled(campaign=self.campaign,
                                       intervention_list=interventions,
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       property_restrictions=PropertyRestrictions(individual_property_restrictions=[["Risk:High"]]))
        self.assertTrue('individual_property_restrictions' in str(context_3.exception))

        # Test the add_intervention_scheduled with one node intervention and delay_distribution
        with self.assertRaises(NotImplementedError) as context_4:
            add_intervention_scheduled(campaign=self.campaign,
                                       intervention_list=interventions,
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       delay_distribution=UniformDistribution(0, 365))
        self.assertTrue('delay_distribution' in str(context_4.exception))

    def verify_event_coordinator(self, event, node_intervention=False, default=False):
        coordinator = event.Event_Coordinator_Config
        self.assertEqual(coordinator['class'], 'StandardInterventionDistributionEventCoordinator')
        if node_intervention or default:
            self.assertEqual(coordinator.Demographic_Coverage, 1)
            self.assertEqual(coordinator.Target_Demographic, 'Everyone')
            self.assertEqual(coordinator.Target_Gender, "All")
            self.assertDictEqual(coordinator.Targeting_Config, {})
            if node_intervention:
                self.assertEqual(coordinator.Node_Property_Restrictions, [{'Risk': 'High'}])
                self.assertEqual(coordinator.Timesteps_Between_Repetitions, 365)
                self.assertEqual(coordinator.Number_Repetitions, 2)
            else:
                self.assertEqual(coordinator.Property_Restrictions, [])
                self.assertEqual(coordinator.Node_Property_Restrictions, [])
                self.assertEqual(coordinator.Property_Restrictions_Within_Node, [])
                self.assertEqual(coordinator.Timesteps_Between_Repetitions, -1)
                self.assertEqual(coordinator.Number_Repetitions, 1)
        else:
            self.assertEqual(coordinator.Demographic_Coverage, 0.7)
            self.assertEqual(coordinator.Target_Demographic, 'ExplicitGender')
            self.assertEqual(coordinator.Target_Gender, "Female")
            self.assertEqual(coordinator.Property_Restrictions_Within_Node, [{'Risk': 'High'}])
            self.assertEqual(coordinator.Targeting_Config['class'], 'IsPregnant')
            self.assertEqual(coordinator.Targeting_Config.Is_Equal_To, 0)
            self.assertEqual(coordinator.Timesteps_Between_Repetitions, 365)
            self.assertEqual(coordinator.Number_Repetitions, 2)
        return coordinator

    def verify_campaign_event(self, start_day, start_year, default=False):
        self.assertEqual(len(self.campaign.campaign_dict['Events']), 1)
        event = self.campaign.campaign_dict['Events'][0]
        if not default:
            self.assertEqual(event.Event_Name, "test_event")
            self.assertEqual(event.Nodeset_Config.Node_List, [1, 2, 3])
            self.assertEqual(event.Nodeset_Config['class'], 'NodeSetNodeList')
        else:
            self.assertEqual(event.Nodeset_Config['class'], 'NodeSetAll')
        if start_day is not None:
            self.assertEqual(event.Start_Day, start_day)
            self.assertEqual(event['class'], 'CampaignEvent')
        else:
            self.assertEqual(event.Start_Year, start_year)
            self.assertEqual(event['class'], 'CampaignEventByYear')
        return event


class TestScheduledDistributorMalariaByDay(BaseScheduledDistributorTest, TestMalaria):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_day = 1
        self.start_year = None

    def tearDown(self):
        compare_to_regression_json(self.campaign, filename=f"Malaria_{self._testMethodName}.json")


class TestScheduledDistributorHIVByYear(BaseScheduledDistributorTest, TestHIV):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_day = None
        self.start_year = 1990

    def tearDown(self):
        compare_to_regression_json(self.campaign, filename=f"HIV_{self._testMethodName}.json")


class BaseTriggeredDistributorTest(BaseTestClass):
    def verify_campaign_event(self, start_day, start_year, default=False, event_index=0, num_events=1):
        self.assertEqual(len(self.campaign.campaign_dict['Events']), num_events)
        event = self.campaign.campaign_dict['Events'][event_index]
        if not default:
            self.assertEqual(event.Event_Name, "test_event")
            self.assertEqual(event.Nodeset_Config.Node_List, [1, 2, 3])
            self.assertEqual(event.Nodeset_Config['class'], 'NodeSetNodeList')
        else:
            self.assertEqual(event.Nodeset_Config['class'], 'NodeSetAll')
        if start_day is not None:
            self.assertEqual(event.Start_Day, start_day)
            self.assertEqual(event['class'], 'CampaignEvent')
        else:
            self.assertEqual(event.Start_Year, start_year)
            self.assertEqual(event['class'], 'CampaignEventByYear')
        return event

    def verify_event_coordinator(self, event, default=False):
        coordinator = event.Event_Coordinator_Config
        self.assertEqual(coordinator['class'], 'StandardInterventionDistributionEventCoordinator')
        if default:
            self.assertEqual(coordinator.Timesteps_Between_Repetitions, -1)
            self.assertEqual(coordinator.Number_Repetitions, 1)
        else:
            self.assertEqual(coordinator.Timesteps_Between_Repetitions, -1)
            self.assertEqual(coordinator.Number_Repetitions, 1)
        # Verify that these are the default values no matter what the parameters are.
        self.assertEqual(coordinator.Demographic_Coverage, 1)
        self.assertEqual(coordinator.Target_Demographic, 'Everyone')
        self.assertEqual(coordinator.Target_Gender, "All")
        self.assertEqual(coordinator.Property_Restrictions, [])
        self.assertEqual(coordinator.Node_Property_Restrictions, [])
        self.assertEqual(coordinator.Property_Restrictions_Within_Node, [])
        self.assertDictEqual(coordinator.Targeting_Config, {})
        return coordinator

    def verify_NLHTIV(self, coordinator, triggers_list, default=False, node_intervention=False):
        NLHTIV = coordinator.Intervention_Config
        self.assertEqual(NLHTIV['class'], 'NodeLevelHealthTriggeredIV')
        if default or node_intervention:
            self.assertEqual(NLHTIV.Demographic_Coverage, 1)
            self.assertEqual(NLHTIV.Target_Demographic, 'Everyone')
            self.assertDictEqual(NLHTIV.Targeting_Config, {})
            self.assertEqual(NLHTIV.Property_Restrictions_Within_Node, [])
        else:
            self.assertEqual(NLHTIV.Demographic_Coverage, 0.7)
            self.assertEqual(NLHTIV.Target_Demographic, 'ExplicitAgeRangesAndGender')
            self.assertEqual(NLHTIV.Target_Gender, 'Male')
            self.assertEqual(NLHTIV.Target_Age_Min, 10)
            self.assertEqual(NLHTIV.Target_Age_Max, 20)
            tc = ~IsPregnant()
            self.assertDictEqual(NLHTIV.Targeting_Config, tc.to_simple_dict(self.campaign))
            self.assertEqual(NLHTIV.Property_Restrictions_Within_Node, [{'Risk': 'High'}])

        if default:
            self.assertEqual(NLHTIV.Duration, -1)
        else:
            self.assertEqual(NLHTIV.Duration, 365)

        self.assertEqual(NLHTIV.Trigger_Condition_List, triggers_list)

        return NLHTIV

    def test_add_individual_intervention_triggered_default(self):
        # Test the default parameters for add_intervention_triggered with one individual intervention
        interventions = [BroadcastEvent(self.campaign, "Test_BroadcastEvent")]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   start_day=self.start_day,
                                   start_year=self.start_year)
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year, default=True)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event, default=True)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=True)

        # Verify that the correct intervention was added to the NLHTIV
        intervention_config = NLHTIV.Actual_IndividualIntervention_Config
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_BroadcastEvent')

    def test_add_individual_intervention_triggered(self):
        # Test the add_intervention_triggered with one individual intervention without delay
        interventions = [BroadcastEvent(self.campaign, "Test_BroadcastEvent")]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365,
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.MALE,
                                                                                       target_age_min=10,
                                                                                       target_age_max=20),
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False)

        # Verify that the correct intervention was added to the NLHTIV
        intervention_config = NLHTIV.Actual_IndividualIntervention_Config
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_BroadcastEvent')

    def test_add_individual_intervention_triggered_with_delay(self):
        # Test the add_intervention_triggered with one individual intervention with delay
        interventions = [BroadcastEvent(self.campaign, "Test_BroadcastEvent")]
        exponential_distribution = ExponentialDistribution(10)
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365,
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.MALE,
                                                                                       target_age_min=10,
                                                                                       target_age_max=20),
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   delay_distribution=exponential_distribution,
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False)

        # Verify that the delayed intervention was added to the NLHTIV
        delayed_intervention_config = NLHTIV.Actual_IndividualIntervention_Config
        self.assertEqual(delayed_intervention_config['class'], 'DelayedIntervention')
        self.assertEqual(delayed_intervention_config.Delay_Period_Distribution, 'EXPONENTIAL_DISTRIBUTION')
        self.assertEqual(delayed_intervention_config.Delay_Period_Exponential, 10)

        intervention_config = delayed_intervention_config.Actual_IndividualIntervention_Configs[0]
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_BroadcastEvent')

    def test_add_individual_intervention_triggered_with_delay_multi_iv(self):
        # Test the add_intervention_triggered with multiple individual interventions with delay
        interventions = [BroadcastEvent(self.campaign, "Test_BroadcastEvent"),
                         SimpleVaccine(self.campaign, waning_config=MapLinear([2010, 2020], [0.9, 0.95]))]
        exponential_distribution = ExponentialDistribution(10)
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365,
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.MALE,
                                                                                       target_age_min=10,
                                                                                       target_age_max=20),
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   delay_distribution=exponential_distribution,
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False)

        # Verify that the delayed intervention was added to the NLHTIV
        delayed_intervention = NLHTIV.Actual_IndividualIntervention_Config
        self.assertEqual(delayed_intervention['class'], 'DelayedIntervention')
        self.assertEqual(delayed_intervention.Delay_Period_Distribution, 'EXPONENTIAL_DISTRIBUTION')
        self.assertEqual(delayed_intervention.Delay_Period_Exponential, 10)

        # Verify the MultiInterventionDistributor was added to the delayed_intervention
        actual_intervention_list = delayed_intervention.Actual_IndividualIntervention_Configs

        self.assertEqual(len(actual_intervention_list), 2)
        self.assertEqual(actual_intervention_list[0]['class'], 'BroadcastEvent')
        self.assertEqual(actual_intervention_list[0].Broadcast_Event, 'Test_BroadcastEvent')
        self.assertEqual(actual_intervention_list[1]['class'], 'SimpleVaccine')
        self.assertEqual(actual_intervention_list[1].Waning_Config['class'], 'WaningEffectMapLinear')
        self.assertEqual(actual_intervention_list[1].Waning_Config.Durability_Map.Times, [2010, 2020])
        self.assertEqual(actual_intervention_list[1].Waning_Config.Durability_Map.Values, [0.9, 0.95])

    def test_add_individual_intervention_triggered_with_multi_iv(self):
        # Test the add_intervention_triggered with multiple individual interventions without delay
        interventions = [BroadcastEvent(self.campaign, "Test_BroadcastEvent"),
                         SimpleVaccine(self.campaign, waning_config=MapLinear([2010, 2020], [0.9, 0.95]))]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365,
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.MALE,
                                                                                       target_age_min=10,
                                                                                       target_age_max=20),
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   targeting_config=~IsPregnant())
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False)

        # Verify the MultiInterventionDistributor was added to the NLHTIV
        multi_intervention_config = NLHTIV.Actual_IndividualIntervention_Config
        self.assertEqual(multi_intervention_config['class'], 'MultiInterventionDistributor')

        # Verify that the interventions were added to the MultiInterventionDistributor
        intervention_configs = multi_intervention_config.Intervention_List
        self.assertEqual(len(intervention_configs), 2)
        for i, intervention_config in enumerate(intervention_configs):
            if i == 0:
                self.assertEqual(intervention_config['class'], 'BroadcastEvent')
                self.assertEqual(intervention_config.Broadcast_Event, 'Test_BroadcastEvent')
            else:
                self.assertEqual(intervention_config['class'], 'SimpleVaccine')
                self.assertEqual(intervention_config.Waning_Config['class'], 'WaningEffectMapLinear')
                self.assertEqual(intervention_config.Waning_Config.Durability_Map.Times, [2010, 2020])
                self.assertEqual(intervention_config.Waning_Config.Durability_Map.Values, [0.9, 0.95])

    def test_add_node_intervention_triggered_exception(self):
        # Test the add_intervention_triggered with one node intervention with TargetDemographicsConfig
        interventions = [Outbreak(self.campaign, number_cases_per_node=20)]
        with self.assertRaises(ValueError) as context_1:
            add_intervention_triggered(campaign=self.campaign,
                                       intervention_list=interventions,
                                       triggers_list=["Trigger1", "Trigger2"],
                                       event_name="test_event",
                                       # Apply the event to nodes 1, 2, and 3
                                       node_ids=[1, 2, 3],
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       duration=365,
                                       target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                           target_gender=TargetGender.MALE,
                                                                                           target_age_min=10,
                                                                                           target_age_max=20))
        self.assertTrue('is a node-level intervention, so it will be distributed to nodes' in str(context_1.exception))

        # Test the add_intervention_triggered with one node intervention and individual_property_restrictions
        with self.assertRaises(ValueError) as context_2:
            add_intervention_triggered(campaign=self.campaign,
                                       intervention_list=interventions,
                                       triggers_list=["Trigger1", "Trigger2"],
                                       event_name="test_event",
                                       # Apply the event to nodes 1, 2, and 3
                                       node_ids=[1, 2, 3],
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       duration=365,
                                       property_restrictions=PropertyRestrictions(
                                           individual_property_restrictions=[["Risk:High"]]))
        self.assertTrue('is a node-level intervention, so it will be distributed to nodes' in str(context_2.exception))

        # Test the add_intervention_triggered with one node intervention and targeting_config
        with self.assertRaises(ValueError) as context_3:
            add_intervention_triggered(campaign=self.campaign,
                                       intervention_list=interventions,
                                       triggers_list=["Trigger1", "Trigger2"],
                                       event_name="test_event",
                                       # Apply the event to nodes 1, 2, and 3
                                       node_ids=[1, 2, 3],
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       duration=365,
                                       targeting_config=~IsPregnant())
        self.assertTrue('is a node-level intervention, so it will be distributed to nodes' in str(context_3.exception))

        # Test the add_intervention_triggered with one node intervention and delay_distribution
        with self.assertRaises(NotImplementedError) as context_4:
            add_intervention_triggered(campaign=self.campaign,
                                       intervention_list=interventions,
                                       triggers_list=["Trigger1", "Trigger2"],
                                       event_name="test_event",
                                       # Apply the event to nodes 1, 2, and 3
                                       node_ids=[1, 2, 3],
                                       start_day=self.start_day,
                                       start_year=self.start_year,
                                       duration=365,
                                       delay_distribution=UniformDistribution(0, 365),)
        self.assertTrue('Node-level interventions do not support delay_distribution' in str(context_4.exception))

    def test_add_node_intervention_triggered(self):
        # Test the add_intervention_triggered with one node intervention
        interventions = [Outbreak(self.campaign, number_cases_per_node=20)]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365)
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False, node_intervention=True)

        # Verify that the correct intervention was added to the NLHTIV
        intervention_config = NLHTIV.Actual_NodeIntervention_Config
        self.assertEqual(intervention_config['class'], 'Outbreak')
        self.assertEqual(intervention_config.Number_Cases_Per_Node, 20)

    def test_add_node_intervention_triggered_with_multi_iv(self):
        # Test the add_intervention_triggered with multiple node interventions
        interventions = [Outbreak(self.campaign, number_cases_per_node=20),
                         Outbreak(self.campaign, number_cases_per_node=40)]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365)
        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False, node_intervention=True)

        # Verify that the correct intervention was added to the NLHTIV
        intervention_config = NLHTIV.Actual_NodeIntervention_Config
        self.assertEqual(intervention_config['class'], 'MultiNodeInterventionDistributor')
        intervention_list = intervention_config.Node_Intervention_List
        self.assertEqual(len(intervention_list), 2)
        self.assertEqual(intervention_list[0]['class'], 'Outbreak')
        self.assertEqual(intervention_list[0].Number_Cases_Per_Node, 20)
        self.assertEqual(intervention_list[1]['class'], 'Outbreak')
        self.assertEqual(intervention_list[1].Number_Cases_Per_Node, 40)

    def test_add_multiple_events(self):
        # Test the add_intervention_triggered with multiple node interventions
        interventions = [Outbreak(self.campaign, number_cases_per_node=20),
                         Outbreak(self.campaign, number_cases_per_node=40)]
        add_intervention_triggered(campaign=self.campaign,
                                   intervention_list=interventions,
                                   triggers_list=["Trigger1", "Trigger2"],
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   duration=365)

        # Test add_intervention_scheduled with one individual intervention without delay
        interventions = [BroadcastEvent(self.campaign, "Test_Event")]
        add_intervention_scheduled(campaign=self.campaign,
                                   intervention_list=interventions,
                                   start_day=self.start_day,
                                   start_year=self.start_year,
                                   event_name="test_event",
                                   # Apply the event to nodes 1, 2, and 3
                                   node_ids=[1, 2, 3],
                                   # Target 70% of female individuals
                                   target_demographics_config=TargetDemographicsConfig(demographic_coverage=0.7,
                                                                                       target_gender=TargetGender.FEMALE),
                                   # Repeat the event twice with 365 timesteps between repetitions
                                   repetition_config=RepetitionConfig(number_repetitions=2,
                                                                      timesteps_between_repetitions=365),
                                   # Apply the intervention only to individuals with a "Risk" property of value "High"
                                   property_restrictions=PropertyRestrictions(
                                       individual_property_restrictions=[["Risk:High"]]),
                                   targeting_config=~IsPregnant())

        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year, num_events=2)

        # Verify that the correct event coordinator was added to the event
        coordinator = self.verify_event_coordinator(event)

        # Verify that the correct NLHTIV intervention was added to the event coordinator
        NLHTIV = self.verify_NLHTIV(coordinator, ["Trigger1", "Trigger2"], default=False, node_intervention=True)

        # Verify that the correct intervention was added to the NLHTIV
        intervention_config = NLHTIV.Actual_NodeIntervention_Config
        self.assertEqual(intervention_config['class'], 'MultiNodeInterventionDistributor')
        intervention_list = intervention_config.Node_Intervention_List
        self.assertEqual(len(intervention_list), 2)
        self.assertEqual(intervention_list[0]['class'], 'Outbreak')
        self.assertEqual(intervention_list[0].Number_Cases_Per_Node, 20)
        self.assertEqual(intervention_list[1]['class'], 'Outbreak')
        self.assertEqual(intervention_list[1].Number_Cases_Per_Node, 40)


        # Verify that the correct event was added to the campaign
        event = self.verify_campaign_event(self.start_day, self.start_year, event_index=1, num_events=2)
        # Verify that the correct event coordinator was added to the even
        coordinator = event.Event_Coordinator_Config
        self.assertEqual(coordinator['class'], 'StandardInterventionDistributionEventCoordinator')
        self.assertEqual(coordinator.Demographic_Coverage, 0.7)
        self.assertEqual(coordinator.Target_Demographic, 'ExplicitGender')
        self.assertEqual(coordinator.Target_Gender, "Female")
        self.assertEqual(coordinator.Property_Restrictions_Within_Node, [{'Risk': 'High'}])
        self.assertEqual(coordinator.Targeting_Config['class'], 'IsPregnant')
        self.assertEqual(coordinator.Targeting_Config.Is_Equal_To, 0)
        self.assertEqual(coordinator.Timesteps_Between_Repetitions, 365)
        self.assertEqual(coordinator.Number_Repetitions, 2)
        # Verify that the correct intervention was added to the event coordinator
        intervention_config = coordinator.Intervention_Config
        self.assertEqual(intervention_config['class'], 'BroadcastEvent')
        self.assertEqual(intervention_config.Broadcast_Event, 'Test_Event')



class TestTriggeredDistributorHIVByYear(BaseTriggeredDistributorTest, TestHIV):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_day = None
        self.start_year = 1990

    def tearDown(self):
        compare_to_regression_json(self.campaign, filename=f"HIV_{self._testMethodName}.json")


class TestTriggeredDistributorMalariaByDay(BaseTriggeredDistributorTest, TestMalaria):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_day = 1
        self.start_year = None

    def tearDown(self):
        compare_to_regression_json(self.campaign, filename=f"Malaria_{self._testMethodName}.json")


class TestDistributorMalariaByYear(TestMalaria):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)

    def test_intervention_scheduled(self):
        with self.assertRaises(ValueError) as context:
            add_intervention_scheduled(campaign=self.campaign,
                                       intervention_list=[BroadcastEvent(self.campaign, "Test_BroadcastEvent")],
                                       start_day=None,
                                       start_year=1990,
                                       event_name="test_event",
                                       repetition_config=RepetitionConfig(number_repetitions=2,
                                                                          timesteps_between_repetitions=365))
        self.assertTrue('The start_year is not supported in this disease model, please use start_day' in str(context.exception))

    def test_intervention_triggered(self):
        with self.assertRaises(ValueError) as context:
            add_intervention_triggered(campaign=self.campaign,
                                       intervention_list=[BroadcastEvent(self.campaign, "Test_BroadcastEvent")],
                                       triggers_list=["Trigger1", "Trigger2"],
                                       event_name="test_event",
                                       start_day=None,
                                       start_year=1990,
                                       duration=365)
        self.assertTrue('The start_year is not supported in this disease model, please use start_day' in str(context.exception))


if __name__ == '__main__':
    unittest.main()
