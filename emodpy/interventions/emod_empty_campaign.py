from emodpy.defaults.iemod_default import IEMODDefault
from emodpy.emod_campaign import EMODCampaign


class EMODEmptyCampaign(IEMODDefault):
    @staticmethod
    def campaign() -> 'EMODCampaign':
        return EMODCampaign.load_from_dict({
            "Campaign_Name": "Empty campaign",
            "Events": [],
            "Use_Defaults": 1
        })
