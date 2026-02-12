import os.path
from emodpy.campaign.base_intervention import IndividualIntervention, NodeIntervention
from emodpy.campaign.individual_intervention import (BroadcastEvent, BroadcastEventToOtherNodes,
                                                     ControlledVaccine, DelayedIntervention, IVCalendar, IndividualImmunityChanger,
                                                     IndividualNonDiseaseDeathRateModifier, MigrateIndividuals,
                                                     MultiEffectBoosterVaccine, MultiEffectVaccine, MultiInterventionDistributor,
                                                     OutbreakIndividual, PropertyValueChanger, SimpleBoosterVaccine,
                                                     _SimpleDiagnostic, _SimpleHealthSeekingBehavior, SimpleVaccine,
                                                     StandardDiagnostic)
from emodpy.campaign.node_intervention import (MultiNodeInterventionDistributor, _NodeLevelHealthTriggeredIV, _BirthTriggeredIV,
                                               _BroadcastCoordinatorEventFromNode, BroadcastNodeEvent, ImportPressure,
                                               MigrateFamily, NodePropertyValueChanger, Outbreak)
from emodpy.utils.emod_enum import NodeSelectionType, VaccineType, EventOrConfig
from emodpy.campaign.common import ValueMap, CommonInterventionParameters, TargetDemographicsConfig, PropertyRestrictions
import emodpy.campaign.waning_config as waning_config
from emodpy.utils.distributions import (ExponentialDistribution, PoissonDistribution, GaussianDistribution,
                                        UniformDistribution, LogNormalDistribution, ConstantDistribution,
                                        WeibullDistribution, DualConstantDistribution, DualExponentialDistribution)
from emodpy.utils.targeting_config import IsPregnant
from emod_api import campaign as api_campaign

from pathlib import Path
import sys
parent = Path(__file__).resolve().parent
sys.path.append(str(parent))
import manifest
import helpers
import pytest


