from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.constant_distribution import ConstantDistribution
from emod_api.utils.distributions.exponential_distribution import ExponentialDistribution
from emod_api.utils.distributions.uniform_distribution import UniformDistribution
from emod_api.utils.distributions.gaussian_distribution import GaussianDistribution
from emod_api.utils.distributions.poisson_distribution import PoissonDistribution
from emod_api.utils.distributions.log_normal_distribution import LogNormalDistribution
from emod_api.utils.distributions.weibull_distribution import WeibullDistribution
from emod_api.utils.distributions.dual_constant_distribution import DualConstantDistribution
from emod_api.utils.distributions.dual_exponential_distribution import DualExponentialDistribution
from emod_api.utils.distributions.bimodal_distribution import BimodalDistribution


# __all_exports: A list of classes that are intended to be exported from this module.
__all_exports = [
    BaseDistribution,
    ConstantDistribution,
    ExponentialDistribution,
    UniformDistribution,
    GaussianDistribution,
    PoissonDistribution,
    LogNormalDistribution,
    WeibullDistribution,
    DualConstantDistribution,
    DualExponentialDistribution,
    BimodalDistribution,
]

# The following loop sets the __module__ attribute of each class in __all_exports to the name of the current module.
# This is done to ensure that when these classes are imported from this module, their __module__ attribute correctly
# reflects their source module.

for _ in __all_exports:
    _.__module__ = __name__

# __all__: A list that defines the public interface of this module.
# This is essential to ensure that Sphinx builds documentation for these classes, including those that are imported
# from emodpy.
# It contains the names of all the classes that should be accessible when this module is imported using the syntax
# 'from module import *'.
# Here, it is set to the names of all classes in __all_exports.

__all__ = [_.__name__ for _ in __all_exports]
