#********************************************************************************
#
# Builds a config.json file to be used as input to the DTK.
#
# Python 3.6.0
#
#********************************************************************************

import os, sys, json

ext_py_path = os.path.join('Assets','site_packages')
if(ext_py_path not in sys.path):
  sys.path.append(ext_py_path)

#********************************************************************************

def configBuilder(params=dict()):

  cFileName = 'config_useful.json'


  # Local parameters
  run_number     = params['run_number']
  n_tsteps       = params['nTsteps']
  R0_val         = params['R0']


  # *****  Dictionary of parameters to be written *****
  
  param_set  = dict()

  
  # ***** Generic simulation *****

  # Simulation name; comment field;
  param_set['Config_Name'] = 'COMMENT_FIELD'
  
  # Simulation type 
  param_set['Simulation_Type'] = 'GENERIC_SIM'

  # Random numbers: seed and generator type
  param_set['Run_Number']                      = run_number
  param_set['Random_Number_Generator_Type']    = 'USE_PSEUDO_DES'
  param_set['Random_Number_Generator_Policy']  = 'ONE_PER_CORE'


  # Timing parameters; implied days 
  # Float: [0.0, 1.0e6]
  param_set['Start_Time']           = 365.0*(2020-1900)+1
  param_set['Simulation_Duration']  = n_tsteps
  param_set['Simulation_Timestep']  =   1.0 

  # Termination predicates
  param_set['Enable_Termination_On_Zero_Total_Infectivity'] =  0


  # ***** Parallel computing *****

  # Number of cores
  # Integer: [1, X]
  param_set['Num_Cores'] = 1  

  # Supporting filename
  param_set['Load_Balance_Filename'] = '' 


  # ***** Serialization type *****
  param_set['Serialization_Type'] = 'NONE' 


  # ***** Serialization type *****
  param_set['Python_Inprocessing_Tsteps'] = list() 


  # ***** Strain Tracking *****
  param_set['Enable_Strain_Tracking'] = 0


  # ***** Infectivity Descriptions *****
  param_set['Enable_Superinfection']           = 0
  param_set['Max_Individual_Infections']       = 1 
  param_set['Enable_Skipping']                 = 0
  param_set['Infection_Updates_Per_Timestep']  = 1
  param_set['Enable_Infectivity_Scaling']      = 0
  param_set['Enable_Infectivity_Reservoir']    = 0

  # Overdispersion of the infection process
  param_set['Enable_Infection_Rate_Overdispersion'] = 1
        
  # Daily infectiousness contribution
  #  (daily amount of shedding; R0 = this_value*mean_shedding_duration)
  param_set['Base_Infectivity_Distribution']      = 'EXPONENTIAL_DISTRIBUTION'
  param_set['Base_Infectivity_Exponential']       = R0_val/8.0  

  # Incubation descriptions
  #  (days between infection and shedding)
  param_set['Incubation_Period_Distribution']     = 'GAUSSIAN_DISTRIBUTION'
  param_set['Incubation_Period_Gaussian_Mean']    = 4.0
  param_set['Incubation_Period_Gaussian_Std_Dev'] = 1.0

  # Infection descriptions
  #  (duration of shedding)
  param_set['Infectious_Period_Distribution']     = 'GAMMA_DISTRIBUTION'
  param_set['Infectious_Period_Shape']            = 2.0
  param_set['Infectious_Period_Scale']            = 4.0

  # Symptoms description
  #  (days after shedding that symptoms begin)
  param_set['Symptomatic_Infectious_Offset']      = 2.0

    
  # ***** Immunity / Mortality Descriptions *****
  param_set['Enable_Disease_Mortality']               = 0
  param_set['Enable_Maternal_Protection']             = 0
  param_set['Enable_Immunity']                        = 1
  param_set['Enable_Immune_Decay']                    = 0
  param_set['Post_Infection_Acquisition_Multiplier']  = 0.0
  param_set['Post_Infection_Transmission_Multiplier'] = 0.0  
  param_set['Post_Infection_Mortality_Multiplier']    = 0.0 


  # ***** Adapted sampling *****
  param_set['Individual_Sampling_Type'] = 'ADAPTED_SAMPLING_BY_IMMUNE_STATE'  
  param_set['Base_Individual_Sample_Rate']       =  1.0  
  param_set['Relative_Sample_Rate_Immune']       =  0.1
  param_set['Immune_Threshold_For_Downsampling'] =  1.0e-5
  param_set['Immune_Downsample_Min_Age']         =  0.0


  # ***** Reporting / Output Parameters *****
  
  # Boolean: 0/1
  param_set['Enable_Default_Reporting']              = 1
  param_set['Enable_Demographics_Reporting']         = 0
  param_set['Enable_Property_Output']                = 1
  param_set['Enable_Spatial_Output']                 = 0
  param_set['Report_Event_Recorder']                 = 0
  param_set['Report_Coordinator_Event_Recorder']     = 0
  param_set['Report_Node_Event_Recorder']            = 0
  param_set['Report_Surveillance_Event_Recorder']    = 0



  # ***** Intervention parameters *****

  param_set['Enable_Interventions'] = 1  
  param_set['Campaign_Filename'] = 'campaign.json'



  # ***** Demographic parameters *****
  
  param_set['Demographics_Filenames']       = ['demographics.json']  

  param_set['Enable_Demographics_Builtin']  = 0
  param_set['Enable_Demographics_Risk'] = 0
  param_set['Node_Grid_Size']               = 4.167e-3
  param_set['x_Base_Population']            = 1.0


  param_set['Age_Initialization_Distribution_Type']        = 'DISTRIBUTION_OFF'
  param_set['Enable_Initial_Susceptibility_Distribution']  = 0
  param_set['Enable_Vital_Dynamics']                       = 0
  param_set['Enable_Heterogeneous_Intranode_Transmission'] = 1
  param_set['Enable_Initial_Prevalence']                   = 0



  #  ***** Migration / Spatial parameters *****
  
  param_set['Migration_Model']     = 'FIXED_RATE_MIGRATION'
  param_set['Migration_Pattern']   = 'SINGLE_ROUND_TRIPS'

  param_set['Enable_Air_Migration']             = 0
  param_set['Enable_Family_Migration']          = 0
  param_set['Enable_Local_Migration']           = 0
  param_set['Enable_Migration_Heterogeneity']   = 0
  param_set['Enable_Regional_Migration']        = 1
  param_set['Enable_Sea_Migration']             = 0

  param_set['Regional_Migration_Filename']      = 'regional_migration.bin'

  param_set['Air_Migration_Roundtrip_Duration']         = 0.0
  param_set['Air_Migration_Roundtrip_Probability']      = 0.0
  param_set['Family_Migration_Roundtrip_Duration']      = 0.0
  param_set['Local_Migration_Roundtrip_Duration']       = 0.0
  param_set['Local_Migration_Roundtrip_Probability']    = 0.0
  param_set['Regional_Migration_Roundtrip_Duration']    = 0.0
  param_set['Regional_Migration_Roundtrip_Probability'] = 0.0
  param_set['Sea_Migration_Roundtrip_Duration']         = 0.0
  param_set['Sea_Migration_Roundtrip_Probability']      = 0.0

  param_set['x_Regional_Migration']             = 1.0

  #  ***** Debug *****

  #param_set['logLevel_Memory'] = 'DEBUG'

    

  #  ***** End file construction *****
  with open(cFileName,'w') as fid01:
    json.dump({'parameters': param_set},fid01,sort_keys=True)

  return cFileName


#end-configBuilder

#********************************************************************************
