from abc import ABCMeta
from typing import Dict

from emodpy.emod_campaign import EMODCampaign


class IEMODDefault(metaclass=ABCMeta):
    def config(self, erad_path) -> Dict:
        return {}

    def campaign(self) -> Dict:
        return EMODCampaign()

    def demographics(self) -> Dict:
        return {}

    def process_simulation(self, simulation):
        simulation.campaign = self.campaign()

        simulation.config = self.config()
