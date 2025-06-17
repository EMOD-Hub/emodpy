import sys
from pathlib import Path
import unittest
import pytest
from emod_api import schema_to_class as s2c
from emod_api import campaign

from emodpy.campaign.common import (TargetGender, TargetDemographicsConfig, MAX_AGE_YEARS,
                                    RepetitionConfig, PropertyRestrictions, ValueMap,
                                    CommonInterventionParameters)

tests_directory = Path(__file__).resolve().parent
sys.path.append(str(tests_directory))

from base_test import TestHIV, TestMalaria, BaseTestClass


class BaseDemographicsConfigTest(BaseTestClass):
    def test_init(self):
        demo_config = TargetDemographicsConfig()
        self.assertEqual(demo_config.demographic_coverage, 1.0)
        self.assertEqual(demo_config.target_age_min, 0)
        self.assertEqual(demo_config.target_age_max, MAX_AGE_YEARS)
        self.assertEqual(demo_config.target_gender, TargetGender.ALL)
        self.assertEqual(demo_config.target_residents_only, False)

    def test_set_target_demographics_default(self):
        demo_config = TargetDemographicsConfig()
        campaign_object = s2c.get_class_with_defaults('NodeLevelHealthTriggeredIV', self.schema_path)
        demo_config._set_target_demographics(campaign_object)
        self.assertEqual(campaign_object.Demographic_Coverage, 1.0)
        self.assertEqual(campaign_object.Target_Residents_Only, False)
        self.assertEqual(campaign_object.Target_Demographic, "Everyone")

    def test_set_target_demographics_age(self):
        demo_config = TargetDemographicsConfig(demographic_coverage=0.6, target_age_min=15, target_age_max=49)
        campaign_object = s2c.get_class_with_defaults('NodeLevelHealthTriggeredIV', self.schema_path)
        demo_config._set_target_demographics(campaign_object)
        self.assertEqual(campaign_object.Demographic_Coverage, 0.6)
        self.assertEqual(campaign_object.Target_Residents_Only, False)
        self.assertEqual(campaign_object.Target_Age_Min, 15)
        self.assertEqual(campaign_object.Target_Age_Max, 49)
        self.assertEqual(campaign_object.Target_Demographic, 'ExplicitAgeRanges')

    def test_set_target_demographics_gender(self):
        demo_config = TargetDemographicsConfig(demographic_coverage=0.9, target_gender=TargetGender.FEMALE)
        campaign_object = s2c.get_class_with_defaults('NodeLevelHealthTriggeredIV', self.schema_path)
        demo_config._set_target_demographics(campaign_object)
        self.assertEqual(campaign_object.Demographic_Coverage, 0.9)
        self.assertEqual(campaign_object.Target_Residents_Only, False)
        self.assertEqual(campaign_object.Target_Gender, TargetGender.FEMALE.value)
        self.assertEqual(campaign_object.Target_Demographic, 'ExplicitGender')

    def test_set_target_demographics_age_gender(self):
        demo_config = TargetDemographicsConfig(demographic_coverage=0.8, target_age_min=10, target_age_max=30, target_gender=TargetGender.MALE)
        campaign_object = s2c.get_class_with_defaults('NodeLevelHealthTriggeredIV', self.schema_path)
        demo_config._set_target_demographics(campaign_object)
        self.assertEqual(campaign_object.Demographic_Coverage, 0.8)
        self.assertEqual(campaign_object.Target_Residents_Only, False)
        self.assertEqual(campaign_object.Target_Age_Min, 10)
        self.assertEqual(campaign_object.Target_Age_Max, 30)
        self.assertEqual(campaign_object.Target_Gender, TargetGender.MALE.value)
        self.assertEqual(campaign_object.Target_Demographic, 'ExplicitAgeRangesAndGender')

    def test_set_target_demographics_residents_only(self):
        demo_config = TargetDemographicsConfig(demographic_coverage=0.7, target_residents_only=True)
        campaign_object = s2c.get_class_with_defaults('NodeLevelHealthTriggeredIV', self.schema_path)
        demo_config._set_target_demographics(campaign_object)
        self.assertEqual(campaign_object.Demographic_Coverage, 0.7)
        self.assertEqual(campaign_object.Target_Residents_Only, True)
        self.assertEqual(campaign_object.Target_Demographic, 'Everyone')



class TestDemographicsConfigHIV(TestHIV, BaseDemographicsConfigTest):
    pass



class TestDemographicsConfigMalaria(TestMalaria, BaseDemographicsConfigTest):
    pass


