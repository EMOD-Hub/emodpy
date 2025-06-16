from abc import ABC, abstractmethod
from emodpy.utils.emod_enum import DistributionType
from emod_api import schema_to_class as s2c


class BaseDistribution(ABC):
    """
    Abstract base class for distribution classes. This class should not be instantiated directly.
    """

    @abstractmethod
    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the intervention object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        pass

    @abstractmethod
    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics distribution of the class type

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        pass

    def _set_parameters(self, emod_object, key, value):
        if hasattr(emod_object, key):
            setattr(emod_object, key, value)
        else:
            raise AttributeError(f"Attribute {key} does not exist in {emod_object.__class__.__name__}")


class ConstantDistribution(BaseDistribution):
    """
    This class represents a constant distribution, a type of statistical distribution where all outcomes are equally
    likely. A constant distribution is defined by a single value that is returned for all inputs.

    Args:
        value (float):
            - The constant value that this distribution returns.
            - The value should not be negative.

    Raises:
        ValueError: If the 'value' argument is negative.

    Example:
        >>> # Create a ConstantDistribution object.
        >>> cd = ConstantDistribution(5)
        >>> # The value attribute can be accessed and updated.
        >>> cd.value
        5
        >>> cd.value = 10
        >>> cd.value
        10
    """
    def __init__(self, value: float):
        super().__init__()
        if value < 0:
            raise ValueError("The 'value' argument should not be negative.")
        self.value = value

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.CONSTANT_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Constant", self.value)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics constant distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 0, "value1": self.value, "value2": None}  # value 2 not used


class UniformDistribution(BaseDistribution):
    """
    This class represents a uniform distribution, which is a type of statistical distribution
    where all outcomes are equally likely within a specified range. A uniform distribution is defined by two parameters:
    the minimum and maximum values that define the range of outcomes.

    Args:
        uniform_min (float):
            - The minimum value of the range for this distribution.
            - The value should not be negative.

        uniform_max (float):
            - The maximum value of the range for this distribution.
            - The value should not be negative.

    Raises:
        ValueError: If 'uniform_min' or 'uniform_max' arguments are negative.

    Example:
        >>> # Create  a UniformDistribution object.
        >>> ud = UniformDistribution(0, 10)
        >>> # The uniform_min and uniform_max attributes can be accessed and updated.
        >>> ud.uniform_min
        0
        >>> ud.uniform_max
        10
        >>> ud.uniform_min = 5
        >>> ud.uniform_min
        5
    """
    def __init__(self, uniform_min: float, uniform_max: float):
        super().__init__()
        if uniform_min < 0 or uniform_max < 0:
            raise ValueError("The 'uniform_min' and 'uniform_max' arguments should not be negative.")
        if uniform_min > uniform_max:
            raise ValueError("The 'uniform_min' argument should be less than 'uniform_max'.")
        self.uniform_min = uniform_min
        self.uniform_max = uniform_max

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.

            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.UNIFORM_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Min", self.uniform_min)
        self._set_parameters(intervention_object, f"{prefix}_Max", self.uniform_max)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics uniform distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 1, "value1": self.uniform_min, "value2": self.uniform_max}


class GaussianDistribution(BaseDistribution):
    """
    This class represents a Gaussian distribution, a type of statistical distribution where the values are distributed
    symmetrically around the mean. A Gaussian distribution is defined by two parameters: the mean and the standard
    deviation.

    Args:
        mean (float):
            - The mean of the Gaussian distribution.
            - This value should not be negative.

        std_dev (float):
            - The standard deviation of the Gaussian distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'mean' argument is negative or 'std_dev' argument is not positive.

    Example:
        >>> # Create a GaussianDistribution object.
        >>> gd = GaussianDistribution(0, 1)
        >>> # The mean and std_dev attributes can be accessed and updated.
        >>> gd.mean
        0
        >>> gd.std_dev
        1
        >>> gd.mean = 5
        >>> gd.mean
        5
    """
    def __init__(self, mean: float, std_dev: float):
        if mean < 0 or std_dev <= 0:
            raise ValueError("The 'mean' argument should not be negative and the 'std_dev' argument should be "
                             "positive.")
        super().__init__()
        self.mean = mean
        self.std_dev = std_dev

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.GAUSSIAN_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Gaussian_Mean", self.mean)
        self._set_parameters(intervention_object, f"{prefix}_Gaussian_Std_Dev", self.std_dev)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics gaussian distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 2, "value1": self.mean, "value2": self.std_dev}


