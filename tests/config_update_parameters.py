from emodpy.emod_task import EMODTask


def standard_cb_updates(task: EMODTask) -> EMODTask:
    task.update_parameters({
        'x_Temporary_Larval_Habitat': 0.2,
        'Base_Population_Scale_Factor': 0.1,
    })

    task.update_parameters({
        # DEMOGRAPHICS
        "Enable_Demographics_Reporting": 1,
        "Enable_Initial_Prevalence": 0,
        "Enable_Strain_Tracking": 0,
        "Enable_Termination_On_Zero_Total_Infectivity": 0,
        "Enable_Vital_Dynamics": 0,
        "Enable_Immune_Decay": 0,
        "Post_Infection_Acquisition_Multiplier": 0.7,
        "Post_Infection_Transmission_Multiplier": 0.4,
        "Post_Infection_Mortality_Multiplier": 0.3,
        "Enable_Maternal_Protection": 0,
        "Enable_Infectivity_Scaling": 0,

        # DISEASE
        "Base_Incubation_Period": 0,
        "Base_Infectivity": 0.7,

        # PRIMARY
        "Run_Number": 1,
        "Simulation_Duration": 120,
        "Start_Time": 0
    })

    # Set climate
    # set_climate_constant(sim)
    task.set_parameter('Climate_Model', 'CLIMATE_CONSTANT')
    task.set_parameter('Climate_Update_Resolution', 'CLIMATE_UPDATE_DAY')


def set_species_param(task, species, parameter, value):
    Vector_Species_Params = task.get_parameter('Vector_Species_Params', {})
    species_dict = Vector_Species_Params.get(species, {})
    species_dict[parameter] = value
    Vector_Species_Params[species] = species_dict
    task.set_parameter('Vector_Species_Params', Vector_Species_Params)
    return {'.'.join([species, parameter]): value}


def update_vector_params(task):
    task.update_parameters({"Vector_Species_Names": ['gambiae']})
    set_species_param(task, 'gambiae', 'Larval_Habitat_Types',
                      {"LINEAR_SPLINE": {
                          "Capacity_Distribution_Over_Time": {
                              "Times": [0.0, 30.417, 60.833, 91.25, 121.667, 152.083,
                                        182.5, 212.917, 243.333, 273.75, 304.167, 334.583],
                              "Values": [3, 0.8, 1.25, 0.1, 2.7, 10, 6, 35, 2.8, 1.5, 1.6, 2.1]
                          },
                          "Capacity_Distribution_Number_Of_Years": 1,
                          "Max_Larval_Capacity": pow(10, 8)
                      }})
    set_species_param(task, "gambiae", "Indoor_Feeding_Fraction", 0.9)
    set_species_param(task, "gambiae", "Adult_Life_Expectancy", 20)


def config_update_params(task):
    # General
    standard_cb_updates(task)
    update_vector_params(task)