class BaseTestRepetitionConfigTest(BaseTestClass):
    def test_init(self):
        with self.assertWarns(Warning) as context:
            repetition_config = RepetitionConfig()
            self.assertEqual(repetition_config.number_repetitions, 1)
            self.assertEqual(repetition_config.timesteps_between_repetitions, None)
        self.assertTrue("the event will not be repeated" in str(context.warning))

    def test_set_repetitions(self):
        repetition_config = RepetitionConfig(number_repetitions=3, timesteps_between_repetitions=5)
        campaign_object = s2c.get_class_with_defaults('StandardEventCoordinator', self.schema_path)
        repetition_config._set_repetitions(campaign_object)
        self.assertEqual(campaign_object["Number_Repetitions"], 3)
        self.assertEqual(campaign_object["Timesteps_Between_Repetitions"], 5)

    def test_set_repetitions_infinity(self):
        repetition_config = RepetitionConfig(infinite_repetitions=True, timesteps_between_repetitions=30)
        campaign_object = s2c.get_class_with_defaults('StandardEventCoordinator', self.schema_path)
        repetition_config._set_repetitions(campaign_object)
        self.assertEqual(campaign_object["Number_Repetitions"], -1)
        self.assertEqual(campaign_object["Timesteps_Between_Repetitions"], 30)

    def test_set_repetitions_exception_1(self):
        with self.assertRaises(ValueError) as context:
            RepetitionConfig(number_repetitions=2)
        self.assertTrue("timesteps_between_repetitions must be set" in str(context.exception))

    def test_set_repetitions_exception_2(self):
        with self.assertRaises(ValueError) as context:
            RepetitionConfig(infinite_repetitions=True)
        self.assertTrue("timesteps_between_repetitions must be set" in str(context.exception))

    def test_set_repetitions_exception_3(self):
        with self.assertRaises(ValueError) as context:
            RepetitionConfig(infinite_repetitions=True, timesteps_between_repetitions=-1)
        self.assertTrue("timesteps_between_repetitions is set to a non positive value" in str(context.exception))

    def test_set_repetitions_exception_4(self):
        with self.assertRaises(ValueError) as context:
            RepetitionConfig(number_repetitions=2, timesteps_between_repetitions=0)
        self.assertTrue("timesteps_between_repetitions is set to a non positive value" in str(context.exception))



class TestRepetitionConfigHIV(TestHIV, BaseTestRepetitionConfigTest):
    pass



class TestRepetitionConfigMalaria(TestMalaria, BaseTestRepetitionConfigTest):
    pass


