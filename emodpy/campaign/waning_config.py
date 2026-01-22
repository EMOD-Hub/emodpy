from abc import ABC, abstractmethod
from emodpy.campaign.common import ValueMap
from emod_api import schema_to_class as s2c


class AbstractWaningConfig(ABC):
    """
    Abstract class for all waning effects. This class is not meant to be used directly, but to be inherited by other
    waning effect classes.
    """
    @abstractmethod
    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the waning effect object to a schema dictionary.
        Needs to be implemented in the child classes.
        """
        pass


class BaseWaningConfig(AbstractWaningConfig, ABC):
    """
    Base class for all waning effects except Combo. This class is not meant to be used directly, but to be inherited by
    other waning effect classes.

    Args:
        effect (float, optional):
            - The initial effect/effect multiplier/constant effect of the waning effect.
            - Must be between 0 and 1.
            - Defaults to 1.
    """

    def __init__(self, effect: float = 1):
        if effect is None:
            raise ValueError("effect should be a float value.")
        elif effect < 0 or effect > 1:
            raise ValueError("effect should be between 0 and 1.")
        self.initial_effect = effect

    @abstractmethod
    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the waning effect object to a schema dictionary.
        Needs to be implemented in the child classes.
        """
        pass


class Combo(AbstractWaningConfig):
    """
    The Combo class is used within individual-level interventions and allows for specifying a list of effects when the
    intervention only has one WaningEffect defined. These effects can be added or multiplied.

    Args:
        effect_list (list[BaseWaningConfig], required):
            - A list of waning effects to be combined.
        add_effects (bool, optional):
            - The Add_Effects parameter tells EMOD how to combine multiple effects from the waning effect classes.
            - If set to true, then the waning effect values from the different waning effect objects are added together.
            - If set to false, the waning effect values are multiplied.
            - The resulting waning effect value is capped at 1. If the value exceeds 1, it will be set to 1.
            - Defaults to False.
        expires_when_all_expire (bool, optional):
            - Specifies whether all effects in the effect_list must expire for the intervention to expire.
            - If set to True, the intervention expires only when all effects in the effect_list expire.
            - If set to False, the intervention expires as soon as one of the effects in the effect_list expires.
            - Only the following effects can cause the intervention to expire: RandomBox, MapLinear (when expire_at_durability_map_end is set to True), MapPiecewise (when expire_at_durability_map_end is set to True).
            - Defaults to False.

    """

    def __init__(self, effect_list: list[BaseWaningConfig], add_effects: bool = False,
                 expires_when_all_expire: bool = False):
        # Validate add_effects
        if not isinstance(add_effects, bool):
            raise ValueError("add_effects should be a boolean.")
        self.add_effects = add_effects
        # Make sure that the effect_list is a list of BaseWaningConfig objects
        # Combo class is not derived from BaseWaningConfig since we don't want to allow Combo instance in the
        # effect_list in Combo class
        for effect in effect_list:
            if not isinstance(effect, BaseWaningConfig):
                raise ValueError(f"effect_list should be a list of BaseWaningConfig objects, not {type(effect)}")
        self.effect_list = effect_list
        # Validate expires_when_all_expire
        if not isinstance(expires_when_all_expire, bool):
            raise ValueError("expires_when_all_expire should be a boolean.")
        self.expires_when_all_expire = expires_when_all_expire

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the Combo waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectCombo", schema_json=campaign.get_schema())
        wc_obj.Add_Effects = self.add_effects
        wc_obj.Expires_When_All_Expire = self.expires_when_all_expire
        wc_obj.Effect_List = [effect.to_schema_dict(campaign) for effect in self.effect_list]
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class Box(BaseWaningConfig):
    """
    This class is used to configure the Box waning effect in the campaign object. The efficacy is held at a
    constant rate until it drops to zero after the user-defined duration.

    Args:
        constant_effect (float, required):
            - Strength of the effect, which remains constant until the duration is complete
            - Must be between 0 and 1.

        box_duration (float, required):
            - The duration from when the intervention was distributed to the person to the current time. During this duration, the 'constant_effect' will be applied.
            - Must be between 0 and 100000.

    """

    def __init__(self, constant_effect: float, box_duration: float):
        super().__init__(constant_effect)
        if box_duration < 0 or box_duration > 100000:
            raise ValueError("box_duration should be between 0 and 100000.")
        self.box_duration = box_duration

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the Box waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectBox", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Box_Duration = self.box_duration
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class BoxExponential(BaseWaningConfig):
    """
    This class is used to configure the BoxExponential waning effect in the campaign object. The initial efficacy
    is held for a specified duration, then the efficacy decays at an exponential rate where the current effect is
    equal to initial_effect - dt/decay_time_constant. Here, 'dt' is the duration of the timestep (config.Simulation_Timestep).

    Args:
        box_duration (float, required):
            - The duration of the box waning effect in days, from when the person gets the intervention to the current time.
            - Must be between 0 and 100000.
        decay_time_constant (float, required):
            - The exponential decay length, in days, where the current effect is equal to initial_effect - dt/decay_time_constant (dt equal to delta time)
            - Must be between 0 and 100000.
        initial_effect (float, optional):
            - Strength of the effect, which remains constant until the box_duration is complete.
            - Must be between 0 and 1.
            - Defaults to 1.
    """

    def __init__(self, box_duration: float, decay_time_constant: float, initial_effect: float = 1, ):
        super().__init__(initial_effect)
        if box_duration < 0 or box_duration > 100000:
            raise ValueError("box_duration should be between 0 and 100000.")
        if decay_time_constant < 0 or decay_time_constant > 100000:
            raise ValueError("decay_time_constant should be between 0 and 100000.")
        self.box_duration = box_duration
        self.decay_time_constant = decay_time_constant

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the BoxExponential waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectBoxExponential", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Box_Duration = self.box_duration
        wc_obj.Decay_Time_Constant = self.decay_time_constant
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class Constant(BaseWaningConfig):
    """
    This class is used to configure the Constant waning effect in the campaign object. The efficacy is held at a
    constant rate.

    Args:
        constant_effect (float, required):
            - Strength of the effect, which remains constant until the intervention expires.
            - Must be between 0 and 1.
    """
    def __init__(self, constant_effect: float):
        super().__init__(constant_effect)

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the Constant waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectConstant", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class Exponential(BaseWaningConfig):
    """
    This class is used to configure the Exponential waning effect in the campaign object. The efficacy decays at an
    exponential rate where the current effect is equal to initial_effect - dt/decay_time_constant. Here, 'dt' is the
    duration of the timestep (config.Simulation_Timestep).

    Args:
        decay_time_constant (float, required):
            - The exponential decay length, in days, where the current effect is equal to initial_effect - dt/decay_time_constant (dt equal to delta time).
            - Must be between 0 and 100000.

        initial_effect (float, optional):
            - Initial strength of the effect.
            - Must be between 0 and 1.
            - default to 1.

    """

    def __init__(self, decay_time_constant: float, initial_effect: float = 1):
        super().__init__(initial_effect)
        if decay_time_constant < 0 or decay_time_constant > 100000:
            raise ValueError("decay_time_constant should be between 0 and 100000.")
        self.decay_time_constant = decay_time_constant

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the Exponential waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectExponential", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Decay_Time_Constant = self.decay_time_constant
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class MapLinear(BaseWaningConfig):
    """
    This class is used to configure the MapLinear waning effect in the campaign object. The efficacy decays based
    on the time since the start of the intervention. This change is defined by a map of time to efficacy values
    in which the time between time/effect points is linearly interpolated. When the time since start reaches the
    end of the times in the map, the last effect will be used unless the intervention expires. If the time since
    start is less than the first effect in the map, the efficacy will be zero. This can be used to define the shape
    of a curve whose magnitude is defined by the effect_multiplier.

    Args:
        times (list[float], required):
            - The list of time, in days, to define the duration. It must have the same length as values.

        effects (list[float], required):
            - The list of values to define the efficacy at the corresponding time. It must have the same length as times.

        effect_multiplier (float, optional):
            - The multiplier used to define the magnitude of the shape of the curve, as specified when using the parameters with the MapLinear class.
            - Min Value: 0
            - Max Value: 1
            - Default Value: 1

        expire_at_durability_map_end (bool, optional):
            - If set to True, the intervention will expire when the time since start reaches the end of the times in the map.
            - If set to False, the last value in the map will be used when the time since start reaches the end of the times in the map.
            - Default Value: False

    Examples:
        In this example, we create a MapLinear object with the following times and effects:
        [365, 730, 1460, 3650] and [10, 20, 33, 40] respectively. The MapLinear object is then create an
        InterpolatedValueMap object in the campaign object to represent these times and effects. The value at time 365
        is 10, at time 730 is 20, at time 1460 is 33, and at time 3650 is 40. The values between these times are
        interpolated linearly. For example, the value at time 1095 is 26.5, which is the average of the values at times
        730 and 1460. The value at time 395 is 10.821918, which is calculated by linear interpolation between the values
        at times 365 and 730, (20-10)*(395-365)/(730-365) + 10 , and so on.

        >>> times = [365, 730, 1460, 3650]
        >>> effects = [10, 20, 33, 40]
        >>> wc = MapLinear(times=times, effects=effects)
    """

    def __init__(self, times: list[float], effects: list[float], effect_multiplier: float = 1,
                 expire_at_durability_map_end: bool = False):
        super().__init__(effect_multiplier)
        # Validation for times and values lists is done in the ValueMap class
        durability_map = ValueMap(times=times, values=effects)
        self.durability_map = durability_map
        if not isinstance(expire_at_durability_map_end, bool):
            raise ValueError("expire_at_durability_map_end should be a boolean.")
        self.expire_at_durability_map_end = expire_at_durability_map_end

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the MapLinear waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectMapLinear", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Durability_Map = self.durability_map.to_schema_dict(campaign)
        wc_obj.Expire_At_Durability_Map_End = self.expire_at_durability_map_end
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class MapLinearAge(BaseWaningConfig):
    """
    This class is used to configure the MapLinearAge waning effect in the campaign object. The efficacy decays based
    the age of the individual who owns the intervention instead of the time since the start of the intervention.
    This change is defined by a map of age to efficacy values in which the age between age/effect points is linearly
    interpolated. When the age of the individual reaches the end of the ages in the map, the last value will be
    used. If the age of the individual is less than the first value in the map, the
    efficacy will be zero. This can be used to define the shape of a curve whose magnitude is defined by the
    effect_multiplier.

    Args:
        ages (list[float], required):
            - The list of ages, in years. It must have the same length as 'effects'.

        effects (list[float], required):
            - The list of values to define the efficacy at the corresponding age. It must have the same length as 'ages'.

        effect_multiplier (float, optional):
            - The multiplier used to define the magnitude of the shape of the curve, as specified when using the parameters with the MapLinearAge class.
            - Min Value: 0
            - Max Value: 1
            - Default Value: 1

    """

    def __init__(self, ages: list[float], effects: list[float], effect_multiplier: float = 1):
        super().__init__(effect_multiplier)
        # Validation for times and values lists is done in the ValueMap class
        durability_map = ValueMap(times=ages, values=effects)
        self.durability_map = durability_map

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the MapLinearAge waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectMapLinearAge", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Durability_Map = self.durability_map.to_schema_dict(campaign)
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class MapLinearSeasonal(BaseWaningConfig):
    """
    This class is used to configure the MapLinearSeasonal waning effect in the campaign object. The efficacy decays
    based on the season of the year. The efficacy will repeat itself every 365 days. That is, the time since start
    will reset to zero once it reaches 365. This allows you to simulate seasonal effects.

    Args:
        times (list[float], required):
            - The list of time, in days, to define the duration. It must have the same length as values.
            - The days should be greater than or equal to 0 and less than or equal to 365.

        effects (list[float], required):
            - The list of values to define the efficacy at the corresponding day.
            - It must have the same length as days.

        effect_multiplier (float, optional):
            - The multiplier used to define the magnitude of the shape of the curve, as specified when using the parameters with the WaningEffectMapLinear class.
            - Min Value: 0
            - Max Value: 1
            - Default Value: 1

    """
    def __init__(self, times: list[float], effects: list[float], effect_multiplier: float):
        super().__init__(effect_multiplier)
        if any(time < 0 for time in times) or any(time > 365 for time in times):
            raise ValueError("The times should be greater than or equal to 0 and less than or equal to 365.")
        # Validation for times and values lists is done in the ValueMap class
        durability_map = ValueMap(times=times, values=effects)
        self.durability_map = durability_map

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the MapLinearSeasonal waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectMapLinearSeasonal", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Durability_Map = self.durability_map.to_schema_dict(campaign)
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class MapPiecewise(BaseWaningConfig):
    """
    This class is used to configure the MapPiecewise waning effect in the campaign object. The efficacy decays based
    on the time since the start of the intervention. Similar to WaningEffectMapLinear, except that the data is
    assumed to be constant between time/value points (no interpolation). If the time since start falls between two
    points, the efficacy of the earlier time point is used.

    Args:
        days (list[float], required):
            - The list of time, in days, to define the duration. It must have the same length as values.

        effects (list[float], required):
            - The list of values to define the efficacy at the corresponding time. It must have the same length as times.

        effect_multiplier (float, optional):
            - The multiplier used to define the magnitude of the shape of the curve, as specified when using the parameters with the WaningEffectMapLinear class.
            - Min Value: 0
            - Max Value: 1
            - Default Value: 1

        expire_at_durability_map_end (bool, optional):
            - If set to True, the intervention will expire when the time since start reaches the end of the times in the map.
            - If set to False, the last value in the map will be used when the time since start reaches the end of the times in the map.
            - Default Value: False

    """
    def __init__(self, days: list[float], effects: list[float], effect_multiplier: float = 1,
                 expire_at_durability_map_end: bool = False):
        super().__init__(effect_multiplier)
        # Validation for times and values lists is done in the ValueMap class
        durability_map = ValueMap(times=days, values=effects)
        self.durability_map = durability_map
        self.expire_at_durability_map_end = expire_at_durability_map_end

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the MapPiecewise waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectMapPiecewise", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Durability_Map = self.durability_map.to_schema_dict(campaign)
        wc_obj.Expire_At_Durability_Map_End = self.expire_at_durability_map_end
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj


