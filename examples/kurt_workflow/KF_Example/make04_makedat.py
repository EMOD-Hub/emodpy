import os, json, shutil

import numpy as np

with open('data_brick.json') as fid01:
  dbrick = json.load(fid01)

with open('param_dict.json') as fid01:
  pdic = json.load(fid01)

nSims  = pdic['nSims']
nTimes = np.array(pdic['nTsteps'])
nTime  = np.max(nTimes)

infBlock = np.zeros((nSims,nTime))
for simKey in dbrick:
  idx = int(simKey)
  infDat = np.sum(np.array(dbrick[simKey]),axis=0)
  if(infDat.shape[0] != nTimes[idx]):
    print(infDat.shape[0], nTimes[idx])
  infBlock[idx,:] = infDat

np.savetxt('infBlock.csv',infBlock,delimiter=',',fmt='%.1f')
