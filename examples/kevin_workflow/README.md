<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->



<!-- END doctoc generated TOC please keep comment here to allow auto update -->

1. generate asset collection (not include Eradication and dlls in assetcollection):
   Run in Slurm cluster: python create_asset_collection_linux.py in Calibration_idmtools dir
   Run in Windows cluster: python create_asset_collection_windows.py in Calibration_idmtools dir

   note: first time run, you need to run with windows console to get prompt for login to bamboo.
   pycharm did not prompt correctly, but once login to bamboo, you do not need to do this login anymore.

2. Do not check in Eradication.exe and dll/so files under inputs to github. always download from bamboo to local folder
   script will load them from local

3. Do not put Eradication and dll in the same folder as other input files(in dropbox)

4. in experiment script, switch platform from windows(COMPS) to linux(SLURM), need to switch 2 lines of code
  platform = Platform('COMPS2')
  os_path = 'windows'
  # platform = Platform('SLURM')
  # os_path = 'linux'

