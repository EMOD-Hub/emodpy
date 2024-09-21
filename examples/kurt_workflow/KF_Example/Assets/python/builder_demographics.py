#********************************************************************************
#
# Builds a demographics.json file to be used as input to the DTK.
#
# Python 3.6.0
#
#********************************************************************************

import os, sys, json, io

from aux_matrix_calc import mat_magic

ext_py_path = os.path.join('Assets','site_packages')
if(ext_py_path not in sys.path):
  sys.path.append(ext_py_path)

import numpy                    as    np

#********************************************************************************

def demographicsBuilder(params=dict()):


  # Local parameters
  totpop     = params['totpop']
  num_nodes  = params['num_nodes']
  mrcoeff    = params['migration_coeff']
  ctextval   = params['ctext_val']


  # *****  Dictionary of parameters to be written ***** 

  json_set = dict()


  # ***** Detailed node attributes *****

  # Add node list
  json_set['Nodes'] = list()

  # Generate node sizes
  temp01  = np.random.rand(num_nodes)+0.5
  npops   = (np.around(temp01/np.sum(temp01)*totpop)).tolist()
  
  # Add nodes to demographics
  for k1 in range(len(npops)):
    nodeDic   = dict()    
    nodeDic['NodeID']         =   k1+1
    nodeDic['NodeAttributes'] = {'InitialPopulation': int(npops[k1]) }
    json_set['Nodes'].append(nodeDic)


  # ***** Metadata and default attributes *****
  
  # Create metadata dictionary
  json_set['Metadata'] = { 'IdReference':   'covid-custom' }

  # Create defaults dictionary
  json_set['Defaults'] = { 'IndividualAttributes': dict()  ,
                           'IndividualProperties': list()  ,
                           'NodeAttributes':       dict()  }
  
  # Add default node attributes
  nadict = dict()

  nadict['BirthRate']                   =   0.0
  nadict['Latitude']                    =   0.0
  nadict['Longitude']                   =   0.0
  nadict['InfectivityOverdispersion']   =   2.1
  nadict['Region']                      =   1  
  nadict['Seaport']                     =   0  
  nadict['Airport']                     =   0  


  json_set['Defaults']['NodeAttributes'].update(nadict)

  # Get HINT matrix
  pdict = {'arg_dist':            [1.0,1.0,1.0,1.0] ,
           'spike_mat':                       False ,
           'nudge_mat':                       False ,
           'hcw_h2h':                         False ,
           'ctext_val':                    ctextval }
  (age_pyr, age_names, mat_block) = mat_magic(pdict)

  # Add default individual properties
  ipdict = dict()

  ipdict['Property']              = 'Geographic'
  ipdict['Values']                = age_names
  ipdict['Initial_Distribution']  = age_pyr.tolist()
  ipdict['Transitions']           = list()
  ipdict['TransmissionMatrix']    = {'Matrix': mat_block.tolist(),
                                     'Route':           'Contact'}

  json_set['Defaults']['IndividualProperties'].append(ipdict)


  # ***** Write demographics files ***** 
  with open('demographics.json','w')  as fid01:
    json.dump(json_set,fid01,sort_keys=True)


  # ***** Write migration files *****
  migJson = {'Metadata': { 'IdReference':   'covid-custom' ,
                           'NodeCount':          num_nodes ,
                           'DatavalueCount':            30 } }
  migJson['NodeOffsets'] = ''.join(['{:08d}{:0>8s}'.format(k1,hex(k1*360)[2:])
                                                  for k1 in range(num_nodes)])
  
  with open('regional_migration.bin.json','w') as fid01:
    json.dump(migJson,fid01,sort_keys=True)

  outbytes = io.BytesIO()
  for k1 in range(num_nodes):
    for k2 in range(1,31):
      if(k2 < num_nodes):
        tnode = int(np.random.choice(np.arange(1,num_nodes+1)))
      else:
        tnode = 0
      #end-if
      outbytes.write(tnode.to_bytes(4,byteorder='little'))
    #end-k2
    for k2 in range(1,31):
      if(k2 < num_nodes):
        val = np.array([mrcoeff],dtype=np.float64)
      else:
        val = np.array([0.0],dtype=np.float64)
      #end-if
      outbytes.write(val.tobytes())
    #end-k2
  #end-k1
  with open('regional_migration.bin','wb') as fid01:
    fid01.write(outbytes.getvalue())

#end-demographicsBuilder

#*******************************************************************************
