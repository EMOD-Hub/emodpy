"""
The following classes can be used to enhance the selection of people when distributing
interventions. Most event coordinators and node-level interventions that distribute
interventions to people have a parameter called Targeting_Config. This allows you to
not only target individuals based on their gender, age, and IndividualProperties
(See NodeProperties and IndividualProperties parameters for more information), but
also on things such as whether or not they have a particular intervention or are in
a relationship.

Below is the JSON for a simple example where we want to distribute a vaccine to 20%
of the people that do not already have the vaccine on the 100th day of the simulation.

    >>> {
    >>>     "class": "CampaignEvent",
    >>>     "Start_Day": 100,
    >>>     "Nodeset_Config": {
    >>>         "class": "NodeSetAll"
    >>>     },
    >>>     "Event_Coordinator_Config": {
    >>>         "class": "StandardInterventionDistributionEventCoordinator",
    >>>         "Target_Demographic": "Everyone",
    >>>         "Demographic_Coverage": 0.2,
    >>>         "Targeting_Config": {
    >>>             "class": "HasIntervention",
    >>>             "Is_Equal_To": 0,
    >>>             "Intervention_Name": "MyVaccine"
    >>>         },
    >>>         "Intervention_Config": {
    >>>             "class": "SimpleVaccine",
    >>>             "Intervention_Name" : "MyVaccine",
    >>>             "Cost_To_Consumer": 1,
    >>>             "Vaccine_Take": 1,
    >>>             "Vaccine_Type": "AcquisitionBlocking",
    >>>             "Waning_Config": {
    >>>                 "class": "WaningEffectConstant",
    >>>                 "Initial_Effect" : 1.0
    >>>             }
    >>>         }
    >>>     }
    >>> }

Below is a slightly more complicated example where we want to distribute a diagnostic
to people that are either high risk or have not been vaccinated.

    >>> {
    >>>     "class": "CampaignEvent",
    >>>     "Start_Day": 100,
    >>>     "Nodeset_Config": {
    >>>         "class": "NodeSetAll"
    >>>     },
    >>>     "Event_Coordinator_Config": {
    >>>         "class": "StandardInterventionDistributionEventCoordinator",
    >>>         "Target_Demographic": "Everyone",
    >>>         "Demographic_Coverage": 0.2,
    >>>         "Targeting_Config": {
    >>>             "class" : "TargetingLogic",
    >>>             "Logic" : [
    >>>                 [
    >>>                     {
    >>>                         "class": "HasIntervention",
    >>>                         "Is_Equal_To": 0,
    >>>                         "Intervention_Name": "MyVaccine"
    >>>                     }
    >>>                 ],
    >>>                 [
    >>>                     {
    >>>                         "class": "HasIP",
    >>>                         "Is_Equal_To": 1,
    >>>                         "IP_Key_Value": "Risk:HIGH"
    >>>                     }
    >>>                 ]
    >>>             ]
    >>>         },
    >>>         "Intervention_Config": {
    >>>             "class": "SimpleDiagnostic",
    >>>             "Treatment_Fraction": 1.0,
    >>>             "Base_Sensitivity": 1.0,
    >>>             "Base_Specificity": 1.0,
    >>>             "Event_Or_Config": "Event",
    >>>             "Positive_Diagnosis_Event": "TestedPositive"
    >>>         }
    >>>     }
    >>> }

The classes of emodpy are intended to make it easier for users to create complex logic and
reduce the burden of trying to create this complex logic in JSON.  Below is the python
configuration logic for the two examples above:

    >>> # Example 1: Does not have MyVaccine
    >>> targeting_config = ~HasIntervention( intervention_name="MyVaccine" )
    >>>
    >>> # Example 2: Does not have MyVaccine OR is high risk
    >>> targeting_config = ~HasIntervention( intervention_name="MyVaccine" ) | HasIP( ip_key_value="Risk:HIGH" )

Notice that this logic uses the bitwise operators instead of the logical operators.
Python does not allow you to override the logical operators so the bitwise operators
were the next best thing to allow simple notation.  The bitwise operators are:

    * '~' - use instead of "not" to logically invert the logical check
    * '&' - use instead of "and" to logically AND two logical checks
    * '|' - use instead of "or" to logically OR two logical checks
    * '^' - XOR - NOT SUPPORTED
    * '<<' - Left Shift - NOT SUPPORTED
    * '>>' - Right Shift - NOT SUPPORTED

The order of operations for bitwise operators is the same as for logical operators.
For the operators we support, the following order of operations is followed:

    1) Parentheses
    2) '~' - NOT
    3) '&' - AND
    4) '|' - OR

Please note that the bitwise operations should not change objects directly.  You expect
them to return a new object with the operation.  For example, if you have A_prime = ~A,
then you expect A_prime to be the inverse of A but you don't expect A to have changed.
"""

