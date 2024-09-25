#********************************************************************************
#
# Python 3.6.0
#
#********************************************************************************

import os, sys, shutil, time, json

from builder_config         import configBuilder
from builder_demographics   import demographicsBuilder
from builder_campaign       import campaignBuilder

ext_py_path = os.path.join('Assets','site_packages')
if(ext_py_path not in sys.path):
  sys.path.append(ext_py_path)

#*******************************************************************************

def application(cFileName=''):


  # Read index of simulation parameter set
  with open('idxStrFile.txt') as fid01:
    simIdx = int(fid01.readline())


  # Read parameter dictionary, select appropriate index
  with open(os.path.join('Assets','param_dict.json')) as fid01:
    param_dict = json.load(fid01)
  var_params = {keyval:param_dict[keyval][simIdx]
                  for keyval in param_dict if type(param_dict[keyval]) is list}  


  # Simulation configuration file
  cFileName = configBuilder(var_params)
  time.sleep(1)


  # Demographics file 
  demographicsBuilder(var_params)
  time.sleep(1)


  # Campaign interventions file
  campaignBuilder(var_params)
  time.sleep(1)


  return cFileName

# end-application

#*******************************************************************************