class ExponentialDistribution(BaseDistribution):
    """
    This class represents an exponential distribution, a type of statistical distribution
    where the probability of an event decreases exponentially with time.
    An exponential distribution is defined by a single parameter: the mean, which represents the average time
    between events.

    Args:
        mean (float):
            - The mean, also the scale parameter of the exponential distribution.
            - It's the 1/rate parameter.
            - This value is set during the initialization of the class instance. It can be updated using the 'update_attribute()' method.
            - The value should not be negative.

    Raises:
        ValueError: If 'mean' argument is negative.

    Example:
        >>> # Create an ExponentialDistribution object.
        >>> ed = ExponentialDistribution(1)
        >>> # The mean attribute can be accessed and updated.
        >>> ed.mean
        1
        >>> ed.mean = 2
        >>> ed.mean
        2
    """
    def __init__(self, mean: float):
        super().__init__()
        if mean < 0:
            raise ValueError("The 'mean' argument should not be negative.")
        self.mean = mean

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.EXPONENTIAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Exponential", self.mean)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics exponential distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 3, "value1": self.mean, "value2": None}  # value2 not used


class PoissonDistribution(BaseDistribution):
    """
    This class represents a Poisson distribution, a type of statistical distribution where the probability of a given
    number of events occurring in a fixed interval of time or space is proportional to the mean number of events.

    Args:
        mean (float):
            - The mean of the Poisson distribution.
            - This value should not be negative.

    Raises:
        ValueError: If 'mean' argument is negative.

    Example:
        >>> # Create a PoissonDistribution object.
        >>> pd = PoissonDistribution(1)
        >>> # The mean attribute can be accessed and updated.
        >>> pd.mean
        1
        >>> pd.mean = 2
        >>> pd.mean
        2
    """
    def __init__(self, mean: float):
        if mean < 0:
            raise ValueError("The 'mean' argument should not be negative.")
        super().__init__()
        self.mean = mean

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.POISSON_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Poisson_Mean", self.mean)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics poisson distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 4, "value1": self.mean, "value2": None}  # value2 not used


class LogNormalDistribution(BaseDistribution):
    """
    This class represents a log-normal distribution, a type of statistical distribution where the logarithm of the
    values is normally distributed. A log-normal distribution is defined by two parameters: the mean and the standard
    deviation.

    Args:
        mean (float):
            - The mean/mu of the log-normal distribution.

        std_dev (float):
            - The standard deviation/sigma/width of the log-normal distribution.

    Example:
        >>> # Create a LogNormalDistribution object.
        >>> lnd = LogNormalDistribution(0, 1)
        >>> # The mean and std_dev attributes can be accessed and updated.
        >>> lnd.mean
        0
        >>> lnd.std_dev
        1
        >>> lnd.mean = 5
        >>> lnd.mean
        5
    """
    def __init__(self, mean: float, std_dev: float):
        super().__init__()
        self.mean = mean
        self.std_dev = std_dev

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.LOG_NORMAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Log_Normal_Mu", self.mean)
        self._set_parameters(intervention_object, f"{prefix}_Log_Normal_Sigma", self.std_dev)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics log normal distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 5, "value1": self.mean, "value2": self.std_dev}


class DualConstantDistribution(BaseDistribution):
    """
    This class represents a dual constant distribution, a type of statistical distribution where the outcomes are
    distributed between a constant value and zero based on a proportion. A dual constant
    distribution is defined by two parameters: the proportion and the constant value.

    This distribution is not supported in EMOD demographics.

    Args:
        proportion (float):
            - The proportion of value of zero.
            - This value should be between 0 and 1.

        constant (float):
            - The second constant value that this distribution returns other than zero.
            - The value should not be negative.

    Raises:
        ValueError: If 'proportion' argument is not between 0 and 1 or 'constant' argument is negative.

    Example:
        >>> # Create a DualConstantDistribution object.
        >>> # In the follow example, there will be 20% of zeros and 80% of 5s.
        >>> dcd = DualConstantDistribution(0.2, 5)
        >>> # The proportion and constant attributes can be accessed and updated.
        >>> dcd.proportion
        0.2
        >>> dcd.constant
        5
        >>> dcd.proportion = 0.6
        >>> dcd.proportion
        0.6
    """
    def __init__(self, proportion: float, constant: float):
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if constant < 0:
            raise ValueError("The 'constant' argument should not be negative.")
        super().__init__()
        self.proportion = proportion
        self.constant = constant

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.DUAL_CONSTANT_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Proportion_0", self.proportion)
        self._set_parameters(intervention_object, f"{prefix}_Peak_2_Value", self.constant)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        This function is not supported in the demographic object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("DualConstantDistribution does not support demographic distribution. Please use "
                                  "other distributions.")