import copy
from abc import ABC
from abc import abstractmethod
import emod_api.schema_to_class as s2c
from emodpy.utils import validate_key_value_pair, validate_intervention_name


class AbstractTargetingConfig(ABC):
    """
    The AbstractTargetingConfig is defines the interface that all targeting config
    classes must implement.  This class is needed to tie the TargetingLogic and
    BaseTargetingConfig classes together.

    class_name: The subclass is responsible for setting the name of the EMOD class.
        This name does not need to be the same as the python class, but it must
        match what is used in EMOD.

    is_equal_to:
        This is a parameter in all of EMOD's Targeting_Config classes.  The check
        performed by the class is compared with the value of this parameter.
        For example, if using HasIP with ip_key_value = "Risk:HIGH" and
        is_equal_to = 0, individuals who do NOT have Risk = HIGH will be selected.
        If is_equal_to = 1, then individuals who DO have Risk = HIGH will be selected.
    """
    def __init__(self):
        self.class_name = "Unknown"
        self.is_equal_to = 1

    @abstractmethod
    def __eq__(self, other):
        """
        Return true if the 'other' object has the same set and values of internal variables.
        """
        pass

    def __invert__(self):
        """
        Return a new object with the reverse equality using the '~' operator.
        """
        copy_obj = copy.deepcopy(self)
        copy_obj.is_equal_to = 0 if copy_obj.is_equal_to == 1 else 1
        return copy_obj

    @abstractmethod
    def __and__(self, right):
        """
        Return a new object that contains the logical and'ing of this object with
        the object on the right of the '&' operand.
        """
        pass

    @abstractmethod
    def __or__(self, right):
        """
        Return a new object that contains the logical or'ing of this object with
        the object on the right of the '|' operand.
        """
        pass

    def __xor__(self, value):
        """
        NOT SUPPORTED
        """
        raise ValueError("The '^' (XOR) operator is not supported.")

    def __lshift__(self, value):
        """
        NOT SUPPORTED
        """
        raise ValueError("The '<<' (left shift) operator is not supported.")

    def __rshift__(self, value):
        """
        NOT SUPPORTED
        """
        raise ValueError("The '>>' (right shift) operator is not supported.")

    def to_schema_dict(self, campaign):
        """
        Create the ReadOnlyDict object representation of this Targeting_Config logic.
        This is the dictionary used to generate the JSON for EMOD.

        Args:
            campaign (api_campaign): The campaign module that has the path to the schema

        Returns:
            (ReadOnlyDict): Dict object created by schema_to_class
        """
        tc_obj = s2c.get_class_with_defaults(self.class_name, schema_json=campaign.get_schema())
        tc_obj.Is_Equal_To = self.is_equal_to
        return tc_obj

    def _clean_dict(self, read_only_dict):
        """
        Convert the ReadOnlyDict to a standard dictionary and strip extra stuff
        like 'schema' and 'explicits' so that it looks like the JSON for EMOD.
        """
        ret_dict = dict(read_only_dict)
        ret_dict.pop("schema")
        if "explicits" in ret_dict:
            ret_dict.pop("explicits")
        if "implicits" in ret_dict:
            ret_dict.pop("implicits")
        return ret_dict

    def to_simple_dict(self, campaign):
        """
        Return a plain/simple dictionary of the expected JSON for EMOD.  The main
        purpose of this is for validation in testing.  We need the ability to see
        that the logic written in python is translated to the JSON correctly.

        Args:
            campaign (api_campaign): The campaign module that has the path to the schema

        Returns:
            (dict): A dictionary containing the data for EMOD.
        """
        tc_obj = self.to_schema_dict(campaign)
        tc_dict = self._clean_dict(tc_obj)
        return tc_dict


