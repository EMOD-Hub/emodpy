#********************************************************************************
#
# Python 3.6.0
#
#********************************************************************************

import json

import numpy as np

#*******************************************************************************

# Setup
nSims      =  250
expName    = 'DTK-COVID19-AFRO-Example'
param_dict = {'nSims': nSims, 'expName': expName}


# Parameters
param_dict['simIdx']                       =     list(range(nSims))
param_dict['ctext_val']                    =          nSims*['AFRO:ETH']


# Config Stuff
param_dict['run_number']                   =     list(range(nSims))
param_dict['nTsteps']                      =          nSims*[730  ]
param_dict['R0']                           =          nSims*[  3.0]
#param_dict['R0']                           = (2.0+np.floor(11.0*np.random.rand(nSims))/5.0).tolist()



# Demographics Stuff
param_dict['totpop']                       =          nSims*[1e5 ]
param_dict['num_nodes']                    =          nSims*[  50]
param_dict['migration_coeff']              =          nSims*[1e-4]


# Campaign Stuff
param_dict['age_effect_a']                 =          nSims*[  0.70]
param_dict['age_effect_t']                 =          nSims*[  0.20]

param_dict['HCW_PPE']                      =          nSims*[  0.95]

param_dict['importations_start_day']       =          nSims*[ 60   ]   
param_dict['importations_daily_rate']      =          nSims*[  1.2 ]
param_dict['importations_duration']        =          nSims*[365   ] 
  
param_dict['self_isolate_on_symp_frac']    =          nSims*[  0.1 ]   
param_dict['self_isolate_effectiveness']   =          nSims*[  0.8 ]

param_dict['active_finding_start_day']     =          nSims*[731   ]   
param_dict['active_finding_coverage']      =          nSims*[  0.0 ] 
param_dict['active_finding_effectiveness'] =          nSims*[  0.9 ]
param_dict['active_finding_delay']         =          nSims*[  0.0 ]


# Write parameter dictionary
with open('param_dict.json','w') as fid01:
  json.dump(param_dict,fid01)

#*******************************************************************************
