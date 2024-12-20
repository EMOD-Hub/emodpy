import os
import sys
from sys import argv
from idmtools.analysis.analyze_manager import AnalyzeManager
from idmtools.core import ItemType
from idmtools.core.platform_factory import Platform
from emodpy.analyzers.population_analyzer import PopulationAnalyzer

sys.path.append(os.path.dirname(__file__))


if __name__ == "__main__":
    platform = Platform('COMPS2')

    analyzers = [PopulationAnalyzer()]
    if len(sys.argv) > 1:
        expid = []
        expid.append((argv[1], ItemType.EXPERIMENT))
        expid.append((argv[2], ItemType.EXPERIMENT))
    else:
        expid = [('8bb8ae8f-793c-ea11-a2be-f0921c167861', ItemType.EXPERIMENT),
                 ('4ea96af7-1549-ea11-a2be-f0921c167861', ItemType.EXPERIMENT)]
    am = AnalyzeManager(platform=platform, ids=expid, analyzers=analyzers)
    am.analyze()