class BasePropertyRestrictionsTest(BaseTestClass):
    def test_init(self):
        with self.assertWarns(Warning) as context:
            property_restrictions = PropertyRestrictions()
            self.assertIsNone(property_restrictions.individual_property_restrictions)
            self.assertIsNone(property_restrictions.node_property_restrictions)
        self.assertTrue("No property restrictions are provided." in str(context.warning))

    def test_individual_space(self):
        campaign_object = s2c.get_class_with_defaults('ReferenceTrackingEventCoordinator', self.schema_path)
        property_restrictions = PropertyRestrictions(
            individual_property_restrictions=[[" Risk : High ", " InterventionStatus : ARTStaging "]])
        property_restrictions._set_property_restrictions(campaign_object)
        self.assertEqual(campaign_object["Property_Restrictions"], [])
        self.assertEqual(campaign_object["Property_Restrictions_Within_Node"],
                         [{"Risk": "High", "InterventionStatus": "ARTStaging"}])
        self.assertEqual(campaign_object["Node_Property_Restrictions"], [])

    def test_individual_and_logic(self):
        campaign_object = s2c.get_class_with_defaults('ReferenceTrackingEventCoordinator', self.schema_path)
        property_restrictions = PropertyRestrictions(
            individual_property_restrictions=[["Risk:HIGH", "InterventionStatus:ARTStaging"]])
        property_restrictions._set_property_restrictions(campaign_object)
        self.assertEqual(campaign_object["Property_Restrictions"], [])
        self.assertEqual(campaign_object["Property_Restrictions_Within_Node"],
                         [{"Risk": "HIGH", "InterventionStatus": "ARTStaging"}])
        self.assertEqual(campaign_object["Node_Property_Restrictions"], [])

    def test_individual_and_or_logic(self):
        campaign_object = s2c.get_class_with_defaults('ReferenceTrackingEventCoordinator', self.schema_path)
        property_restrictions = PropertyRestrictions(
            individual_property_restrictions=[["Risk:HIGH", "InterventionStatus:ARTStaging"],
                                              ["Risk:MEDIUM", "InterventionStatus:ARTStaging"]])
        property_restrictions._set_property_restrictions(campaign_object)
        self.assertEqual(campaign_object["Property_Restrictions"], [])
        self.assertEqual(campaign_object["Property_Restrictions_Within_Node"],
                         [{"Risk": "HIGH", "InterventionStatus": "ARTStaging"},
                          {"Risk": "MEDIUM", "InterventionStatus": "ARTStaging"}])
        self.assertEqual(campaign_object["Node_Property_Restrictions"], [])

    def test_node(self):
        campaign_object = s2c.get_class_with_defaults('ReferenceTrackingEventCoordinator', self.schema_path)
        property_restrictions = PropertyRestrictions(
            node_property_restrictions=[["Risk:MEDIUM", "Place:URBAN"], ["Risk:LOW", "Place:RURAL"]])
        property_restrictions._set_property_restrictions(campaign_object)
        self.assertEqual(campaign_object["Property_Restrictions"], [])
        self.assertEqual(campaign_object["Property_Restrictions_Within_Node"], [])
        self.assertEqual(campaign_object["Node_Property_Restrictions"],
                         [{"Risk": "MEDIUM", "Place": "URBAN"},
                          {"Risk": "LOW", "Place": "RURAL"}])

    def test_exception_invalid_restriction(self):
        with self.assertRaises(ValueError) as context:
            PropertyRestrictions(individual_property_restrictions=[["'Risk':'HIGH'"]])
        self.assertTrue("should be strings that represent dictionaries key:value pairs with at least one alphanumeric "
                        "character before and after ':'" in str(context.exception))

    def test_exception_invalid_restriction_2(self):
        with self.assertRaises(ValueError) as context:
            PropertyRestrictions(individual_property_restrictions=[['Risk HIGH']])
        self.assertTrue("should be strings that represent dictionaries key:value pairs with at least one alphanumeric "
                        "character before and after ':'" in str(context.exception))

    def test_exception_invalid_restriction_3(self):
        with self.assertRaises(ValueError) as context:
            PropertyRestrictions(individual_property_restrictions=[{'Risk':'HIGH'}])
        self.assertTrue("The individual_property_restrictions should be a 2D list" in str(context.exception))


class TestPropertyRestrictionsHIV(TestHIV, BasePropertyRestrictionsTest):
    pass


class TestPropertyRestrictionsMalaria(TestMalaria, BasePropertyRestrictionsTest):
    pass


class BaseValueMapTest(BaseTestClass):
    def test_value_map(self):
        value_map = ValueMap([1995, 2005], [10, 20])
        self.assertEqual(value_map.to_schema_dict(self.campaign_obj).Times, [1995, 2005])
        self.assertEqual(value_map.to_schema_dict(self.campaign_obj).Values, [10, 20])


class TestValueMapHIV(TestHIV, BaseValueMapTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)
    pass


class TestValueMapMalaria(TestMalaria, BaseValueMapTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)
    pass


class BaseCommonInterventionParametersTest(BaseTestClass):
    def test_init_default(self):
        common_intervention_parameters = CommonInterventionParameters()
        self.assertEqual(common_intervention_parameters.intervention_name, None)
        self.assertEqual(common_intervention_parameters.cost, None)
        self.assertEqual(common_intervention_parameters.disqualifying_properties, None)
        self.assertEqual(common_intervention_parameters.new_property_value, None)
        self.assertEqual(common_intervention_parameters.dont_allow_duplicates, None)

    def test_init(self):
        common_intervention_parameters = CommonInterventionParameters(intervention_name="Intervention1", cost=100,
                                                                      disqualifying_properties=["Risk:HIGH", "Place:URBAN"],
                                                                      new_property_value="Risk:HIGH",
                                                                      dont_allow_duplicates=True)
        self.assertEqual(common_intervention_parameters.intervention_name, "Intervention1")
        self.assertEqual(common_intervention_parameters.cost, 100)
        self.assertEqual(common_intervention_parameters.disqualifying_properties, ["Risk:HIGH", "Place:URBAN"])
        self.assertEqual(common_intervention_parameters.new_property_value, "Risk:HIGH")
        self.assertEqual(common_intervention_parameters.dont_allow_duplicates, True)


class TestCommonInterventionParametersHIV(TestHIV, BaseCommonInterventionParametersTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)
    pass


class TestCommonInterventionParametersMalaria(TestMalaria, BaseCommonInterventionParametersTest):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)
    pass


if __name__ == '__main__':
    unittest.main()
