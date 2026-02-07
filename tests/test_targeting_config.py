import copy
import os
import pytest

import emodpy.utils.targeting_config as tc
from emodpy.emod_task import EMODTask, logger
from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import helpers


@pytest.mark.unit
class TestTargetingConfig():

    def setup_custom_params(self):
        """
        Set up any custom parameters needed for the tests.
        This can be overridden in subclasses to provide specific parameters.
        """
        self.builders = helpers.BuildersCommon

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.num_sim = 2
        self.num_sim_long = 20
        self.case_name = os.path.basename(__file__) + "_" + request.node.name
        self.original_working_dir = os.getcwd()
        self.test_folder = helpers.make_test_directory(self.case_name)
        self.setup_custom_params()
        self.campaign = EMODTask.build_default_campaign(schema_path=self.builders.schema_path)

        # Run test
        yield

        # Post-test
        helpers.close_logger(logger.parent)
        os.chdir(self.original_working_dir)

    def test_is_pregnant(self):
        """
        Test the IsPregnat targeting config filter and see that it creates
        the proper JSON.
        """

        is_preg_yes_1 =  tc.IsPregnant()
        is_preg_yes_2 =  tc.IsPregnant()
        is_preg_no_1  = ~tc.IsPregnant()
        is_preg_no_2  = ~tc.IsPregnant()

        assert(is_preg_yes_1==is_preg_yes_2)
        assert(is_preg_no_1==is_preg_no_2)
        assert(is_preg_yes_1!=is_preg_no_1)
        assert(is_preg_yes_2!=is_preg_no_2)
        assert(is_preg_yes_2!=is_preg_no_1)
        assert(is_preg_yes_1!=is_preg_no_2)

        not_is_preg_yes_1 = ~is_preg_yes_1
        not_is_preg_no_1  = ~is_preg_no_1

        assert(is_preg_yes_1!=not_is_preg_yes_1)
        assert(is_preg_no_1!=not_is_preg_no_1)
        assert(is_preg_no_1==not_is_preg_yes_1)
        assert(is_preg_yes_1==not_is_preg_no_1)

        is_yes_json = {
            "class": "IsPregnant",
            "Is_Equal_To": 1
        }
        
        is_no_json = {
            "class": "IsPregnant",
            "Is_Equal_To": 0
        }

        assert(is_yes_json==is_preg_yes_1.to_simple_dict(self.campaign))
        assert(is_yes_json==is_preg_yes_2.to_simple_dict(self.campaign))
        assert(is_no_json==is_preg_no_1.to_simple_dict(self.campaign))
        assert(is_no_json==is_preg_no_2.to_simple_dict(self.campaign))

    def test_has_ip(self):
        """
        Test the HasIP targeting config filter and see that it creates
        the proper JSON.
        """
        has_ip_risk_no         =  tc.HasIP( ip_key_value= "Risk:NO" )
        has_ip_risk_yes        =  tc.HasIP( ip_key_value= "Risk:YES" )
        not_has_ip_risk_no     = ~tc.HasIP( ip_key_value= "Risk:NO" )
        not_has_ip_risk_yes    = ~tc.HasIP( ip_key_value= "Risk:YES" )
        has_ip_location_urban  =  tc.HasIP( ip_key_value= "Location:URBAN" )
        has_ip_location_rural  =  tc.HasIP( ip_key_value= "Location:RURAL" )

        assert(has_ip_risk_no==has_ip_risk_no)
        assert(has_ip_risk_yes==has_ip_risk_yes)
        assert(has_ip_risk_no!=has_ip_risk_yes)
        assert(has_ip_risk_yes!=has_ip_risk_no)
        assert(has_ip_risk_no!=not_has_ip_risk_no)
        assert(has_ip_risk_yes!=not_has_ip_risk_yes)
        assert(has_ip_location_urban!=has_ip_location_rural)
        assert(has_ip_risk_yes!=has_ip_location_rural)

        has_ip_risk_no_json = {
            "class": "HasIP",
            "Is_Equal_To": 1,
            "IP_Key_Value" : "Risk:NO"
        }

        has_ip_risk_yes_json = {
            "class": "HasIP",
            "Is_Equal_To": 1,
            "IP_Key_Value" : "Risk:YES"
        }
        
        not_has_ip_risk_no_json = {
            "class": "HasIP",
            "Is_Equal_To": 0,
            "IP_Key_Value" : "Risk:NO"
        }

        not_has_ip_risk_yes_json = {
            "class": "HasIP",
            "Is_Equal_To": 0,
            "IP_Key_Value" : "Risk:YES"
        }

        has_ip_location_urban_json = {
            "class": "HasIP",
            "Is_Equal_To": 1,
            "IP_Key_Value" : "Location:URBAN"
        }
        
        has_ip_location_rural_json = {
            "class": "HasIP",
            "Is_Equal_To": 1,
            "IP_Key_Value" : "Location:RURAL"
        }
        
        assert(has_ip_risk_no_json==has_ip_risk_no.to_simple_dict(self.campaign))
        assert(has_ip_risk_yes_json==has_ip_risk_yes.to_simple_dict(self.campaign))
        assert(not_has_ip_risk_no_json==not_has_ip_risk_no.to_simple_dict(self.campaign))
        assert(not_has_ip_risk_yes_json==not_has_ip_risk_yes.to_simple_dict(self.campaign))
        assert(has_ip_location_urban_json==has_ip_location_urban.to_simple_dict(self.campaign))
        assert(has_ip_location_rural_json==has_ip_location_rural.to_simple_dict(self.campaign))

    def test_has_intervention(self):
        """
        Test the HasIntervention targeting config filter and see that it creates
        the proper JSON.
        """
        has_intervention_vaccine_flu_yes_1    =  tc.HasIntervention( intervention_name="FluVaccine" )
        has_intervention_vaccine_flu_yes_2    =  tc.HasIntervention( intervention_name="FluVaccine" )
        has_intervention_vaccine_flu_no_1     = ~tc.HasIntervention( intervention_name="FluVaccine" )
        has_intervention_vaccine_flu_no_2     = ~tc.HasIntervention( intervention_name="FluVaccine" )

        assert(has_intervention_vaccine_flu_yes_1==has_intervention_vaccine_flu_yes_2)
        assert(has_intervention_vaccine_flu_no_1==has_intervention_vaccine_flu_no_2)
        assert(has_intervention_vaccine_flu_yes_1!=has_intervention_vaccine_flu_no_1)
        assert(has_intervention_vaccine_flu_yes_2!=has_intervention_vaccine_flu_no_2)
        assert(has_intervention_vaccine_flu_yes_2!=has_intervention_vaccine_flu_no_1)
        assert(has_intervention_vaccine_flu_yes_1!=has_intervention_vaccine_flu_no_2)

        not_has_intervention_vaccine_flu_yes_1 = ~has_intervention_vaccine_flu_yes_1
        not_has_intervention_vaccine_flu_no_1  = ~has_intervention_vaccine_flu_no_1

        assert(has_intervention_vaccine_flu_yes_1!=not_has_intervention_vaccine_flu_yes_1)
        assert(has_intervention_vaccine_flu_no_1!=not_has_intervention_vaccine_flu_no_1)
        assert(has_intervention_vaccine_flu_no_1==not_has_intervention_vaccine_flu_yes_1)
        assert(has_intervention_vaccine_flu_yes_1==not_has_intervention_vaccine_flu_no_1)

        has_intervention_vaccine_covid_yes  =  tc.HasIntervention( intervention_name="CovidVaccine" )

        assert(has_intervention_vaccine_flu_yes_1!=has_intervention_vaccine_covid_yes)

        has_intervention_vaccine_flu_yes_json = {
            "class": "HasIntervention",
            "Is_Equal_To": 1,
            "Intervention_Name" : "FluVaccine"
        }
        
        has_intervention_vaccine_flu_no_json = {
            "class": "HasIntervention",
            "Is_Equal_To": 0,
            "Intervention_Name" : "FluVaccine"
        }
        
        has_intervention_vaccine_covid_yes_json = {
            "class": "HasIntervention",
            "Is_Equal_To": 1,
            "Intervention_Name" : "CovidVaccine"
        }

        assert(has_intervention_vaccine_flu_yes_json==has_intervention_vaccine_flu_yes_1.to_simple_dict(self.campaign))
        assert(has_intervention_vaccine_flu_no_json==has_intervention_vaccine_flu_no_1.to_simple_dict(self.campaign))
        assert(has_intervention_vaccine_flu_no_json==not_has_intervention_vaccine_flu_yes_1.to_simple_dict(self.campaign))
        assert(has_intervention_vaccine_flu_yes_json==not_has_intervention_vaccine_flu_no_1.to_simple_dict(self.campaign))
        assert(has_intervention_vaccine_covid_yes_json==has_intervention_vaccine_covid_yes.to_simple_dict(self.campaign))

    def test_targeting_logic(self):
        """
        Test the ability to use the bitwise operators ~, |, and &.  We have to use these
        because python does not allow us to override the logical operators.
        """
        has_flu_vaccine =  tc.HasIntervention( intervention_name="FluVaccine" )

        has_ip_risk_low  =  tc.HasIP( ip_key_value="Risk:LOW"  )
        has_ip_risk_high =  tc.HasIP( ip_key_value="Risk:HIGH" )

        is_preg =  tc.IsPregnant()

        # -------------
        # --- Test AND
        # -------------
        is_high_risk_AND_pregnant = has_ip_risk_high & is_preg

        is_high_risk_AND_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    },
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ]
            ]
        }

        assert(is_high_risk_AND_pregnant_json==is_high_risk_AND_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # ----------------
        # --- Test NOT AND
        # ----------------
        not_is_high_risk_AND_pregnant = ~has_ip_risk_high & is_preg

        not_is_high_risk_AND_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 0,
                        "IP_Key_Value" : "Risk:HIGH"
                    },
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ]
            ]
        }

        assert(not_is_high_risk_AND_pregnant_json==not_is_high_risk_AND_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # ----------------
        # --- Test AND NOT
        # ----------------
        is_high_risk_AND_not_pregnant = has_ip_risk_high & ~is_preg

        is_high_risk_AND_not_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    },
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 0
                    }
                ]
            ]
        }

        assert(is_high_risk_AND_not_pregnant_json==is_high_risk_AND_not_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # -------------
        # --- Test OR
        # -------------
        is_high_risk_OR_pregnant = has_ip_risk_high | is_preg

        is_high_risk_OR_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ],
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ]
            ]
        }

        assert(is_high_risk_OR_pregnant_json==is_high_risk_OR_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # ----------------
        # --- Test NOT OR
        # ----------------
        not_is_high_risk_OR_pregnant = ~has_ip_risk_high | is_preg

        not_is_high_risk_OR_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 0,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ],
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ]
            ]
        }

        assert(not_is_high_risk_OR_pregnant_json==not_is_high_risk_OR_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # -----------------
        # --- Test OR NOT
        # -----------------
        is_high_risk_OR_not_pregnant = has_ip_risk_high | ~is_preg

        is_high_risk_OR_not_pregnant_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ],
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 0
                    }
                ]
            ]
        }

        assert(is_high_risk_OR_not_pregnant_json==is_high_risk_OR_not_pregnant.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # ---------------------------
        # --- Test AND reverse order
        # ---------------------------
        is_pregnant_AND_high_risk = is_preg & has_ip_risk_high

        is_pregnant_AND_high_risk_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    },
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ]
            ]
        }

        assert(is_pregnant_AND_high_risk_json==is_pregnant_AND_high_risk.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # --------------------------
        # --- Test OR reverse order
        # --------------------------
        is_pregnant_OR_high_risk = is_preg | has_ip_risk_high

        is_pregnant_OR_high_risk_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ],
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ]
            ]
        }

        assert(is_pregnant_OR_high_risk_json==is_pregnant_OR_high_risk.to_simple_dict(self.campaign))
        assert(is_preg.is_equal_to)
        assert(has_ip_risk_high.is_equal_to)
        assert(has_flu_vaccine.is_equal_to)

        # -------------------------------
        # --- Test combining AND and OR
        # -------------------------------

        is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine1 =  has_ip_risk_high & is_preg  |  has_ip_risk_low & has_flu_vaccine
        is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine2 = (has_ip_risk_high & is_preg) | (has_ip_risk_low & has_flu_vaccine)

        is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    },
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    }
                ],
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:LOW"
                    },
                    {
                        "class": "HasIntervention",
                        "Is_Equal_To": 1,
                        "Intervention_Name" : "FluVaccine"
                    }
                ]
            ]
        }

        assert(is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine_json==
               is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine1.to_simple_dict(self.campaign))
        assert(is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine_json==
               is_high_risk_AND_pregnant_OR_low_risk_AND_has_flu_vaccine2.to_simple_dict(self.campaign))

        # -------------------------------
        # --- Test combining OR and AND
        # -------------------------------

        is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine1 =  has_ip_risk_high |  is_preg  &  has_ip_risk_low  | has_flu_vaccine
        is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine2 =  has_ip_risk_high | (is_preg  &  has_ip_risk_low) | has_flu_vaccine

        is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:HIGH"
                    }
                ],
                [
                    {
                        "class": "IsPregnant",
                        "Is_Equal_To": 1
                    },
                    {
                        "class": "HasIP",
                        "Is_Equal_To": 1,
                        "IP_Key_Value" : "Risk:LOW"
                    }
                ],
                [
                    {
                        "class": "HasIntervention",
                        "Is_Equal_To": 1,
                        "Intervention_Name" : "FluVaccine"
                    }
                ]
            ]
        }

        assert(is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine_json==
               is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine1.to_simple_dict(self.campaign))
        assert(is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine_json==
               is_high_risk_OR_pregnant_AND_low_risk_OR_has_flu_vaccine2.to_simple_dict(self.campaign))

        # --------------------------------------------------------------
        # --- Test using parentheses to change the order of operations
        # --------------------------------------------------------------

        is_high_risk_or_pregnant_AND_low_risk_or_has_flu_vaccine =  (has_ip_risk_high |  is_preg)  &  (has_ip_risk_low  | has_flu_vaccine)

        is_high_risk_or_pregnant_AND_low_risk_or_has_flu_vaccine_json = {
            "class": "TargetingLogic",
            "Is_Equal_To": 1,
            "Logic": [
                [
                    {
                        "class": "TargetingLogic",
                        "Is_Equal_To": 1,
                        "Logic": [
                            [
                                {
                                    "class": "HasIP",
                                    "Is_Equal_To": 1,
                                    "IP_Key_Value" : "Risk:HIGH"
                                }
                            ],
                            [
                                {
                                    "class": "IsPregnant",
                                    "Is_Equal_To": 1
                                }
                            ]
                        ]
                    },
                    {
                        "class": "TargetingLogic",
                        "Is_Equal_To": 1,
                        "Logic": [
                            [
                                {
                                    "class": "HasIP",
                                    "Is_Equal_To": 1,
                                    "IP_Key_Value" : "Risk:LOW"
                                }
                            ],
                            [
                                {
                                    "class": "HasIntervention",
                                    "Is_Equal_To": 1,
                                    "Intervention_Name" : "FluVaccine"
                                }
                            ]
                        ]
                    }
                ]
            ]
        }

        assert(is_high_risk_or_pregnant_AND_low_risk_or_has_flu_vaccine_json==
               is_high_risk_or_pregnant_AND_low_risk_or_has_flu_vaccine.to_simple_dict(self.campaign))

        # ---------------------------------------------------------------------
        # --- Test that operators don't change state of object
        # ---
        # --- I believe the tests above check the BaseTargetingConfig objects,
        # --- but we need to make sure that TargetingLogic ones don't change.
        # ---------------------------------------------------------------------

        #
        # Check invert
        #
        tmp = has_ip_risk_high & is_preg
        tmp_copy = copy.deepcopy(tmp)
        assert(isinstance(tmp, tc._TargetingLogic))
        assert(isinstance(tmp_copy, tc._TargetingLogic))

        tmp_neg = ~tmp
        assert(1==tmp.is_equal_to)
        assert(0==tmp_neg.is_equal_to)
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        #
        # Check AND
        #
        tmp_and_flu = tmp & has_flu_vaccine
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        tmp_and_flu = has_flu_vaccine & tmp
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        tmp_and_and = tmp & tmp
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        #
        # Check OR
        #
        tmp_and_flu = tmp | has_flu_vaccine
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        tmp_and_flu = has_flu_vaccine | tmp
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        tmp_and_and = tmp | tmp
        assert(tmp_copy.to_simple_dict(self.campaign)==tmp.to_simple_dict(self.campaign))

        # --------------------------------------------------------------
        # --- Test inversion on TargetingLogic when logically combining
        # --------------------------------------------------------------

        has_covid_vaccine =  tc.HasIntervention( intervention_name="CovidVaccine" )

        #
        # OR not
        #
        or_not = is_preg | ~((has_ip_risk_low & has_covid_vaccine) | has_flu_vaccine)

        or_not_json = {
            'class': 'TargetingLogic',
            'Is_Equal_To': 1, 
            'Logic': [
                [
                    {
                        'class': 'IsPregnant', 
                        'Is_Equal_To': 1
                    }
                ], [
                    {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 0, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 
                                    'Risk:LOW', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'CovidVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ], [
                                {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'FluVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ]
                        ]
                    }
                ]
            ]
        }
        assert(or_not_json==or_not.to_simple_dict(self.campaign))

        #
        # AND not
        #
        and_not = is_preg & ~((has_ip_risk_low & has_covid_vaccine) | has_flu_vaccine)

        and_not_json = {
            'class': 'TargetingLogic', 
            'Is_Equal_To': 1, 
            'Logic': [
                [
                    {
                        'class': 'IsPregnant', 
                        'Is_Equal_To': 1
                    }, {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 0, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 'Risk:LOW', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'CovidVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ], [
                                {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'FluVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ]
                        ]
                    }
                ]
            ]
        }
        assert(and_not_json==and_not.to_simple_dict(self.campaign))

        not_or = ~((has_ip_risk_low & has_covid_vaccine) | has_flu_vaccine) | is_preg

        not_or_json = {
            'class': 'TargetingLogic', 
            'Is_Equal_To': 1, 
            'Logic': [
                [
                    {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 0, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 'Risk:LOW', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'CovidVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ], [
                                {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'FluVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ]
                        ]
                    }
                ], [
                    {
                        'class': 'IsPregnant', 
                        'Is_Equal_To': 1
                    }
                ]
            ]
        }
        assert(not_or_json==not_or.to_simple_dict(self.campaign))

        #
        # not AND
        #
        not_and = ~((has_ip_risk_low & has_covid_vaccine) | has_flu_vaccine) & is_preg

        not_and_json = {
            'class': 'TargetingLogic', 
            'Is_Equal_To': 1, 
            'Logic': [
                [
                    {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 0, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 'Risk:LOW', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'CovidVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ], [
                                {
                                    'class': 'HasIntervention', 
                                    'Intervention_Name': 'FluVaccine', 
                                    'Is_Equal_To': 1
                                }
                            ]
                        ]
                    }, {
                        'class': 'IsPregnant', 
                        'Is_Equal_To':1
                    }
                ]
            ]
        }
        assert(not_and_json==not_and.to_simple_dict(self.campaign))

        # -------------------------------------------
        # --- Test deeply nested logic
        # -------------------------------------------
        nested = has_ip_risk_high & is_preg
        nested =  nested & ~nested
        nested = ~nested &  nested

        nested_json = {
            'class': 'TargetingLogic', 
            'Is_Equal_To': 1, 
            'Logic': [
                [
                    {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 0, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 'Risk:HIGH', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'IsPregnant', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'TargetingLogic', 
                                    'Is_Equal_To': 0, 
                                    'Logic': [
                                        [
                                            {
                                                'class': 'HasIP', 
                                                'IP_Key_Value': 'Risk:HIGH', 
                                                'Is_Equal_To': 1
                                            }, {
                                                'class': 'IsPregnant', 
                                                'Is_Equal_To': 1
                                            }
                                        ]
                                    ]
                                }
                            ]
                        ]
                    }, {
                        'class': 'TargetingLogic', 
                        'Is_Equal_To': 1, 
                        'Logic': [
                            [
                                {
                                    'class': 'HasIP', 
                                    'IP_Key_Value': 'Risk:HIGH', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'IsPregnant', 
                                    'Is_Equal_To': 1
                                }, {
                                    'class': 'TargetingLogic', 
                                    'Is_Equal_To': 0, 
                                    'Logic': [
                                        [
                                            {
                                                'class': 'HasIP', 
                                                'IP_Key_Value': 'Risk:HIGH', 
                                                'Is_Equal_To': 1
                                            }, {
                                                'class': 'IsPregnant', 
                                                'Is_Equal_To': 1
                                            }
                                        ]
                                    ]
                                }
                            ]
                        ]
                    }
                ]
            ]
        }
        assert(nested_json==nested.to_simple_dict(self.campaign))
