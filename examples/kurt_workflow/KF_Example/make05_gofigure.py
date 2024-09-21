import os, json

import numpy              as np
import matplotlib.pyplot  as plt
import matplotlib.patches as patch


datlist = list()
vallist = list()

targfile = 'infBlock.csv'
with open(targfile) as fid01:
  infBlock = np.loadtxt(fid01,delimiter=',')
datlist.append(infBlock)
targfile = 'param_dict.json'
with open(targfile) as fid01:
  pDic = json.load(fid01)
vallist.append(pDic)


for k1 in range(len(datlist)):

    # Figure
    fig01 = plt.figure()
    axs01 = fig01.add_axes([0.15,0.1,0.75,0.80])
    plt.sca(axs01)
 
    axs01.grid(b=True, which='major', ls='-', lw=0.5, label='')
    axs01.grid(b=True, which='minor', ls=':', lw=0.1)
    axs01.set_axisbelow(True)

    axs01.set_ylabel('Daily Infections per-100k',fontsize=15)

    infDatCum  = np.cumsum(datlist[k1],axis=1)
    infDatPart = datlist[k1]
    tyslice = infDatPart
    if(tyslice.shape[0] > 0):
      yval = np.mean(tyslice,axis=0)
    else:
      continue

    xval          = np.arange(0.5,tyslice.shape[1])
    infDatSetSort = np.sort(tyslice,axis=0)
    infDatSetSort = infDatSetSort/1e1    

    for patwid in [0.475,0.375,0.25]:
      xydat = np.zeros((2*infDatSetSort.shape[1],2))
      xydat[:,0] = np.hstack((xval,xval[::-1]))
      tidx = int((0.5-patwid)*infDatSetSort.shape[0])
      xydat[:,1] = np.hstack((infDatSetSort[tidx,:],infDatSetSort[-tidx,::-1]))

      polyShp = patch.Polygon(xydat, facecolor='C0', alpha=0.7-patwid, edgecolor=None)
      axs01.add_patch(polyShp)
    
    yval = yval/1e1
    axs01.plot(xval,yval,color='C0',linestyle='-',linewidth=2)
    
    plt.savefig('CloudDaily.png')
    plt.close()