class BimodalDistribution(BaseDistribution):
    """
    This class represents a bimodal distribution, a type of statistical distribution with two different modes (peaks).
    A bimodal distribution is defined by two parameters: the proportion of the second bin, user defined bin, and the
    constant value of the second bin. The 1-proportion will be the first bin and constant value in the first bin is 1.

    This distribution is not supported in EMOD interventions.

    Args:
        proportion (float):
            - The proportion of the second bin.
            - This value should be between 0 and 1.

        constant (float):
            - The constant value of the second bin.
            - The value should not be negative.

    Examples:
        >>> # Create a BimodalDistribution object.
        >>> # In the follow example, there will be 20% of the second bin(5) and 80% of the first bin(1).
        >>> bd = BimodalDistribution(0.2, 5)
        >>> # The proportion and constant attributes can be accessed and updated.
        >>> bd.proportion
        0.2
        >>> bd.constant
        5
        >>> bd.proportion = 0.6
        >>> bd.proportion
        0.6

    """
    def __init__(self, proportion: float, constant: float):
        super().__init__()
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if constant < 0:
            raise ValueError("The 'constant' argument should not be negative.")
        self.proportion = proportion
        self.constant = constant

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        This function is not supported in the intervention object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("BimodalDistribution does not support intervention distribution. Please use "
                                  "other distributions.")

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics bimodal distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": 6,
                "value1": self.proportion,
                "value2": self.constant}


class WeibullDistribution(BaseDistribution):
    """
    This class represents a Weibull distribution, a type of statistical distribution where the probability density
    function is defined by two parameters: the shape parameter (kappa) and the scale parameter (lambda).

    Args:
        weibull_kappa (float):
            - The shape parameter of the Weibull distribution.
            - This value should be positive.

        weibull_lambda (float):
            - The scale parameter of the Weibull distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'weibull_kappa' or 'weibull_lambda' arguments are not positive.

    Example:
        >>> # Create a WeibullDistribution object.
        >>> wd = WeibullDistribution(1, 2)
        >>> # The weibull_kappa and weibull_lambda attributes can be accessed and updated.
        >>> wd.weibull_kappa
        1
        >>> wd.weibull_lambda
        2
        >>> wd.weibull_kappa = 3
        >>> wd.weibull_kappa
        3
    """
    def __init__(self, weibull_kappa: float, weibull_lambda: float):
        if weibull_kappa <= 0 or weibull_lambda <= 0:
            raise ValueError("The 'weibull_kappa' and 'weibull_lambda' arguments should be positive.")
        super().__init__()
        self.weibull_kappa = weibull_kappa
        self.weibull_lambda = weibull_lambda

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.WEIBULL_DISTRIBUTION.value)
        # scale parameter is lambda, shape parameter is kappa
        self._set_parameters(intervention_object, f"{prefix}_Kappa", self.weibull_kappa)
        self._set_parameters(intervention_object, f"{prefix}_Lambda", self.weibull_lambda)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics weibull distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        # scale parameter is lambda, shape parameter is kappa
        return {"flag": 7, "value1": self.weibull_lambda, "value2": self.weibull_kappa}


class DualExponentialDistribution(BaseDistribution):
    """
    This class represents a dual exponential distribution, a type of statistical distribution where the outcomes are
    distributed between two exponential distributions based on a proportion. A dual exponential distribution is defined
    by three parameters: the proportion, the first mean, and the second mean.

    This distribution is not supported in EMOD demographics.

    Args:
        proportion (float):
            - The proportion of the first exponential distribution.
            - This value should be between 0 and 1.

        mean_1 (float):
            - The mean of the first exponential distribution.
            - This value should be positive.

        mean_2 (float):
            - The mean of the second exponential distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'proportion' argument is not between 0 and 1 or 'mean_1' or 'mean_2' arguments are negative.

    Example:
        >>> # Create a DualExponentialDistribution object.
        >>> # In the follow example, there will be 20% of the first exponential distribution and 80% of the second.
        >>> ded = DualExponentialDistribution(0.2, 1, 2)
        >>> # The proportion, mean_1, and mean_2 attributes can be accessed and updated.
        >>> ded.proportion
        0.2
        >>> ded.mean_1
        1
        >>> ded.mean_2
        2
        >>> ded.proportion = 0.6
        >>> ded.proportion
        0.6
    """
    def __init__(self, proportion: float, mean_1: float, mean_2: float):
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if mean_1 <= 0 or mean_2 <= 0:
            raise ValueError("The 'mean_1' and 'mean_2' arguments should be positive.")
        super().__init__()
        self.proportion = proportion
        self.mean_1 = mean_1
        self.mean_2 = mean_2

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.DUAL_EXPONENTIAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Proportion_1", self.proportion)
        self._set_parameters(intervention_object, f"{prefix}_Mean_1", self.mean_1)
        self._set_parameters(intervention_object, f"{prefix}_Mean_2", self.mean_2)

    def get_demographic_distribution_parameters(self) -> None:
        """
        This function is not supported in the demographic object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("DualExponentialDistribution does not support demographic distribution. Please use "
                                  "other distributions.")
