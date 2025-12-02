from typing import List

from emod_api.demographics.demographics import Demographics as EMODAPIDemographics
from emod_api.demographics.node import Node
from emodpy.utils.distributions import UniformDistribution


class Demographics(EMODAPIDemographics):
    # TODO: move to emodpy-malaria as only it uses these for innate immune distributions
    # PYROGENIC_THRESHOLD = 'PYROGENIC_THRESHOLD'
    # CYTOKINE_KILLING = 'CYTOKINE_KILLING'

    def __init__(self, nodes: List[Node], default_node: Node, idref: str = "Gridded world grump2.5arcmin"):
        # Forces emodpy-layer Demographics instantiation to use Node object-route for default node . Cannot use
        # the old self.raw dict representation of a default node.
        super().__init__(nodes=nodes, default_node=default_node, idref=idref)

    @property
    def raw(self):
        raise AttributeError("raw is not a valid attribute for Demographics objects")

    @raw.setter
    def raw(self, value):
        raise AttributeError("raw is not a valid attribute for Demographics objects")