class _TargetingLogic(AbstractTargetingConfig):
    """
    TargetingLogic is a class of EMOD, but users do not need to interact with directly.
    The BaseTargetingConfig class should take care of all of the users needs for TargetingLogic.
    Hence, we make this private so that they do not use it.

    TargetingLogic allows the user to logically combine different checks.  We leverage bitwise
    operators to make the syntax of combining different checks low and straight forward.

    NOTE: We put the initial and'ing and or'ing in the constructor to reduce the amount of
    object creation and to stop a situation where we would end up with a nested TargetingLogic
    element that only had one element.  See the "deeply nested" test in test_targeting_config.py.

    Args:
        is_and: If true, initialize the TargetingLogic object such that 'left' and 'right' are AND'd
            together.  If false, initialize it such that they are OR'd.
        left: The targeting config object on the left side of the operator
        right: The targeting config object on the right side of the operator
    """
    def __init__(self, is_and: bool, left: AbstractTargetingConfig, right: AbstractTargetingConfig):
        super().__init__()
        self.class_name = "TargetingLogic"
        self.logic = []
        if is_and:
            inner = []
            inner.append(left)
            inner.append(right)
            self.logic.append(inner)
        else:
            inner_left = []
            inner_left.append(left)
            inner_right = []
            inner_right.append(right)
            self.logic.append(inner_left)
            self.logic.append(inner_right)

    def __eq__(self, other):
        """
        Return true if the 'other' object has the same set and values of internal variables.
        """
        if not isinstance(other, _TargetingLogic):
            return False
        else:
            return self.__dict__ == other.__dict__

    def __and__(self, right):
        """
        Return a new object that contains the logical and'ing of this object with
        the object on the right of the '&' operand.
        """
        if not isinstance(right, AbstractTargetingConfig):
            raise ValueError("The object on the right of the '&' is not of type 'AbstractTargetingConfig'.")

        if self.is_equal_to == 0:
            # ------------------------------------------------------------------------------------------
            # --- !!!Inversion and TargetingLogic!!!
            # --- When TargetingLogic as is_equal_to = 0, the easiest thing for us to do is to keep its
            # --- contents constant and not add to it.  If we try to add to it, we need to do the "math"
            # --- to add the new logic.  This "math" would require reordering the existing components
            # --- and if the existing components are also TargetingLogic, it just gets more complicated
            # --- than keeping it as is.  For example, A | ~(B & C).  We can't just move the A into the
            # --- TargetingLogic on the right because of the '~'.  To revert the '~', we would need to
            # --- change ~(B & C) to ~B | ~C.  This seems more involved than we need to be.
            # ------------------------------------------------------------------------------------------
            tl = _TargetingLogic(is_and=True, left=self, right=right)
            return tl
        elif isinstance(right, _TargetingLogic) and right.is_equal_to == 1:
            copy_obj = copy.deepcopy(self)
            left = copy.deepcopy(copy_obj)
            copy_obj.logic.clear()
            inner = []
            inner.append(left)
            inner.append(right)
            copy_obj.logic.append(inner)
            return copy_obj
        else:
            copy_obj = copy.deepcopy(self)
            for inner_list in copy_obj.logic:
                inner_list.append(right)
            return copy_obj

    def __or__(self, right):
        """
        Return a new object that contains the logical or'ing of this object with
        the object on the right of the '|' operand.
        """
        if not isinstance(right, AbstractTargetingConfig):
            raise ValueError("The object on the right of the '|' is not of type 'AbstractTargetingConfig'.")

        if self.is_equal_to == 0:
            # See !!!Inversion and TargetingLogic!!! above
            tl = _TargetingLogic(is_and=False, left=self, right=right)
            return tl
        elif isinstance(right, _TargetingLogic) and right.is_equal_to == 1:
            copy_obj = copy.deepcopy(self)
            copy_obj.logic.extend(right.logic)
            return copy_obj
        else:
            copy_obj = copy.deepcopy(self)
            inner = []
            inner.append(right)
            copy_obj.logic.append(inner)
            return copy_obj

    def pre_and(self, left):
        """
        Return a new object that is "and'd" with the object to the left of the '&' operator
        """
        copy_obj = copy.deepcopy(self)
        for inner in copy_obj.logic:
            inner.insert(0, left)
        return copy_obj

    def pre_or(self, left):
        """
        Return a new object that is "or'd" with the object to the left of the '|' operator
        """
        copy_obj = copy.deepcopy(self)
        inner = []
        inner.append(left)
        copy_obj.logic.insert(0, inner)
        return copy_obj

    def to_schema_dict(self, campaign):
        """
        Create the ReadOnlyDict object representation of this Targeting_Config logic.
        This is the dictionary used to generate the JSON for EMOD.

        Args:
            campaign: The campaign module that has the path to the schema

        Returns:
            A ReadOnlyDict object created by schema_to_class
        """
        tc_out = super().to_schema_dict(campaign)
        tc_out.Logic = []
        for inner_list in self.logic:
            inner_list_out = []
            for inner_obj in inner_list:
                inner_list_out.append(inner_obj.to_schema_dict(campaign))
            tc_out.Logic.append(inner_list_out)
        return tc_out

    def _convert_logic_to_dict(self, tc_dict):
        """
        Convert the elements of the 'Logic' array to standard dictionaries.
        """
        logic_list = []
        for inner_list in tc_dict["Logic"]:
            inner_list_out = []
            for inner_obj in inner_list:
                inner_obj = self._clean_dict(inner_obj)
                if inner_obj["class"] == "TargetingLogic":
                    inner_obj = self._convert_logic_to_dict(inner_obj)
                inner_list_out.append(inner_obj)
            logic_list.append(inner_list_out)
        tc_dict["Logic"] = logic_list
        return tc_dict

    def to_simple_dict(self, campaign):
        """
        Return a plain/simple dictionary of the expected JSON for EMOD.  The main
        purpose of this is for validation in testing.  We need the ability to see
        that the logic written in python is translated to the JSON correctly.

        Args:
            campaign: The campaign module that has the path to the schema

        Returns:
            A simple dictionary containing the data for EMOD.
        """
        tc_obj = self.to_schema_dict(campaign)
        tc_dict = self._clean_dict(tc_obj)
        tc_dict = self._convert_logic_to_dict(tc_dict)
        return tc_dict


