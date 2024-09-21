def set_params(config):
    config.parameters.Enable_Termination_On_Zero_Total_Infectivity = 1
    config.parameters.Minimum_End_Time = 100
    config.parameters.Simulation_Duration = 365
    config.parameters.Enable_Demographics_Builtin = 0
    config.parameters.Enable_Vital_Dynamics = 0
    config.parameters.Enable_Event_DB = 1
    config.parameters.Demographics_Filenames = "demographics/generic_scenarios_demographics.json",
    config.parameters.Enable_Interventions = 1 # dtk_pre_proc should set this
    config.parameters.Campaign_Filename = "campaign.json" # dtk_pre_proc should set this
    config.parameters.Base_Infectivity_Distribution = "EXPONENTIAL_DISTRIBUTION"
    config.parameters.Base_Infectivity_Exponential = 0.35
    config.parameters.Incubation_Period_Distribution = "GAUSSIAN_DISTRIBUTION"
    config.parameters.Incubation_Period_Gaussian_Mean = 8
    config.parameters.Incubation_Period_Gaussian_Std_Dev = 3
    config.parameters.Infectious_Period_Distribution = "GAMMA_DISTRIBUTION" 
    config.parameters.Infectious_Period_Scale = 4
    config.parameters.Infectious_Period_Shape = 2
    # config.parameters.Symptomatic_Infectious_Offset = 2
    config.parameters.Enable_Demographics_Reporting = 0
    config.parameters.Load_Balance_Filename = ""
    return config
