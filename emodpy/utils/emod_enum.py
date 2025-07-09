from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value
    pass


class DistributionType(StrEnum):
    NOT_INITIALIZED = 'NOT_INITIALIZED'
    CONSTANT_DISTRIBUTION = 'CONSTANT_DISTRIBUTION'
    UNIFORM_DISTRIBUTION = 'UNIFORM_DISTRIBUTION'
    GAUSSIAN_DISTRIBUTION = 'GAUSSIAN_DISTRIBUTION'
    EXPONENTIAL_DISTRIBUTION = 'EXPONENTIAL_DISTRIBUTION'
    POISSON_DISTRIBUTION = 'POISSON_DISTRIBUTION'
    LOG_NORMAL_DISTRIBUTION = 'LOG_NORMAL_DISTRIBUTION'
    DUAL_CONSTANT_DISTRIBUTION = 'DUAL_CONSTANT_DISTRIBUTION'
    WEIBULL_DISTRIBUTION = 'WEIBULL_DISTRIBUTION'
    DUAL_EXPONENTIAL_DISTRIBUTION = 'DUAL_EXPONENTIAL_DISTRIBUTION'
    BIMODAL_DISTRIBUTION = 'BIMODAL_DISTRIBUTION'


class NodeSelectionType(StrEnum):
    DISTANCE_ONLY = 'DISTANCE_ONLY'
    MIGRATION_NODES_ONLY = 'MIGRATION_NODES_ONLY'
    DISTANCE_AND_MIGRATION = 'DISTANCE_AND_MIGRATION'


class VaccineType(StrEnum):
    Generic = 'Generic'
    TransmissionBlocking = 'TransmissionBlocking'
    AcquisitionBlocking = 'AcquisitionBlocking'
    MortalityBlocking = 'MortalityBlocking'


class SensitivityType(StrEnum):
    SINGLE_VALUE = 'SINGLE_VALUE'
    VERSUS_TIME = 'VERSUS_TIME'


class EventOrConfig(StrEnum):
    Config = 'Config'
    Event = 'Event'


class SettingType(StrEnum):
    CURRENT_AGE = 'CURRENT_AGE'
    USER_SPECIFIED = 'USER_SPECIFIED'
