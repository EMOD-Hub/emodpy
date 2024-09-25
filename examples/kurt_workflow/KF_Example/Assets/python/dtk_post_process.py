#********************************************************************************
#
# Python 3.6.0
#
#********************************************************************************

import os, sys, json

ext_py_path = os.path.join('Assets','site_packages')
if(ext_py_path not in sys.path):
  sys.path.append(ext_py_path)

import numpy as np

#********************************************************************************

def application(oDirName=''):

  # Read index of simulation parameter set
  with open('idxStrFile.txt','r') as fid01:
    simIdx = int(fid01.readline())


  # Read parameter dictionary, select appropriate index
  with open(os.path.join('Assets','param_dict.json')) as fid01:
    param_dict = json.load(fid01)
  var_params = {keyval:param_dict[keyval][simIdx]
                  for keyval in param_dict if type(param_dict[keyval]) is list}


  # Prep output dictionary
  keyStr = '{:05d}'.format(simIdx)
  tmpDat = dict()


  # Output parsing
  databrick = np.zeros((17,var_params['nTsteps']))
  with open(os.path.join(oDirName,'PropertyReport.json')) as fid01:
    rep_file = json.load(fid01)
    rep_channels = rep_file['Channels']
    for channel_value in rep_channels:
      if('New Infections' not in channel_value):
        continue
      else:
        infDat = np.array(rep_channels[channel_value]['Data'])
      for k1 in range(16):
        agestr = 'age{:02d}'.format(5*k1)
        if(agestr in channel_value):
          databrick[k1,:] += infDat
      if('HCW' in channel_value):
          databrick[-1,:] += infDat  
  tmpDat[keyStr] = databrick.tolist()


  # Write output dictionary
  with open('tmpOutfile','w') as tmpFile:
    json.dump(tmpDat, tmpFile)
    
  
  return None

#end-application

#********************************************************************************