class BaseTargetingConfig(AbstractTargetingConfig):
    """
    The BaseTargetingConfig class should used as the base class for all of the
    Targeting_Config classes.  The main job of the subclasses is to maintain
    the extra data needed by the class in EMOD to perform the check.  For example,
    HasIP needs to know the IP key:value so that in EMOD the class can check if
    the individual has the given IP.  HasIP is responsible for making sure it
    is translated in the EMOD configuration.
    """
    def __init__(self):
        super().__init__()

    def __eq__(self, other):
        """
        Return true if the 'other' object has the same set and values of internal variables.
        """
        if not isinstance(other, BaseTargetingConfig):
            return False
        else:
            return self.__dict__ == other.__dict__

    def __and__(self, right):
        """
        Return a new object that contains the logical and'ing of this object with
        the object on the right of the '&' operand.
        """
        if not isinstance(right, AbstractTargetingConfig):
            raise ValueError("The object on the right of the '&' is not of type 'AbstractTargetingConfig'.")
        elif isinstance(right, _TargetingLogic) and right.is_equal_to == 1:
            # See !!!Inversion and TargetingLogic!!! above
            return right.pre_and(self)
        else:
            tl = _TargetingLogic(is_and=True, left=self, right=right)
            return tl

    def __or__(self, right):
        """
        Return a new object that contains the logical or'ing of this object with
        the object on the right of the '|' operand.
        """
        if not isinstance(right, AbstractTargetingConfig):
            raise ValueError("The object on the right of the '|' is not of type 'AbstractTargetingConfig'.")
        elif isinstance(right, _TargetingLogic) and right.is_equal_to == 1:
            # See !!!Inversion and TargetingLogic!!! above
            return right.pre_or(self)
        else:
            tl = _TargetingLogic(is_and=False, left=self, right=right)
            return tl


class HasIP(BaseTargetingConfig):
    """
    This determines if the person has a particular value of a particular IndividualProperties (IP).
    This is especially needed when determining if a partner has a particular IP
    (see emodpy-hiv.utils.targeting_config.HasRelationship).

    ip_key_value: An IndividualProperties Key:Value pair where the key/property name and one of its
        values is separated by a colon (':').  This cannot be an empty string.
    """
    def __init__(self, ip_key_value):
        super().__init__()
        self.class_name = "HasIP"
        if not ip_key_value:
            raise ValueError("'ip_key_value' must be a non-zero length string.")
        self.ip_key_value = validate_key_value_pair(ip_key_value)

    def to_schema_dict(self, campaign):
        """
        Create the ReadOnlyDict object representation of this Targeting_Config logic.
        This is the dictionary used to generate the JSON for EMOD.

        Args:
            campaign (api_campaign): The campaign module that has the path to the schema

        Returns:
            (ReadOnlyDict): Dict object created by schema_to_class
        """
        tc_obj = super().to_schema_dict(campaign)
        tc_obj.IP_Key_Value = self.ip_key_value
        return tc_obj


class HasIntervention(BaseTargetingConfig):
    """
    This check determines whether or not the individual has an intervention with the given name.
    This will only work for interventions that persist like SimpleVaccine and DelayedIntervention.
    It will not work for interventions like BroadcastEvent since it does not persist.

    intervention_name: The name of the intervention the person should have. This cannot be an empty
        string but should be either the name of the intervention class or the name given to the
        intervention of interest.  EMOD does not verify that this name exists or is used in your
        campaign.
    """
    def __init__(self, intervention_name):
        super().__init__()
        self.class_name = "HasIntervention"

        if not intervention_name:
            raise ValueError("'intervention_name' must be a non-zero length string.")
        self.intervention_name = validate_intervention_name(intervention_name)

    def to_schema_dict(self, campaign):
        """
        Create the ReadOnlyDict object representation of this Targeting_Config logic.
        This is the dictionary used to generate the JSON for EMOD.

        Args:
            campaign (api_campaign): The campaign module that has the path to the schema

        Returns:
            (ReadOnlyDict): Dict object created by schema_to_class
        """
        tc_obj = super().to_schema_dict(campaign)
        tc_obj.Intervention_Name = self.intervention_name
        return tc_obj


class IsPregnant(BaseTargetingConfig):
    """
    Select the individual based on whether or not they are pregnant.
    """
    def __init__(self):
        super().__init__()
        self.class_name = "IsPregnant"