class RandomBox(BaseWaningConfig):
    """
    This class is used to configure the RandomBox waning effect in the campaign object. The efficacy is held at a
    constant rate until it drops to zero after a user-defined duration. This duration is randomly selected from an
    exponential distribution where exponential_discard_time is the mean.

    The intervention will expire when the randomly selected duration is complete.

    Args:
        constant_effect (float, required):
            - Strength of the effect, which remains constant until the duration is complete.
            - Must be between 0 and 1.

        exponential_discard_time (float, required):
            - The mean time, in days, of an exponential distribution of the duration of the effect of an intervention (such as a vaccine or bed net).
            - Must be between 0 and 100000.
    """
    def __init__(self, constant_effect: float, exponential_discard_time: float):
        super().__init__(constant_effect)
        if exponential_discard_time < 0 or exponential_discard_time > 100000:
            raise ValueError(f"exponential_discard_time should be between 0 and 100000, not {exponential_discard_time}.")
        self.expected_discard_time = exponential_discard_time

    def to_schema_dict(self, campaign) -> s2c.ReadOnlyDict:
        """
        This method is used to convert the RandomBox waning effect object to a schema dictionary.
        """
        wc_obj = s2c.get_class_with_defaults("WaningEffectRandomBox", schema_json=campaign.get_schema())
        wc_obj.Initial_Effect = self.initial_effect
        wc_obj.Expected_Discard_Time = self.expected_discard_time
        wc_obj.pop("schema", None)
        wc_obj.pop("explicits", None)
        return wc_obj
