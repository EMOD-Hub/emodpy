import unittest
from emodpy.utils.distributions import (ConstantDistribution, UniformDistribution, GaussianDistribution,
                                        ExponentialDistribution, PoissonDistribution, LogNormalDistribution,
                                        DualConstantDistribution, WeibullDistribution, DualExponentialDistribution,
                                        BimodalDistribution, BaseDistribution)
from emodpy.utils.emod_enum import DistributionType

import pytest

demographics_distribution_flag_map = {
    DistributionType.CONSTANT_DISTRIBUTION: 0,
    DistributionType.UNIFORM_DISTRIBUTION: 1,
    DistributionType.GAUSSIAN_DISTRIBUTION: 2,
    DistributionType.EXPONENTIAL_DISTRIBUTION: 3,
    DistributionType.POISSON_DISTRIBUTION: 4,
    DistributionType.LOG_NORMAL_DISTRIBUTION: 5,
    DistributionType.BIMODAL_DISTRIBUTION: 6,
    DistributionType.WEIBULL_DISTRIBUTION: 7}

"""
Distributions are tested against the schema in test_interventions.py
"""

@pytest.mark.emod
class TestDistributions(unittest.TestCase):
    def is_constant_distribution(self, cd, value):
        self.assertTrue(isinstance(cd, ConstantDistribution))
        self.assertEqual(cd.value, value)

    def test_constant_distribution(self):
        cd = ConstantDistribution(5)
        self.is_constant_distribution(cd, 5)
        self.assertTrue(isinstance(cd, BaseDistribution))
        cd2 = ConstantDistribution(value=15)
        self.is_constant_distribution(cd2, 15)
        cd2.value = 10
        self.is_constant_distribution(cd2, 10)
        self.is_constant_distribution(cd, 5)

    def test_constant_distribution_get_demo_distribution(self):
        cd = ConstantDistribution(1)
        self.assertEqual(cd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.CONSTANT_DISTRIBUTION],
                          "value1": 1,
                          "value2": None})

    def is_uniform_distribution(self, ud, min_value, max_value):
        self.assertTrue(isinstance(ud, UniformDistribution))
        self.assertEqual(ud.uniform_min, min_value)
        self.assertEqual(ud.uniform_max, max_value)

    def test_uniform_distribution(self):
        ud = UniformDistribution(0, 10)
        self.is_uniform_distribution(ud, 0, 10)
        ud2 = UniformDistribution(uniform_min=5, uniform_max=15)
        self.is_uniform_distribution(ud2, 5, 15)
        ud2.uniform_min = 1
        ud2.uniform_max = 2
        self.is_uniform_distribution(ud2, 1, 2)
        self.is_uniform_distribution(ud, 0, 10)

    def test_uniform_distribution_get_demo_distribution(self):
        ud = UniformDistribution(0, 10)
        self.assertEqual(ud.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.UNIFORM_DISTRIBUTION],
                          "value1": 0,
                          "value2": 10})

    def is_gaussian_distribution(self, gd, mean, std_dev):
        self.assertTrue(isinstance(gd, GaussianDistribution))
        self.assertEqual(gd.mean, mean)
        self.assertEqual(gd.std_dev, std_dev)

    def test_gaussian_distribution(self):
        gd = GaussianDistribution(0, 1)
        self.is_gaussian_distribution(gd, 0, 1)
        gd2 = GaussianDistribution(mean=5, std_dev=2)
        self.is_gaussian_distribution(gd2, 5, 2)
        gd2.mean = 10
        gd2.std_dev = 3
        self.is_gaussian_distribution(gd2, 10, 3)
        self.is_gaussian_distribution(gd, 0, 1)

    def test_gaussian_distribution_get_demo_distribution(self):
        gd = GaussianDistribution(20, 0.5)
        self.assertEqual(gd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.GAUSSIAN_DISTRIBUTION],
                          "value1": 20,
                          "value2": 0.5})

    def is_exponential_distribution(self, ed, mean):
        self.assertTrue(isinstance(ed, ExponentialDistribution))
        self.assertEqual(ed.mean, mean)

    def test_exponential_distribution(self):
        ed = ExponentialDistribution(1)
        self.is_exponential_distribution(ed, 1)
        ed2 = ExponentialDistribution(mean=2)
        self.is_exponential_distribution(ed2, 2)
        ed2.mean = 3
        self.is_exponential_distribution(ed2, 3)
        self.is_exponential_distribution(ed, 1)

    def test_exponential_distribution_get_demo_distribution(self):
        ed = ExponentialDistribution(1)
        self.assertEqual(ed.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.EXPONENTIAL_DISTRIBUTION],
                          "value1": 1,
                          "value2": None})

    def is_poisson_distribution(self, pd, mean):
        self.assertTrue(isinstance(pd, PoissonDistribution))
        self.assertEqual(pd.mean, mean)

    def test_poisson_distribution(self):
        pd = PoissonDistribution(1)
        self.is_poisson_distribution(pd, 1)
        pd2 = PoissonDistribution(mean=2)
        self.is_poisson_distribution(pd2, 2)
        pd2.mean = 3
        self.is_poisson_distribution(pd2, 3)
        self.is_poisson_distribution(pd, 1)

    def test_poisson_distribution_get_demo_distribution(self):
        pd = PoissonDistribution(4)
        self.assertEqual(pd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.POISSON_DISTRIBUTION],
                          "value1": 4,
                          "value2": None})

    def is_log_normal_distribution(self, lnd, mean, std_dev):
        self.assertTrue(isinstance(lnd, LogNormalDistribution))
        self.assertEqual(lnd.mean, mean)
        self.assertEqual(lnd.std_dev, std_dev)

    def test_log_normal_distribution(self):
        lnd = LogNormalDistribution(0, 1)
        self.is_log_normal_distribution(lnd, 0, 1)
        lnd2 = LogNormalDistribution(mean=2, std_dev=3)
        self.is_log_normal_distribution(lnd2, 2, 3)
        lnd2.mean = 4
        lnd2.std_dev = 5
        self.is_log_normal_distribution(lnd2, 4, 5)
        self.is_log_normal_distribution(lnd, 0, 1)

    def test_log_normal_distribution_get_demo_distribution(self):
        lnd = LogNormalDistribution(2, 0.8)
        self.assertEqual(lnd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.LOG_NORMAL_DISTRIBUTION],
                          "value1": 2,
                          "value2": 0.8})

    def is_dual_constant_distribution(self, dcd, proportion, constant):
        self.assertTrue(isinstance(dcd, DualConstantDistribution))
        self.assertEqual(dcd.proportion, proportion)
        self.assertEqual(dcd.constant, constant)

    def test_dual_constant_distribution(self):
        dcd = DualConstantDistribution(0.2, 5)
        self.is_dual_constant_distribution(dcd, 0.2, 5)
        dcd2 = DualConstantDistribution(proportion=0.3, constant=10)
        self.is_dual_constant_distribution(dcd2, 0.3, 10)
        dcd2.proportion = 0.4
        dcd2.constant = 15
        self.is_dual_constant_distribution(dcd2, 0.4, 15)
        self.is_dual_constant_distribution(dcd, 0.2, 5)

    def test_dual_constant_distribution_get_demo_distribution(self):
        with self.assertRaises(NotImplementedError) as context:
            dcd = DualConstantDistribution(0.2, 5)
            dcd.get_demographic_distribution_parameters()
        self.assertTrue("DualConstantDistribution does not support demographic distribution" in str(context.exception))

    def is_weibull_distribution(self, wd, kappa, lambd):
        self.assertTrue(isinstance(wd, WeibullDistribution))
        self.assertEqual(wd.weibull_kappa, kappa)
        self.assertEqual(wd.weibull_lambda, lambd)

    def test_weibull_distribution(self):
        wd = WeibullDistribution(1, 2)
        self.is_weibull_distribution(wd, 1, 2)
        wd2 = WeibullDistribution(weibull_kappa=3, weibull_lambda=4)
        self.is_weibull_distribution(wd2, 3, 4)
        wd2.weibull_kappa = 5
        wd2.weibull_lambda = 6
        self.is_weibull_distribution(wd2, 5, 6)
        self.is_weibull_distribution(wd, 1, 2)

    def test_weibull_distribution_get_demo_distribution(self):
        wd = WeibullDistribution(0.9, 3)
        self.assertEqual(wd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.WEIBULL_DISTRIBUTION],
                          "value1": 3,
                          "value2": 0.9})

    def is_dual_exponential_distribution(self, ded, proportion, mean_1, mean_2):
        self.assertTrue(isinstance(ded, DualExponentialDistribution))
        self.assertEqual(ded.proportion, proportion)
        self.assertEqual(ded.mean_1, mean_1)
        self.assertEqual(ded.mean_2, mean_2)

    def test_dual_exponential_distribution(self):
        ded = DualExponentialDistribution(0.2, 1, 2)
        self.is_dual_exponential_distribution(ded, 0.2, 1, 2)
        ded2 = DualExponentialDistribution(proportion=0.3, mean_1=3, mean_2=4)
        self.is_dual_exponential_distribution(ded2, 0.3, 3, 4)
        ded2.proportion = 0.4
        ded2.mean_1 = 5
        ded2.mean_2 = 6
        self.is_dual_exponential_distribution(ded2, 0.4, 5, 6)
        self.is_dual_exponential_distribution(ded, 0.2, 1, 2)

    def test_dual_exponential_distribution_get_demo_distribution(self):
        with self.assertRaises(NotImplementedError) as context:
            ded = DualExponentialDistribution(0.2, 1, 2)
            ded.get_demographic_distribution_parameters()
        self.assertTrue("DualExponentialDistribution does not support demographic distribution" in str(context.exception))

    def is_bimodal_distribution(self, bd, proportion, constant):
        self.assertTrue(isinstance(bd, BimodalDistribution))
        self.assertEqual(bd.proportion, proportion)
        self.assertEqual(bd.constant, constant)

    def test_bimodal_distribution(self):
        bd = BimodalDistribution(0.2, 1)
        self.is_bimodal_distribution(bd, 0.2, 1)
        bd2 = BimodalDistribution(proportion=0.3, constant=3)
        self.is_bimodal_distribution(bd2, 0.3, 3)
        bd2.proportion = 0.4
        bd2.constant = 5
        self.is_bimodal_distribution(bd2, 0.4, 5)
        self.is_bimodal_distribution(bd, 0.2, 1)

    def test_bimodal_distribution_get_demo_distribution(self):
        bd = BimodalDistribution(0.8, 5)
        self.assertEqual(bd.get_demographic_distribution_parameters(),
                         {"flag": demographics_distribution_flag_map[DistributionType.BIMODAL_DISTRIBUTION],
                          "value1": 0.8,
                          "value2": 5})


if __name__ == '__main__':
    unittest.main()
