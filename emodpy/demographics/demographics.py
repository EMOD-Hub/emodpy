from typing import List

from emod_api.demographics.demographics import Demographics as EMODAPIDemographics
from emod_api.demographics.node import Node


class Demographics(EMODAPIDemographics):

    def __init__(self, nodes: List[Node], default_node: Node = None, idref: str = None, set_defaults: bool = True):
        super().__init__(nodes=nodes, default_node=default_node, idref=idref, set_defaults=set_defaults)

    # Forces emodpy-layer Demographics instantiation to use Node object-route for default node . Cannot use
    # the old self.raw dict representation of a default node.

    @property
    def raw(self):
        raise AttributeError("raw is not a valid attribute for Demographics objects")

    @raw.setter
    def raw(self, value):
        raise AttributeError("raw is not a valid attribute for Demographics objects")
