from typing import List

from emod_api.demographics.demographics import Demographics as EMODAPIDemographics
from emod_api.demographics.node import Node
from emodpy.utils.distributions import UniformDistribution


class Demographics(EMODAPIDemographics):
    PYROGENIC_THRESHOLD = 'PYROGENIC_THRESHOLD'
    CYTOKINE_KILLING = 'CYTOKINE_KILLING'

    def __init__(self, nodes: List[Node], default_node: Node, idref: str = "Gridded world grump2.5arcmin"):
        # Forces emodpy-layer Demographics instantiation to use Node object-route for default node . Cannot use
        # the old self.raw dict representation of a default node.
        super().__init__(nodes=nodes, default_node=default_node, idref=idref)
        if default_node is None:
            age_distribution = UniformDistribution(uniform_min=0, uniform_max=18250)
            self.set_age_distribution(distribution=age_distribution)

    @property
    def raw(self):
        raise AttributeError("raw is not a valid attribute for Demographics objects")

    @raw.setter
    def raw(self, value):
        raise AttributeError("raw is not a valid attribute for Demographics objects")
