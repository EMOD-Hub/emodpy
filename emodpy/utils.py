import hashlib
import os
import stat
from pathlib import Path
from sys import exit
from enum import Enum, Flag, auto
from getpass import getpass
from logging import getLogger
import requests


logger = getLogger(__name__)
user_logger = getLogger('user')


class EradicationPlatformExtension(Enum):
    LINUX = ''
    Windows = '.exe'