@ pytest.mark.unit
class TestIndividualIntervention():
    if not os.path.isfile(manifest.hiv_eradication_path):
        import emod_hiv.bootstrap as dtk
        dtk.setup(manifest.hiv_package_folder)
    campaign = api_campaign  # Initialize the campaign object
    campaign.set_schema(manifest.hiv_schema_path)  # set the schema path to the HIV schema file
    common_intervention_parameters = CommonInterventionParameters(cost=0.5,
                                                                  disqualifying_properties=['age:20'],
                                                                  dont_allow_duplicates=True,
                                                                  intervention_name='TestName',
                                                                  new_property_value='Risk:High')
    custom_intervention_name = 'TestName'

    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'SimpleVaccine'
        self.intervention = IndividualIntervention(self.campaign, self.intervention_class_name, self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        """
        This method test the initialization of the Intervention class.
        Each subtest classes should override this function for its own.
        """
        assert(self.intervention_dict['class']==self.intervention_class_name)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')

    def assert_common_parameters(self,
                                 intervention_dict,
                                 cost=None,
                                 disqualifying_properties=None,
                                 dont_allow_duplicates=None,
                                 intervention_name=None,
                                 new_property_value=None):

        if cost is not None:
            assert(intervention_dict.Cost_To_Consumer==cost)
        if disqualifying_properties is not None:
            assert(intervention_dict.Disqualifying_Properties==disqualifying_properties)
        if dont_allow_duplicates is not None:
            assert(intervention_dict.Dont_Allow_Duplicates==dont_allow_duplicates)
        if intervention_name is not None:
            assert(intervention_dict.Intervention_Name==intervention_name)
        if new_property_value is not None:
            assert(intervention_dict.New_Property_Value==new_property_value)

    def test_set_cost(self):
        """
        This method test the set_cost method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        cost = 10.0
        self.intervention._set_cost(cost)
        assert(self.intervention_dict.Cost_To_Consumer==cost)

    def test_set_disqualifying_properties(self):
        """
        This method test the set_disqualifying_properties method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        disqualifying_properties = ['age:30']
        self.intervention._set_disqualifying_properties(disqualifying_properties)
        assert(self.intervention_dict.Disqualifying_Properties==disqualifying_properties)
        disqualifying_properties_2 = [' age : 30 ']
        self.intervention._set_disqualifying_properties(disqualifying_properties_2)
        assert(self.intervention_dict.Disqualifying_Properties==disqualifying_properties)

    def test_set_dont_allow_duplicates(self):
        """
        This method test the set_dont_allow_duplicates method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        self.intervention._set_dont_allow_duplicates(True)
        assert(self.intervention_dict.Dont_Allow_Duplicates)

    def test_set_intervention_name(self):
        """
        This method test the set_intervention_name method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        intervention_name = 'TestName'
        self.intervention._set_intervention_name(intervention_name)
        assert(self.intervention_dict.Intervention_Name==intervention_name)

    def test_get_intervention_name(self):
        """
        This method test the get_intervention_name method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        assert(self.intervention.get_intervention_name()==self.custom_intervention_name)

    def assert_get_intervention_name(self):
        """
        This method test the Warning raised when the intervention name is not a valid parameter, it only runs when it's explicitly called.
        """
        pytest.warns(Warning, self.intervention.get_intervention_name)


    def test_set_new_property_value(self):
        """
        This method test the set_new_property_value method of the IndividualIntervention class.
        Each subtest classes will run this test automatically unless it's overridden.
        """
        new_property_value = 'Risk:High'
        self.intervention._set_new_property_value(new_property_value)
        assert(self.intervention_dict.New_Property_Value==new_property_value)
        new_property_value_2 = ' Risk : High '
        self.intervention._set_new_property_value(new_property_value_2)
        assert(self.intervention_dict.New_Property_Value==new_property_value)

    def assert_set_cost(self):
        """
        This method test the ValueError raised when the cost is not a valid parameter, it only runs when it's explicitly called.
        """
        cost = 10.0
        with pytest.raises(Exception) as e_info:
            self.intervention._set_cost(cost)
        assert('not a valid parameter' in str(e_info))

    def assert_set_disqualifying_properties(self):
        """
        This method test the ValueError raised when the disqualifying properties is not a valid parameter, it only runs when it's explicitly called.
        """
        disqualifying_properties = ['age:30']
        with pytest.raises(Exception) as e_info:
            self.intervention._set_disqualifying_properties(disqualifying_properties)
        assert('not a valid parameter' in str(e_info))

    def assert_set_dont_allow_duplicates(self):
        """
        This method test the ValueError raised when the dont_allow_duplicates is not a valid parameter, it only runs when it's explicitly called.
        """
        with pytest.raises(Exception) as e_info:
            self.intervention._set_dont_allow_duplicates(True)
        assert('not a valid parameter' in str(e_info))

    def assert_set_intervention_name(self):
        """
        This method test the ValueError raised when the intervention name is not a valid parameter, it only runs when it's explicitly called.
        """
        intervention_name = 'TestName'
        with pytest.raises(Exception) as e_info:
            self.intervention._set_intervention_name(intervention_name)
        assert('not a valid parameter' in str(e_info))

    def assert_set_new_property_value(self):
        """
        This method test the ValueError raised when the new property value is not a valid parameter, it only runs when it's explicitly called.
        """
        new_property_value = 'Risk:High'
        with pytest.raises(Exception) as e_info:
            self.intervention._set_new_property_value(new_property_value)
        assert('not a valid parameter' in str(e_info))


@pytest.mark.unit
class TestBroadcastEvent(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_name = 'BroadcastEvent'
        self.broadcast_event = 'TestEvent'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = BroadcastEvent(self.campaign, self.broadcast_event, self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_name)
        assert(self.intervention_dict.Broadcast_Event==self.broadcast_event)
        self.assert_common_parameters(self.intervention_dict,None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_no_commom_parameters(self):
        intervention = BroadcastEvent(self.campaign, self.broadcast_event)
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_name)
        assert(intervention_dict.Broadcast_Event==self.broadcast_event)
        assert(intervention_dict.Disqualifying_Properties==[])
        assert(not intervention_dict.Dont_Allow_Duplicates)
        assert(intervention_dict.Intervention_Name==self.intervention_name)
        assert(intervention_dict.New_Property_Value=='')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestBroadcastEventToOtherNodes(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_name = 'BroadcastEventToOtherNodes'
        self.broadcast_event = 'TestEvent'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = BroadcastEventToOtherNodes(self.campaign, self.broadcast_event,
                                                       node_selection_type=NodeSelectionType.DISTANCE_ONLY,
                                                       max_distance_to_other_nodes_km=100,
                                                       include_my_node=True,
                                                       common_intervention_parameters=self.common_intervention_parameters
                                                       )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']=='BroadcastEventToOtherNodes')
        assert(self.intervention_dict.Event_Trigger==self.broadcast_event)
        assert(self.intervention_dict.Node_Selection_Type==NodeSelectionType.DISTANCE_ONLY.value)
        assert(self.intervention_dict.Max_Distance_To_Other_Nodes_Km==100)
        assert(self.intervention_dict.Include_My_Node)
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_init_Migration(self):
        intervention = BroadcastEventToOtherNodes(self.campaign, self.broadcast_event,
                                                  node_selection_type=NodeSelectionType.MIGRATION_NODES_ONLY,
                                                  include_my_node=False)
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_name)
        assert(intervention_dict.Event_Trigger==self.broadcast_event)
        assert(intervention_dict.Node_Selection_Type==NodeSelectionType.MIGRATION_NODES_ONLY.value)
        assert(not intervention_dict.Include_My_Node)

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestControlledVaccine(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'ControlledVaccine'
        self.waning_config = waning_config.Box(constant_effect=0.3, box_duration=50)
        self.intervention = ControlledVaccine(self.campaign,
                                              waning_config=self.waning_config,
                                              vaccine_type=VaccineType.AcquisitionBlocking,
                                              vaccine_take=0.9,
                                              expired_event_trigger='Vaccine_expired',
                                              efficacy_is_multiplicative=False,
                                              duration_to_wait_before_revaccination=365,
                                              distributed_event_trigger='Vaccine_distributed',
                                              common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Waning_Config=={'Box_Duration': 50,
                                                      'Initial_Effect': 0.3,
                                                      'class': 'WaningEffectBox'})
        assert(self.intervention_dict.Vaccine_Type==VaccineType.AcquisitionBlocking.value)
        assert(self.intervention_dict.Vaccine_Take==0.9)
        assert(self.intervention_dict.Expired_Event_Trigger=='Vaccine_expired')
        assert(not self.intervention_dict.Efficacy_Is_Multiplicative)
        assert(self.intervention_dict.Duration_To_Wait_Before_Revaccination==365)
        assert(self.intervention_dict.Distributed_Event_Trigger=='Vaccine_distributed')
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestDelayedIntervention(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'DelayedIntervention'
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = DelayedIntervention(self.campaign,
                                                intervention_to_distribute_at_delay_completion=inv_to_distribute,
                                                delay_period_distribution=ExponentialDistribution(180),
                                                common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(len(self.intervention_dict.Actual_IndividualIntervention_Configs)==1)
        assert(self.intervention_dict.Actual_IndividualIntervention_Configs[0]['class']=='BroadcastEvent')
        assert(self.intervention_dict.Delay_Period_Distribution=='EXPONENTIAL_DISTRIBUTION')
        assert(self.intervention_dict.Delay_Period_Exponential==180)
        assert(self.intervention_dict.Coverage==1.0)
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_constant_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=ConstantDistribution(365))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_class_name)
        assert(len(intervention_dict.Actual_IndividualIntervention_Configs)==1)
        assert(intervention_dict.Actual_IndividualIntervention_Configs[0]['class']=='BroadcastEvent')
        assert(intervention_dict.Delay_Period_Distribution=='CONSTANT_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Constant==365)
        assert(intervention_dict.Coverage==1.0)

    def test_uniform_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=inv_to_distribute,
                                           delay_period_distribution=UniformDistribution(180, 365))
        intervention_dict = intervention.to_schema_dict()
        assert(len(intervention_dict.Actual_IndividualIntervention_Configs)==1)
        assert(intervention_dict.Actual_IndividualIntervention_Configs[0]['class']=='BroadcastEvent')
        assert(intervention_dict.Delay_Period_Distribution=='UNIFORM_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Min==180)
        assert(intervention_dict.Delay_Period_Max==365)

    def test_lognormal_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=LogNormalDistribution(180, 0.5))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='LOG_NORMAL_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Log_Normal_Mu==180)
        assert(intervention_dict.Delay_Period_Log_Normal_Sigma==0.5)

    def test_gaussian_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=GaussianDistribution(180, 0.5))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='GAUSSIAN_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Gaussian_Mean==180)
        assert(intervention_dict.Delay_Period_Gaussian_Std_Dev==0.5)

    def test_weibull_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=WeibullDistribution(180, 0.5))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='WEIBULL_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Kappa==180)
        assert(intervention_dict.Delay_Period_Lambda==0.5)

    def test_poisson_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=PoissonDistribution(180))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='POISSON_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Poisson_Mean==180)

    def test_dual_constant_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=DualConstantDistribution(0.4, 365))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='DUAL_CONSTANT_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Proportion_0==0.4)
        assert(intervention_dict.Delay_Period_Peak_2_Value==365)

    def test_dual_exponential_delay(self):
        inv_to_distribute = BroadcastEvent(self.campaign, 'TestEvent')
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_to_distribute],
                                           delay_period_distribution=DualExponentialDistribution(0.2, 365, 730))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='DUAL_EXPONENTIAL_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Proportion_1==0.2)
        assert(intervention_dict.Delay_Period_Mean_1==365)
        assert(intervention_dict.Delay_Period_Mean_2==730)

    def test_delay_with_multi_iv(self):
        inv_be = BroadcastEvent(self.campaign, 'TestEvent')
        inv_oi = OutbreakIndividual(self.campaign, 10)
        intervention = DelayedIntervention(self.campaign,
                                           intervention_to_distribute_at_delay_completion=[inv_be, inv_oi],
                                           delay_period_distribution=DualExponentialDistribution(0.2, 365, 730))
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict.Delay_Period_Distribution=='DUAL_EXPONENTIAL_DISTRIBUTION')
        assert(intervention_dict.Delay_Period_Proportion_1==0.2)
        assert(intervention_dict.Delay_Period_Mean_1==365)
        assert(intervention_dict.Delay_Period_Mean_2==730)
        assert(intervention_dict.Actual_IndividualIntervention_Configs[0]['class']=='BroadcastEvent')
        assert(intervention_dict.Actual_IndividualIntervention_Configs[1]['class']=='OutbreakIndividual')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestIVCalendar(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'IVCalendar'
        self.common_intervention_parameters = CommonInterventionParameters(cost=1.5)
        sv = SimpleVaccine(self.campaign,
                           vaccine_take=0.99,
                           vaccine_type=VaccineType.AcquisitionBlocking,
                           waning_config=waning_config.Box(constant_effect=0.3, box_duration=50),
                           efficacy_is_multiplicative=True)

        age_prob_list = []
        age_prob_list.append(IVCalendar.AgeAndProbability(age_days=1, probability=1))
        age_prob_list.append(IVCalendar.AgeAndProbability(age_days=180, probability=0.5))
        age_prob_list.append(IVCalendar.AgeAndProbability(age_days=365, probability=0.25))

        self.intervention = IVCalendar(self.campaign,
                                       intervention_list=[sv],
                                       dropout=False,
                                       calendar=age_prob_list)
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = self.intervention_class_name

    def test_init(self):
        assert(self.intervention_class_name==self.intervention_dict['class'])
        assert(len(self.intervention_dict.Calendar)==3)
        assert(self.intervention_dict.Calendar[0].Age==1)
        assert(self.intervention_dict.Calendar[1].Age==180)
        assert(self.intervention_dict.Calendar[2].Age==365)
        assert(self.intervention_dict.Calendar[0].Probability==1.00)
        assert(self.intervention_dict.Calendar[1].Probability==0.50)
        assert(self.intervention_dict.Calendar[2].Probability==0.25)
        assert(len(self.intervention_dict.Actual_IndividualIntervention_Configs)==1)
        assert(self.intervention_dict.Actual_IndividualIntervention_Configs[0]['class']=='SimpleVaccine')
        assert(self.intervention_dict.Actual_IndividualIntervention_Configs[0].Vaccine_Type==VaccineType.AcquisitionBlocking)
        assert(self.intervention_dict.Actual_IndividualIntervention_Configs[0].Vaccine_Take==0.99)

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestIndividualImmunityChanger(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'IndividualImmunityChanger'
        self.common_intervention_parameters = CommonInterventionParameters(cost=1.5)
        self.intervention = IndividualImmunityChanger(self.campaign,
                                                      prime_transmit=0.1,
                                                      prime_acquire=0.3,
                                                      prime_mortality=0.5,
                                                      boost_transmit=0.2,
                                                      boost_acquire=0.4,
                                                      boost_mortality=0.6,
                                                      boost_threshold_transmit=0.7,
                                                      boost_threshold_acquire=0.8,
                                                      boost_threshold_mortality=0.9,
                                                      common_intervention_parameters=self.common_intervention_parameters
                                                      )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Prime_Transmit==0.1)
        assert(self.intervention_dict.Prime_Acquire==0.3)
        assert(self.intervention_dict.Prime_Mortality==0.5)
        assert(self.intervention_dict.Boost_Transmit==0.2)
        assert(self.intervention_dict.Boost_Acquire==0.4)
        assert(self.intervention_dict.Boost_Mortality==0.6)
        assert(self.intervention_dict.Boost_Threshold_Transmit==0.7)
        assert(self.intervention_dict.Boost_Threshold_Acquire==0.8)
        assert(self.intervention_dict.Boost_Threshold_Mortality==0.9)
        assert(self.intervention_dict.Cost_To_Consumer==1.5)

    def test_set_disqualifying_properties(self):
        self.assert_set_disqualifying_properties()

    def test_set_dont_allow_duplicates(self):
        self.assert_set_dont_allow_duplicates()

    def test_set_intervention_name(self):
        self.assert_set_intervention_name()

    def test_get_intervention_name(self):
        self.assert_get_intervention_name()

    def test_set_new_property_value(self):
        self.assert_set_new_property_value()


@pytest.mark.unit
class TestIndividualNonDiseaseDeathRateModifier(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'IndividualNonDiseaseDeathRateModifier'
        self.intervention = IndividualNonDiseaseDeathRateModifier(self.campaign,
                                                                  duration_to_modifier=ValueMap(times=[0, 365],
                                                                                                values=[1, 2]),
                                                                  expiration_event='Expired',
                                                                  expiration_duration_distribution=PoissonDistribution(4),
                                                                  common_intervention_parameters=self.common_intervention_parameters
                                                                  )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Duration_To_Modifier.Times==[0, 365])
        assert(self.intervention_dict.Duration_To_Modifier.Values==[1, 2])
        assert(self.intervention_dict.Expiration_Event=='Expired')
        assert(self.intervention_dict.Expiration_Duration_Distribution=='POISSON_DISTRIBUTION')
        assert(self.intervention_dict.Expiration_Duration_Poisson_Mean==4)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestMigrateIndividuals(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MigrateIndividuals'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:50'],
                                                                           dont_allow_duplicates=False,
                                                                           intervention_name='TestName2',
                                                                           new_property_value='Risk:Low')
        self.intervention = MigrateIndividuals(self.campaign,
                                               nodeid_to_migrate_to=1,
                                               is_moving=False,
                                               duration_before_leaving_distribution=GaussianDistribution(30, 0.5),
                                               duration_at_node_distribution=ConstantDistribution(365),
                                               common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = 'TestName2'

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.NodeID_To_Migrate_To==1)
        assert(not self.intervention_dict.Is_Moving)
        assert(self.intervention_dict.Duration_Before_Leaving_Distribution=='GAUSSIAN_DISTRIBUTION')
        assert(self.intervention_dict.Duration_Before_Leaving_Gaussian_Mean==30)
        assert(self.intervention_dict.Duration_Before_Leaving_Gaussian_Std_Dev==0.5)
        assert(self.intervention_dict.Duration_At_Node_Distribution=='CONSTANT_DISTRIBUTION')
        assert(self.intervention_dict.Duration_At_Node_Constant==365)
        self.assert_common_parameters(self.intervention_dict, None, ['age:50'], False, 'TestName2', 'Risk:Low')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
# todo: update when WaningEffect is ready
class TestMultiEffectBoosterVaccine(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MultiEffectBoosterVaccine'
        self.intervention = MultiEffectBoosterVaccine(self.campaign,
                                                      transmit_config=waning_config.Constant(constant_effect=0.1),
                                                      acquire_config=waning_config.MapLinear(times=[0, 365],
                                                                                             effects=[1, 0.5],
                                                                                             expire_at_durability_map_end=True,
                                                                                             effect_multiplier=0.2),
                                                      mortality_config=waning_config.BoxExponential(initial_effect=0.3,
                                                                                                    box_duration=365,
                                                                                                    decay_time_constant=0.1),
                                                      vaccine_take=0.7,
                                                      prime_acquire=0.8,
                                                      prime_transmit=0.9,
                                                      prime_mortality=1.0,
                                                      boost_acquire=0.1,
                                                      boost_transmit=0.6,
                                                      boost_mortality=0.3,
                                                      boost_threshold_acquire=0.4,
                                                      boost_threshold_transmit=0.5,
                                                      boost_threshold_mortality=0.6,
                                                      common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Transmit_Config=={'Initial_Effect': 0.1,
                                                        'class': 'WaningEffectConstant'})
        assert(self.intervention_dict.Acquire_Config=={'class': 'WaningEffectMapLinear',
                                                       'Durability_Map': {'Times': [0, 365],
                                                                          'Values': [1, 0.5]},
                                                       'Expire_At_Durability_Map_End': 1,
                                                       'Initial_Effect': 0.2,
                                                       'Reference_Timer': 0})  # todo: Reference_Timer is not used, remove it after we remove it from the schema
        assert(self.intervention_dict.Mortality_Config=={'Initial_Effect': 0.3,
                                                         'Box_Duration': 365,
                                                         'Decay_Time_Constant': 0.1,
                                                         'class': 'WaningEffectBoxExponential'})
        assert(self.intervention_dict.Vaccine_Take==0.7)
        assert(self.intervention_dict.Prime_Acquire==0.8)
        assert(self.intervention_dict.Prime_Transmit==0.9)
        assert(self.intervention_dict.Prime_Mortality==1.0)
        assert(self.intervention_dict.Boost_Acquire==0.1)
        assert(self.intervention_dict.Boost_Transmit==0.6)
        assert(self.intervention_dict.Boost_Mortality==0.3)
        assert(self.intervention_dict.Boost_Threshold_Acquire==0.4)
        assert(self.intervention_dict.Boost_Threshold_Transmit==0.5)
        assert(self.intervention_dict.Boost_Threshold_Mortality==0.6)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
# todo: update when WaningEffect is ready
class TestMultiEffectVaccine(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MultiEffectVaccine'
        self.intervention = MultiEffectVaccine(self.campaign,
                                               transmit_config=waning_config.Exponential(decay_time_constant=10,
                                                                                         initial_effect=0.1),
                                               acquire_config=waning_config.MapLinearAge(ages=[0, 30, 60],
                                                                                         effects=[1, 0.5, 0.2],
                                                                                         effect_multiplier=0.3),
                                               mortality_config=waning_config.MapLinearSeasonal(times=[0, 365],
                                                                                                effects=[1, 0.5],
                                                                                                effect_multiplier=0.4),
                                               vaccine_take=0.7,
                                               common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Transmit_Config=={'Decay_Time_Constant': 10,
                                                        'Initial_Effect': 0.1,
                                                        'class': 'WaningEffectExponential'})
        assert(self.intervention_dict.Acquire_Config=={'class': 'WaningEffectMapLinearAge',
                                                       'Durability_Map': {'Times': [0, 30, 60],
                                                                          'Values': [1, 0.5, 0.2]},
                                                       'Initial_Effect': 0.3})
        assert(self.intervention_dict.Mortality_Config=={'class': 'WaningEffectMapLinearSeasonal',
                                                         'Durability_Map': {'Times': [0, 365],
                                                                            'Values': [1, 0.5]},
                                                         'Initial_Effect': 0.4})
        assert(self.intervention_dict.Vaccine_Take==0.7)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestMultiInterventionDistributor(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MultiInterventionDistributor'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:30'],
                                                                           dont_allow_duplicates=False,
                                                                           intervention_name='TestName3',
                                                                           new_property_value='Risk:Low')
        self.intervention = MultiInterventionDistributor(self.campaign,
                                                         intervention_list=
                                                         [BroadcastEvent(self.campaign, 'TestEvent'),
                                                          IndividualImmunityChanger(self.campaign, prime_acquire=0.8)],
                                                         common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = 'TestName3'

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Intervention_List[0]['class']=='BroadcastEvent')
        assert(self.intervention_dict.Intervention_List[1]['class']=='IndividualImmunityChanger')
        self.assert_common_parameters(self.intervention_dict, None, ['age:30'], False, 'TestName3', 'Risk:Low')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestOutbreakIndividual(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'OutbreakIndividual'
        self.intervention = OutbreakIndividual(self.campaign,
                                               incubation_period_override=10,
                                               ignore_immunity=False,
                                               genome=1,
                                               antigen=2
                                               )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Incubation_Period_Override==10)
        assert(not self.intervention_dict.Ignore_Immunity)
        assert(self.intervention_dict.Genome==1)
        assert(self.intervention_dict.Antigen==2)

    def test_set_cost(self):
        self.assert_set_cost()

    def test_set_new_property_value(self):
        self.assert_set_new_property_value()

    def test_set_disqualifying_properties(self):
        self.assert_set_disqualifying_properties()

    def test_set_dont_allow_duplicates(self):
        self.assert_set_dont_allow_duplicates()

    def test_set_intervention_name(self):
        self.assert_set_intervention_name()

    def test_get_intervention_name(self):
        self.assert_get_intervention_name()


@pytest.mark.unit
class TestPropertyValueChanger(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'PropertyValueChanger'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:40'],
                                                                           dont_allow_duplicates=False,
                                                                           intervention_name='TestName4',
                                                                           new_property_value='Risk:Low')
        self.intervention = PropertyValueChanger(self.campaign,
                                                 target_property_value="High",
                                                 target_property_key="Risk",
                                                 revert=365,
                                                 maximum_duration=730,
                                                 daily_probability=0.8,
                                                 common_intervention_parameters=self.common_intervention_parameters
                                                 )
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = 'TestName4'

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Target_Property_Value=="High")
        assert(self.intervention_dict.Target_Property_Key=="Risk")
        assert(self.intervention_dict.Revert==365)
        assert(self.intervention_dict.Maximum_Duration==730)
        assert(self.intervention_dict.Daily_Probability==0.8)
        self.assert_common_parameters(self.intervention_dict, None, ['age:40'], False, 'TestName4', 'Risk:Low')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
# todo: update when WaningEffect is ready
class TestSimpleBoosterVaccine(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'SimpleBoosterVaccine'
        self.intervention = SimpleBoosterVaccine(self.campaign,
                                                 waning_config=waning_config.Combo(effect_list=[waning_config.Constant(constant_effect=0.1),
                                                                                                waning_config.Exponential(decay_time_constant=0.2,
                                                                                                                          initial_effect=0.5)],
                                                                                   add_effects=True,
                                                                                   expires_when_all_expire=True),
                                                 vaccine_type=VaccineType.TransmissionBlocking,
                                                 vaccine_take=0.9,
                                                 prime_effect=0.8,
                                                 boost_effect=0.7,
                                                 efficacy_is_multiplicative=False,
                                                 boost_threshold=0.6,
                                                 common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        expected_waning_config = {'Effect_List': [{'Initial_Effect': 0.1, 'class': 'WaningEffectConstant'},
                                                  {'class': 'WaningEffectExponential', 'Decay_Time_Constant': 0.2, 'Initial_Effect': 0.5}],
                                  'Add_Effects': 1,
                                  'Expires_When_All_Expire': 1,
                                  'class': 'WaningEffectCombo'}
        assert(self.intervention_dict.Waning_Config==expected_waning_config)
        assert(self.intervention_dict.Vaccine_Type==VaccineType.TransmissionBlocking.value)
        assert(self.intervention_dict.Vaccine_Take==0.9)
        assert(self.intervention_dict.Prime_Effect==0.8)
        assert(self.intervention_dict.Boost_Effect==0.7)
        assert(not self.intervention_dict.Efficacy_Is_Multiplicative)
        assert(self.intervention_dict.Boost_Threshold==0.6)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestSimpleDiagnostic(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'SimpleDiagnostic'
        self.intervention = _SimpleDiagnostic(self.campaign,
                                              positive_diagnosis_config=BroadcastEvent(self.campaign, 'PositiveDiagnosis'),
                                              treatment_fraction=0.9,
                                              enable_is_symptomatic=True,
                                              days_to_diagnosis=4,
                                              base_sensitivity=0.9,
                                              base_specificity=0.95,
                                              common_intervention_parameters=self.common_intervention_parameters
                                              )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Positive_Diagnosis_Config['class']=='BroadcastEvent')
        assert(self.intervention_dict.Treatment_Fraction==0.9)
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Config)
        assert(self.intervention_dict.Enable_Is_Symptomatic)
        assert(self.intervention_dict.Days_To_Diagnosis==4)
        assert(self.intervention_dict.Base_Sensitivity==0.9)
        assert(self.intervention_dict.Base_Specificity==0.95)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')

    def test_init_event(self):
        intervention = _SimpleDiagnostic(self.campaign,
                                         positive_diagnosis_event='PositiveDiagnosis',
                                         treatment_fraction=0.99,
                                         enable_is_symptomatic=False,
                                         days_to_diagnosis=3,
                                         base_sensitivity=0.98,
                                         base_specificity=0.97
                                         )
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_class_name)
        assert(intervention_dict.Positive_Diagnosis_Event=='PositiveDiagnosis')
        assert(intervention_dict.Treatment_Fraction==0.99)
        assert(intervention_dict.Event_Or_Config==EventOrConfig.Event)
        assert(not intervention_dict.Enable_Is_Symptomatic)
        assert(intervention_dict.Days_To_Diagnosis==3)
        assert(intervention_dict.Base_Sensitivity==0.98)
        assert(intervention_dict.Base_Specificity==0.97)

    def test_init_no_commom_intervention(self):
        intervention = _SimpleDiagnostic(self.campaign, positive_diagnosis_event='PositiveDiagnosis')
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_class_name)
        assert(intervention_dict.Positive_Diagnosis_Event=='PositiveDiagnosis')
        assert(intervention_dict.Treatment_Fraction==1)
        assert(intervention_dict.Event_Or_Config==EventOrConfig.Event)
        assert(not intervention_dict.Enable_Is_Symptomatic)
        assert(intervention_dict.Days_To_Diagnosis==0)
        assert(intervention_dict.Base_Sensitivity==1)
        assert(intervention_dict.Base_Specificity==1)
        assert(intervention_dict.Cost_To_Consumer==1)
        assert(intervention_dict.Disqualifying_Properties==[])
        assert(not intervention_dict.Dont_Allow_Duplicates)
        assert(intervention_dict.Intervention_Name==self.intervention_class_name)
        assert(intervention_dict.New_Property_Value=='')


@pytest.mark.unit
class TestSimpleHealthSeekingBehavior(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'SimpleHealthSeekingBehavior'
        self.common_intervention_parameters= CommonInterventionParameters(disqualifying_properties=['age:50'],
                                                                          dont_allow_duplicates=False,
                                                                          intervention_name='TestName5',
                                                                          new_property_value='Risk:Low')
        self.intervention = _SimpleHealthSeekingBehavior(self.campaign,
                                                         intervention_config=
                                                         BroadcastEvent(self.campaign,
                                                                        "SeekHealthTreatment"),
                                                         tendency=0.8,
                                                         single_use=False,
                                                         common_intervention_parameters=self.common_intervention_parameters
                                                         )
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = 'TestName5'

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_IndividualIntervention_Config['class']=='BroadcastEvent')
        assert(self.intervention_dict.Actual_IndividualIntervention_Config.Broadcast_Event=='SeekHealthTreatment')
        assert(self.intervention_dict.Tendency==0.8)
        assert(not self.intervention_dict.Single_Use)
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Config)
        self.assert_common_parameters(self.intervention_dict, None, ['age:50'], False, 'TestName5', 'Risk:Low')

    def test_init_event(self):
        intervention = _SimpleHealthSeekingBehavior(self.campaign,
                                                    intervention_event="SeekHealthTreatment",
                                                    tendency=0.9,
                                                    single_use=True
                                                    )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_IndividualIntervention_Event=="SeekHealthTreatment")
        assert(self.intervention_dict.Tendency==0.9)
        assert(self.intervention_dict.Single_Use)
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Event)

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestSimpleVaccine(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'SimpleVaccine'
        self.intervention = SimpleVaccine(self.campaign,
                                          waning_config=waning_config.MapPiecewise(days=[0, 365],
                                                                                   effects=[1, 0.5],
                                                                                   effect_multiplier=0.2,
                                                                                   expire_at_durability_map_end=True),
                                          vaccine_type=VaccineType.AcquisitionBlocking,
                                          vaccine_take=0.9,
                                          efficacy_is_multiplicative=False,
                                          common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Waning_Config=={'class': 'WaningEffectMapPiecewise',
                                                      'Durability_Map': {'Times': [0, 365],
                                                                         'Values': [1, 0.5]},
                                                      'Expire_At_Durability_Map_End': 1,
                                                      'Initial_Effect': 0.2,
                                                      'Reference_Timer': 0})  # todo: Reference_Timer is not used, remove it after we remove it from the schema
        assert(self.intervention_dict.Vaccine_Type==VaccineType.AcquisitionBlocking.value)
        assert(self.intervention_dict.Vaccine_Take==0.9)
        assert(not self.intervention_dict.Efficacy_Is_Multiplicative)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestStandardDiagnostic(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'StandardDiagnostic'
        self.intervention = StandardDiagnostic(self.campaign,
                                               positive_diagnosis_config=BroadcastEvent(self.campaign, 'PositiveDiagnosis'),
                                               negative_diagnosis_config=BroadcastEvent(self.campaign, 'NegativeDiagnosis'),
                                               enable_is_symptomatic=True,
                                               days_to_diagnosis=4,
                                               treatment_fraction=0.89,
                                               base_sensitivity=0.9,
                                               base_specificity=0.95,
                                               common_intervention_parameters=self.common_intervention_parameters
                                               )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Positive_Diagnosis_Config['class']=='BroadcastEvent')
        assert(self.intervention_dict.Positive_Diagnosis_Config.Broadcast_Event=='PositiveDiagnosis')
        assert(self.intervention_dict.Negative_Diagnosis_Config['class']=='BroadcastEvent')
        assert(self.intervention_dict.Negative_Diagnosis_Config.Broadcast_Event=='NegativeDiagnosis')
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Config)
        assert(self.intervention_dict.Enable_Is_Symptomatic)
        assert(self.intervention_dict.Days_To_Diagnosis==4)
        assert(self.intervention_dict.Base_Sensitivity==0.9)
        assert(self.intervention_dict.Base_Specificity==0.95)
        assert(self.intervention_dict.Treatment_Fraction==0.89)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')

    def test_init_event(self):
        intervention = StandardDiagnostic(self.campaign,
                                          positive_diagnosis_event='PositiveDiagnosis',
                                          negative_diagnosis_event='NegativeDiagnosis',
                                          enable_is_symptomatic=False,
                                          days_to_diagnosis=3,
                                          base_sensitivity=0.98,
                                          base_specificity=0.97
                                          )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Positive_Diagnosis_Event=='PositiveDiagnosis')
        assert(self.intervention_dict.Negative_Diagnosis_Event=='NegativeDiagnosis')
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Event)
        assert(not self.intervention_dict.Enable_Is_Symptomatic)
        assert(self.intervention_dict.Days_To_Diagnosis==3)
        assert(self.intervention_dict.Base_Sensitivity==0.98)
        assert(self.intervention_dict.Base_Specificity==0.97)
        assert(self.intervention_dict.Treatment_Fraction==1)

    def test_init_positive_event(self):
        intervention = StandardDiagnostic(self.campaign,
                                          positive_diagnosis_event='PositiveDiagnosis',
                                          enable_is_symptomatic=False,
                                          days_to_diagnosis=4,
                                          base_sensitivity=0.77,
                                          base_specificity=0.66
                                          )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Positive_Diagnosis_Event=='PositiveDiagnosis')
        assert(self.intervention_dict.Negative_Diagnosis_Event=='')
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Event)
        assert(not self.intervention_dict.Enable_Is_Symptomatic)
        assert(self.intervention_dict.Days_To_Diagnosis==4)
        assert(self.intervention_dict.Base_Sensitivity==0.77)
        assert(self.intervention_dict.Base_Specificity==0.66)

    def test_init_positive_config(self):
        intervention = StandardDiagnostic(self.campaign,
                                          positive_diagnosis_config=BroadcastEvent(self.campaign, 'PositiveDiagnosis'),
                                          enable_is_symptomatic=True,
                                          days_to_diagnosis=4,
                                          base_sensitivity=0.9,
                                          base_specificity=0.95,
                                          common_intervention_parameters=self.common_intervention_parameters
                                          )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Positive_Diagnosis_Config['class']=='BroadcastEvent')
        assert(self.intervention_dict.Positive_Diagnosis_Config.Broadcast_Event=='PositiveDiagnosis')
        assert(self.intervention_dict.Negative_Diagnosis_Config=={})
        assert(self.intervention_dict.Event_Or_Config==EventOrConfig.Config)
        assert(self.intervention_dict.Enable_Is_Symptomatic)
        assert(self.intervention_dict.Days_To_Diagnosis==4)
        assert(self.intervention_dict.Base_Sensitivity==0.9)
        assert(self.intervention_dict.Base_Specificity==0.95)
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestNodeIntervention(TestIndividualIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        """
        This method is called before each test, it initializes the Intervention class and the intervention class name.
        Each subtest classes should override this function for its own.
        """
        self.intervention_class_name = 'BroadcastNodeEvent'
        self.intervention = NodeIntervention(self.campaign, self.intervention_class_name,
                                             self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()


@pytest.mark.unit
class TestMultiNodeInterventionDistributor(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MultiNodeInterventionDistributor'
        intervention_list = [
            Outbreak(self.campaign),
            BroadcastNodeEvent(self.campaign, broadcast_event='TestNodeEvent')]
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = MultiNodeInterventionDistributor(self.campaign,
                                                             node_intervention_list=intervention_list,
                                                             common_intervention_parameters=
                                                             self.common_intervention_parameters
                                                             )
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Node_Intervention_List[0]['class']=='Outbreak')
        assert(self.intervention_dict.Node_Intervention_List[1]['class']=='BroadcastNodeEvent')
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestNodeLevelHealthTriggeredIV(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'NodeLevelHealthTriggeredIV'
        self.intervention = _NodeLevelHealthTriggeredIV(self.campaign,
                                                        intervention_list=[Outbreak(self.campaign)],
                                                        trigger_condition_list=["TestTrigger"]
                                                       )
        self.intervention_dict = self.intervention.to_schema_dict()
        self.custom_intervention_name = self.intervention_class_name

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_NodeIntervention_Config['class']=='Outbreak')
        assert(self.intervention_dict.Trigger_Condition_List==["TestTrigger"])

    def test_node_intervention(self):
        intervention = _NodeLevelHealthTriggeredIV(self.campaign,
                                                   intervention_list=[Outbreak(self.campaign)],
                                                   trigger_condition_list=["TestTrigger"]
                                                   )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_IndividualIntervention_Config=={})
        assert(self.intervention_dict.Actual_NodeIntervention_Config['class']=='Outbreak')
        assert(self.intervention_dict.Trigger_Condition_List==["TestTrigger"])
        assert(self.intervention_dict.Property_Restrictions_Within_Node==[])
        assert(self.intervention_dict.Node_Property_Restrictions==[])
        assert(self.intervention_dict.Targeting_Config=={})

    def test_multi_node_intervention(self):
        intervention = _NodeLevelHealthTriggeredIV(self.campaign,
                                                   intervention_list=[Outbreak(self.campaign),
                                                                      BroadcastNodeEvent(self.campaign,
                                                                                              'TestNodeEvent')],
                                                   trigger_condition_list=["TestTrigger"]
                                                   )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_IndividualIntervention_Config=={})
        assert(self.intervention_dict.Actual_NodeIntervention_Config['class']=='MultiNodeInterventionDistributor')
        assert(self.intervention_dict.Actual_NodeIntervention_Config.Node_Intervention_List[0]['class']=='Outbreak')
        assert(self.intervention_dict.Actual_NodeIntervention_Config.Node_Intervention_List[1]['class']=='BroadcastNodeEvent')
        assert(self.intervention_dict.Trigger_Condition_List==["TestTrigger"])

    def test_individual_intervention(self):
        intervention = _NodeLevelHealthTriggeredIV(self.campaign,
                                                   intervention_list=[OutbreakIndividual(self.campaign)],
                                                   trigger_condition_list=["TestTrigger"],
                                                   target_demographics_config=TargetDemographicsConfig(
                                                       demographic_coverage=0.5,
                                                       target_age_min=10,
                                                       target_age_max=20),
                                                   targeting_config=~IsPregnant(),
                                                   property_restrictions=PropertyRestrictions(
                                                       individual_property_restrictions=[["risk:HIGH"]]),
                                                   )
        self.intervention_dict = intervention.to_schema_dict()
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Actual_NodeIntervention_Config=={})
        assert(self.intervention_dict.Actual_IndividualIntervention_Config['class']=='OutbreakIndividual')
        assert(self.intervention_dict.Trigger_Condition_List==["TestTrigger"])
        assert(self.intervention_dict.Demographic_Coverage==0.5)
        assert(self.intervention_dict.Target_Age_Min==10)
        assert(self.intervention_dict.Target_Age_Max==20)
        assert(self.intervention_dict.Property_Restrictions_Within_Node==[{"risk": "HIGH"}])
        assert(self.intervention_dict.Targeting_Config=={'Is_Equal_To': 0, 'class': 'IsPregnant'})


    def test_multi_individual_intervention(self):
        intervention = _NodeLevelHealthTriggeredIV(self.campaign,
                                                   intervention_list=[OutbreakIndividual(self.campaign),
                                                                      BroadcastEvent(self.campaign,
                                                                                         'TestIndividualEvent')],
                                                   trigger_condition_list=["TestTrigger"]
                                                   )
        intervention_dict = intervention.to_schema_dict()
        assert(intervention_dict['class']==self.intervention_class_name)
        assert(intervention_dict.Actual_NodeIntervention_Config=={})
        assert(intervention_dict.Actual_IndividualIntervention_Config['class']=='MultiInterventionDistributor')
        assert(intervention_dict.Actual_IndividualIntervention_Config.Intervention_List[0]['class']=='OutbreakIndividual')
        assert(intervention_dict.Actual_IndividualIntervention_Config.Intervention_List[1]['class']=='BroadcastEvent')
        assert(intervention_dict.Trigger_Condition_List==["TestTrigger"])

    def test_set_cost(self):
        self.assert_set_cost()

    def test_node_intervention_individual_targeting(self):
        with pytest.raises(Exception) as e_info:
            iv = _NodeLevelHealthTriggeredIV(self.campaign,
                                             intervention_list=[Outbreak(self.campaign)],
                                             trigger_condition_list=["TestTrigger"],
                                             target_demographics_config=TargetDemographicsConfig(
                                             demographic_coverage=0.5,
                                             target_age_min=10,
                                             target_age_max=20),
                                             targeting_config=IsPregnant(),
                                             property_restrictions=PropertyRestrictions(
                                             individual_property_restrictions=[["risk:HIGH"]]))
        assert('is a node-level intervention, so it will be distributed to nodes.' in str(e_info))


@pytest.mark.unit
class TestBroadcastCoordinatorEventFromNode(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'BroadcastCoordinatorEventFromNode'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = _BroadcastCoordinatorEventFromNode(self.campaign, broadcast_event='TestEvent',
                                                               common_intervention_parameters=
                                                              self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Broadcast_Event=='TestEvent')
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestBroadcastNodeEvent(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'BroadcastNodeEvent'
        self.intervention = BroadcastNodeEvent(self.campaign, broadcast_event='TestNodeEvent',
                                               common_intervention_parameters=
                                               self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Broadcast_Event=='TestNodeEvent')
        self.assert_common_parameters(self.intervention_dict, 0.5, ['age:20'], True, 'TestName', 'Risk:High')


@pytest.mark.unit
class TestImportPressure(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'ImportPressure'
        self.intervention = ImportPressure(self.campaign, import_age=365, genome=0, durations=[30],
                                           daily_import_pressures=[0.1], antigen=1)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Import_Age==365)
        assert(self.intervention_dict.Genome==0)
        assert(self.intervention_dict.Durations==[30])
        assert(self.intervention_dict.Daily_Import_Pressures==[0.1])
        assert(self.intervention_dict.Antigen==1)

    def test_set_cost(self):
        self.assert_set_cost()

    def test_set_new_property_value(self):
        self.assert_set_new_property_value()

    def test_set_disqualifying_properties(self):
        self.assert_set_disqualifying_properties()

    def test_set_dont_allow_duplicates(self):
        self.assert_set_dont_allow_duplicates()

    def test_set_intervention_name(self):
        self.assert_set_intervention_name()

    def test_get_intervention_name(self):
        self.assert_get_intervention_name()


@pytest.mark.unit
class TestMigrateFamily(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'MigrateFamily'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = MigrateFamily(self.campaign, nodeid_to_migrate_to=1, is_moving=True,
                                          duration_before_leaving_distribution=LogNormalDistribution(30, 0.5),
                                          duration_at_node_distribution=WeibullDistribution(2, 4),
                                          common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.NodeID_To_Migrate_To==1)
        assert(self.intervention_dict.Is_Moving)
        assert(self.intervention_dict.Duration_Before_Leaving_Distribution=='LOG_NORMAL_DISTRIBUTION')
        assert(self.intervention_dict.Duration_Before_Leaving_Log_Normal_Mu==30)
        assert(self.intervention_dict.Duration_Before_Leaving_Log_Normal_Sigma==0.5)
        assert(self.intervention_dict.Duration_At_Node_Distribution=='WEIBULL_DISTRIBUTION')
        assert(self.intervention_dict.Duration_At_Node_Kappa==2)
        assert(self.intervention_dict.Duration_At_Node_Lambda==4)
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestNodePropertyValueChanger(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'NodePropertyValueChanger'
        self.common_intervention_parameters = CommonInterventionParameters(disqualifying_properties=['age:20'],
                                                                           dont_allow_duplicates=True,
                                                                           intervention_name='TestName',
                                                                           new_property_value='Risk:High')
        self.intervention = NodePropertyValueChanger(self.campaign, target_np_key_value="TestKey:TestValue",
                                                     revert=365, maximum_duration=730, daily_probability=0.8,
                                                     common_intervention_parameters=self.common_intervention_parameters)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Target_NP_Key_Value=="TestKey:TestValue")
        assert(self.intervention_dict.Revert==365)
        assert(self.intervention_dict.Maximum_Duration==730)
        assert(self.intervention_dict.Daily_Probability==0.8)
        self.assert_common_parameters(self.intervention_dict, None, ['age:20'], True, 'TestName', 'Risk:High')

    def test_set_cost(self):
        self.assert_set_cost()


@pytest.mark.unit
class TestOutbreak(TestNodeIntervention):
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        # Pre-test
        self.intervention_class_name = 'Outbreak'
        self.intervention = Outbreak(self.campaign, probability_of_infection=0.5, number_cases_per_node=10,
                                     import_age=365, genome=1, antigen=2)
        self.intervention_dict = self.intervention.to_schema_dict()

    def test_init(self):
        assert(self.intervention_dict['class']==self.intervention_class_name)
        assert(self.intervention_dict.Probability_Of_Infection==0.5)
        assert(self.intervention_dict.Number_Cases_Per_Node==10)
        assert(self.intervention_dict.Import_Age==365)
        assert(self.intervention_dict.Genome==1)
        assert(self.intervention_dict.Antigen==2)

    def test_set_cost(self):
        self.assert_set_cost()

    def test_set_new_property_value(self):
        self.assert_set_new_property_value()

    def test_set_disqualifying_properties(self):
        self.assert_set_disqualifying_properties()

    def test_set_dont_allow_duplicates(self):
        self.assert_set_dont_allow_duplicates()

    def test_set_intervention_name(self):
        self.assert_set_intervention_name()

    def test_get_intervention_name(self):
        self.assert_set_intervention_name()
