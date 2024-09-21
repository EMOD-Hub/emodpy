#********************************************************************************
#
# Python 3.6.0
#
#*******************************************************************************

import json, multiprocessing, time

from COMPS                       import Client

from COMPS.Data                  import Experiment
from COMPS.Data.Simulation       import SimulationState

# ******************************************************************************



def GetTheThing(mapArg):
  (simObj, expDat, simNum) = mapArg
  targ_json = 'tmpOutfile'
  sim_id = simObj.id.hex
  Client.login('https://comps2.idmod.org')
  r_data = Client.get(path='/asset/Simulations/'+sim_id+'/Output')
  r_list = (r_data.json())['Resources']
  r_dict = {out_ass['FriendlyName']: out_ass['Url'] for out_ass in r_list}
  if(targ_json in r_dict):
    urlVal   = (r_dict[targ_json]).split('/asset/')
    shrdDat  = (Client.get(path='/asset/'+urlVal[1])).json()
    expDat.update(shrdDat)
  if((simNum+1)%100==0):
    print(simNum+1)



if __name__ == '__main__':

  # Get Experiment ID
  with open('COMPS_ID') as fid01:
    exp_id = fid01.readline().strip()

  # Login to the COMPS server
  Client.login('https://comps2.idmod.org')

  # Wait until all simulations are completed
  while(True):
      exp01    = Experiment.get(id=exp_id)
      sim_list = exp01.get_simulations()

      num_done = 0
      for sim in sim_list:
          if(sim.state == SimulationState.Succeeded or
             sim.state == SimulationState.Failed or
             sim.state == SimulationState.CancelRequested or
             sim.state == SimulationState.Canceled):
              num_done = num_done + 1
            
      print('Remaining: {:d}'.format(len(sim_list) - num_done))

      if(num_done < len(sim_list)):
          time.sleep(90)
      else:
          break
  #end-while

  # Copy output file to local output directory
  pool_boss = multiprocessing.Manager()
  expDat    = pool_boss.dict()
  exp01     = Experiment.get(id=exp_id)
  sim_list  = exp01.get_simulations()
  pool_args = [(sim_list[k1], expDat, k1) for k1 in range(len(sim_list))]
  with multiprocessing.Pool(8) as proc_pool:
    proc_pool.map(GetTheThing, pool_args)

  with open('data_brick.json','w') as fid01:
    json.dump(dict(expDat),fid01)

# ******************************************************************************
