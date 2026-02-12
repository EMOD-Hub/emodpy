from emod_api.demographics.node import Node
from emod_api.demographics.overlay_node import OverlayNode
from emod_api.demographics.properties_and_attributes import (IndividualAttributes, IndividualProperties,
                                                             IndividualProperty, NodeAttributes)

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution

from emodpy.demographics.demographics import Demographics

# __all_exports: A list of classes that are intended to be exported from this module.
__all_exports = [
    Node,
    OverlayNode,
    IndividualAttributes,
    IndividualProperties,
    IndividualProperty,
    NodeAttributes,
    AgeDistribution,
    FertilityDistribution,
    MortalityDistribution,
    SusceptibilityDistribution,
    Demographics
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
