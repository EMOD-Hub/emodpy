import unittest
import pytest
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import emod_api.campaign as campaign
from emodpy.campaign.common import ValueMap
from emodpy.campaign.waning_config import Box, BoxExponential, Combo, Constant, Exponential, MapLinear, MapLinearAge, \
    MapLinearSeasonal, MapPiecewise, RandomBox
from base_test import TestHIV, TestMalaria, BaseTestClass



class BaseWaningConfigTest(BaseTestClass):
    def test_box(self):
        box = Box(constant_effect=0.8, box_duration=365)
        self.assertEqual(box.initial_effect, 0.8)
        self.assertEqual(box.box_duration, 365)

    def test_box_to_schema_dict(self):
        box = Box(constant_effect=0.8, box_duration=365)
        schema_dict = box.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict.Box_Duration, 365)
        self.assertEqual(schema_dict['class'], "WaningEffectBox")

    def test_box_exponential(self):
        box_exp = BoxExponential(initial_effect=0.8, box_duration=365, decay_time_constant=0.1)
        self.assertEqual(box_exp.initial_effect, 0.8)
        self.assertEqual(box_exp.box_duration, 365)
        self.assertEqual(box_exp.decay_time_constant, 0.1)

    def test_box_exponential_to_schema_dict(self):
        box_exp = BoxExponential(initial_effect=0.8, box_duration=365, decay_time_constant=0.1)
        schema_dict = box_exp.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict.Box_Duration, 365)
        self.assertEqual(schema_dict.Decay_Time_Constant, 0.1)
        self.assertEqual(schema_dict['class'], "WaningEffectBoxExponential")

    def test_combo(self):
        combo = Combo(effect_list=[Constant(constant_effect=0.5),
                                   Exponential(initial_effect=0.3, decay_time_constant=10)])
        self.assertEqual(len(combo.effect_list), 2)
        self.assertIsInstance(combo.effect_list[0], Constant)
        self.assertIsInstance(combo.effect_list[1], Exponential)

    def test_combo_to_schema_dict(self):
        combo = Combo(effect_list=[Constant(constant_effect=0.5),
                                   Exponential(initial_effect=0.3, decay_time_constant=10)])
        schema_dict = combo.to_schema_dict(self.campaign_obj)
        self.assertEqual(len(schema_dict.Effect_List), 2)
        self.assertEqual(schema_dict.Effect_List[0].Initial_Effect, 0.5)
        self.assertEqual(schema_dict.Effect_List[1].Initial_Effect, 0.3)
        self.assertEqual(schema_dict.Effect_List[1].Decay_Time_Constant, 10)
        self.assertEqual(schema_dict['class'], "WaningEffectCombo")

    def test_constant(self):
        constant = Constant(constant_effect=0.8)
        self.assertEqual(constant.initial_effect, 0.8)

    def test_constant_to_schema_dict(self):
        constant = Constant(constant_effect=0.8)
        schema_dict = constant.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict['class'], "WaningEffectConstant")

    def test_exponential(self):
        exponential = Exponential(initial_effect=0.8, decay_time_constant=20)
        self.assertEqual(exponential.initial_effect, 0.8)
        self.assertEqual(exponential.decay_time_constant, 20)

    def test_exponential_to_schema_dict(self):
        exponential = Exponential(initial_effect=0.8, decay_time_constant=20)
        schema_dict = exponential.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict.Decay_Time_Constant, 20)
        self.assertEqual(schema_dict['class'], "WaningEffectExponential")

    def test_map_linear(self):
        map_linear = MapLinear(times=[0, 365], effects=[1, 0.5], expire_at_durability_map_end=True,
                               effect_multiplier=0.2)
        self.assertEqual(map_linear.durability_map, ValueMap(times=[0, 365], values=[1, 0.5]))
        self.assertTrue(map_linear.expire_at_durability_map_end)
        self.assertEqual(map_linear.initial_effect, 0.2)

    def test_map_linear_to_schema_dict(self):
        map_linear = MapLinear(times=[0, 365], effects=[1, 0.5], expire_at_durability_map_end=True,
                               effect_multiplier=0.2)
        schema_dict = map_linear.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Durability_Map, ValueMap(times=[0, 365], values=[1, 0.5]).to_schema_dict(self.campaign_obj))
        self.assertTrue(schema_dict.Expire_At_Durability_Map_End)
        self.assertEqual(schema_dict.Initial_Effect, 0.2)
        self.assertEqual(schema_dict['class'], "WaningEffectMapLinear")

    def test_map_linear_age(self):
        map_linear_age = MapLinearAge(ages=[0, 30], effects=[1, 0.5],
                                      effect_multiplier=0.5)
        self.assertEqual(map_linear_age.durability_map, ValueMap(times=[0, 30], values=[1, 0.5]))
        self.assertEqual(map_linear_age.initial_effect, 0.5)

    def test_map_linear_age_to_schema_dict(self):
        map_linear_age = MapLinearAge(ages=[0, 30], effects=[1, 0.5],
                                      effect_multiplier=0.5)
        schema_dict = map_linear_age.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Durability_Map, ValueMap(times=[0, 30], values=[1, 0.5]).to_schema_dict(self.campaign_obj))
        self.assertEqual(schema_dict.Initial_Effect, 0.5)
        self.assertEqual(schema_dict['class'], "WaningEffectMapLinearAge")

    def test_map_linear_seasonal(self):
        map_linear_seasonal = MapLinearSeasonal(times=[0, 180, 365], effects=[1, 0.7, 0.5], effect_multiplier=0.9)
        self.assertEqual(map_linear_seasonal.durability_map, ValueMap(times=[0, 180, 365], values=[1, 0.7, 0.5]))
        self.assertEqual(map_linear_seasonal.initial_effect, 0.9)

    def test_map_linear_seasonal_to_schema_dict(self):
        map_linear_seasonal = MapLinearSeasonal(times=[0, 180, 365], effects=[1, 0.7, 0.5], effect_multiplier=0.9)
        schema_dict = map_linear_seasonal.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Durability_Map, ValueMap(times=[0, 180, 365], values=[1, 0.7, 0.5]).to_schema_dict(self.campaign_obj))
        self.assertEqual(schema_dict.Initial_Effect, 0.9)
        self.assertEqual(schema_dict['class'], "WaningEffectMapLinearSeasonal")

    def test_map_piecewise(self):
        map_piecewise = MapPiecewise(days=[0, 365], effects=[1, 0.5], effect_multiplier=0.8, expire_at_durability_map_end=True)
        self.assertEqual(map_piecewise.durability_map, ValueMap(times=[0, 365], values=[1, 0.5]))
        self.assertTrue(map_piecewise.expire_at_durability_map_end)
        self.assertEqual(map_piecewise.initial_effect, 0.8)

    def test_map_piecewise_to_schema_dict(self):
        map_piecewise = MapPiecewise(days=[0, 365], effects=[1, 0.5], effect_multiplier=0.8, expire_at_durability_map_end=True)
        schema_dict = map_piecewise.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Durability_Map, ValueMap(times=[0, 365], values=[1, 0.5]).to_schema_dict(self.campaign_obj))
        self.assertTrue(schema_dict.Expire_At_Durability_Map_End)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict['class'], "WaningEffectMapPiecewise")

    def test_random_box(self):
        random_box = RandomBox(constant_effect=0.8, exponential_discard_time=60)
        self.assertEqual(random_box.initial_effect, 0.8)
        self.assertEqual(random_box.expected_discard_time, 60)

    def test_random_box_to_schema_dict(self):
        random_box = RandomBox(constant_effect=0.8, exponential_discard_time=60)
        schema_dict = random_box.to_schema_dict(self.campaign_obj)
        self.assertEqual(schema_dict.Initial_Effect, 0.8)
        self.assertEqual(schema_dict.Expected_Discard_Time, 60)
        self.assertEqual(schema_dict['class'], "WaningEffectRandomBox")


@pytest.mark.emod
class TestWaningConfigHIV(TestHIV, BaseWaningConfigTest):

    def setUp(self):
        TestHIV().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)


@pytest.mark.emod
class TestWaningConfigMalaria(TestMalaria, BaseWaningConfigTest):
    def setUp(self):
        TestHIV().setUp()
        self.campaign_obj = campaign
        self.campaign_obj.set_schema(self.schema_path)


if __name__ == '__main__':
    unittest.main()
