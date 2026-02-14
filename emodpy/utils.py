from enum import Enum
from logging import getLogger


logger = getLogger(__name__)
user_logger = getLogger('user')


class EradicationPlatformExtension(Enum):
    LINUX = ''
    Windows = '.exe'
