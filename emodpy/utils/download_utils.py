import hashlib
import os
import stat
from pathlib import Path
from enum import Enum
from logging import getLogger
import requests
from idmtools.utils.decorators import optional_yaspin_load

# Github URLs
ERADICATION_GIT_URL_TEMPLATE = 'https://github.com/InstituteforDiseaseModeling/EMOD/releases/download/v{}/Eradication{}'


logger = getLogger(__name__)
user_logger = getLogger('user')


class EradicationPlatformExtension(Enum):
    LINUX = ''
    Windows = '.exe'


def get_github_eradication_url(version: str,
                               extension: EradicationPlatformExtension = EradicationPlatformExtension.LINUX) -> str:
    """
    Get the github eradication url for specified release

    Args:
        version: Release to fetch
        extension: Optional extensions. Defaults to Linux(None)
    Returns:
        Url of eradication release
    """
    return ERADICATION_GIT_URL_TEMPLATE.format(version, extension.value)


@optional_yaspin_load(text='Downloading file')
def download_eradication(url: str, cache_path: str = None, spinner=None):
    """
    Downloads Eradication binary

    Useful for downloading binaries from Bamboo or Github

    Args:
        url: Url to binary
        cache_path: Optional output directory
        spinner: Spinner object

    Returns:
        Full path to output file
    """
    # download eradication from path to our local_data cache
    if cache_path is None:
        cache_path = os.path.join(
            str(Path.home()), '.local_data', "eradication-cache")
    elif os.path.exists(cache_path) and os.path.isfile(cache_path):
        raise ValueError("Path must be a directory")
    filename = hashlib.md5(url.encode('utf-8')).hexdigest()
    out_name = os.path.join(cache_path, filename)
    os.makedirs(cache_path, exist_ok=True)
    if not os.path.exists(out_name):
        if spinner:
            spinner.text = f"Downloading {url} to {out_name}"
        logger.debug(f"Downloading {url} to {out_name}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(out_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
        # ensure on linux we make it executable locally
        if os.name != 'nt':
            st = os.stat(out_name)
            os.chmod(out_name, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        logger.debug(f"Finished downloading {url}")
    else:
        logger.debug(f'{url} already cached as {out_name}')
    return out_name


ERADICATION_213 = get_github_eradication_url('2.13.0')
ERADICATION_218 = get_github_eradication_url('2.18.0')
ERADICATION_220 = get_github_eradication_url('2.20.0')
