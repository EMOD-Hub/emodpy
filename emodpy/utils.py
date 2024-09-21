import hashlib
import os
import stat
from pathlib import Path
from sys import exit
from enum import Enum, Flag, auto
from getpass import getpass
from logging import getLogger
import requests
import emodpy.bamboo_api_utils as bamboo_api
from idmtools.utils.decorators import optional_yaspin_load

# Github URLs
ERADICATION_GIT_URL_TEMPLATE = 'https://github.com/InstituteforDiseaseModeling/EMOD/releases/download/v{}/Eradication{}'


logger = getLogger(__name__)
user_logger = getLogger('user')


class EradicationPlatformExtension(Enum):
    LINUX = ''
    Windows = '.exe'


class EradicationBambooBuilds(Enum):
    GENERIC_LINUX = 'DTKGENCI-SCONSLNXGEN'
    GENERIC_WIN = 'DTKGENCI-SCONSWINGEN'
    GENERIC = GENERIC_LINUX
    TBHIV_LINUX = 'DTKTBHIVCI-SCONSRELLNXTBHIV'
    TBHIV_WIN = 'DTKTBHIVCI-SCONSWINTBHIV'
    TBHIV = TBHIV_LINUX
    MALARIA_LINUX = 'DTKMALCI-SCONSLNXMAL'
    MALARIA_WIN = 'DTKMALCI-SCONSWINMAL'
    MALARIA = MALARIA_LINUX
    HIV_LINUX = 'DTKHIVCI-SCONSRELLNXHIV'
    HIV_WIN = 'DTKHIVCI-RELWINHIV'
    HIV = HIV_LINUX
    DENGUE_LINUX = 'DTKDENGCI-SCONSRELLNX'
    DENGUE_WIN = 'DTKDENGCI-VSRELWINALL'
    DENGUE = DENGUE_LINUX
    FP_LINUX = 'DTKFPCI-SCONSRELLNX'
    FP_WIN = 'DTKFPCI-SCONSWINFP'
    FP = FP_LINUX
    TYPHOID_LINUX = 'DTKTYPHCI-SCONSRELLNX'
    TYPHOID_WIN = 'DTKTYPHCI-SCONSWINENV'
    TYPHOID = TYPHOID_LINUX
    EMOD_RELEASE = 'EMODREL-SCONSRELLNX'
    RELEASE = 'DTKREL-SCONSRELLNX'


class BambooArtifact(Flag):
    ERADICATION = auto()
    SCHEMA = auto()
    PLUGINS = auto()
    ALL = ERADICATION | SCHEMA | PLUGINS


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


def save_bamboo_credentials(username, password):
    """Save bamboo api login credentials using keyring.

    Args:
        username (str): bamboo api login username (e.g. somebody@idmod.org)
        password (str): bamboo api login password
    """
    bamboo_api.save_credentials(username, password)


def bamboo_api_login():
    """Automatically login to bamboo, prompt for credentials if none are cached or there's no login session."""
    success = False
    try:
        success = bamboo_api.bamboo_connection().login()
        if success:
            return
    except PermissionError:
        success = False

    retries = 3
    while not success and retries > 0:
        retries += -1
        user_logger.error('Unable to login to Bamboo API, please provide a username and password.')
        username = input('Username: ')
        password = getpass('Password: ')
        try:
            if username and password:
                success = bamboo_api.bamboo_connection().login(username, password)
                if success:
                    save_pass = input('Login successful, save username and password to keyring? [y/N] ')
                    if save_pass.strip().lower() == 'y':
                        save_bamboo_credentials(username, password)
                        user_logger.info('Saved.')
                    return
            else:
                user_logger.warning('Username/password cannot be blank.')
        except PermissionError:
            success = False
            user_logger.error('Permission error logging in to Bamboo API.')

    exit(1)


def download_bamboo_artifacts(plan_key: str, build_num: str = None, scheduled_builds_only: bool = True,
                              artifact: BambooArtifact = BambooArtifact.ERADICATION, out_path: str = None) -> list:
    """
    Downloads artifact(s) for a DTK Bamboo build plan to the specified path

    Args:
        plan_key (str):
        build_num (str):
        scheduled_builds_only (bool):
        artifact (BambooArtifact):
        out_path (str): Output path to save file (default to current directory)

    Returns:
        Returns list of downloaded files on filesystem
    """
    bamboo_api_login()
    if not out_path:
        out_path = os.getcwd()
    if not build_num:
        build_num, build_info = bamboo_api.BuildInfo.get_latest_successful_build(plan_key,
                                                                                 scheduled_only=scheduled_builds_only)
    if not build_num:
        raise FileNotFoundError(f"Could not find a successful build for plan {plan_key}. Please check plan name again")

    artifact_list = list()
    if artifact & BambooArtifact.ERADICATION:
        artifact_list.append(bamboo_api.BuildArtifacts.ERADICATION_EXE)
    if artifact & BambooArtifact.SCHEMA:
        artifact_list.append(bamboo_api.BuildArtifacts.SCHEMA_JSON)
    if artifact & BambooArtifact.PLUGINS:
        artifact_list.append(bamboo_api.BuildArtifacts.REPORTER_PLUGINS)

    user_logger.debug('Downloading ({}) artifact(s) from build {}#{}'.format(', '.join(artifact_list), plan_key, build_num))

    downloaded_files = bamboo_api.BuildArtifacts.download_artifacts_to_path(plan_key=plan_key,
                                                                            build_num=int(build_num),
                                                                            artifact=artifact_list,
                                                                            destination_path=out_path)

    # check for Eradication binary and mark as executable on linux
    for downloaded_file in downloaded_files:
        if os.path.basename(downloaded_file) == 'Eradication':
            bamboo_api.BuildArtifacts.make_exe_executable(downloaded_file)

    return downloaded_files


def download_latest_bamboo(plan: EradicationBambooBuilds, scheduled_builds_only: bool = True,
                           out_path: str = None) -> str:
    """
    Downloads the Eradication binary for the latest successful build for a Bamboo Plan to specified path. Exists for
    backward compatibility, just a pass-thru to download_latest_eradication().

    Args:
        plan: Bamboo Plan key. for supported build
        out_path: Output path to save file (default to current directory)

    Returns:
        Returns local filename of downloaded file
    """
    return download_latest_eradication(plan, scheduled_builds_only=scheduled_builds_only, out_path=out_path)


def download_latest_eradication(plan: EradicationBambooBuilds, scheduled_builds_only: bool = True,
                                out_path: str = None) -> str:
    """
    Downloads the Eradication binary for the latest successful build for a Bamboo Plan to specified path.

    Args:
        plan: Bamboo Plan key. for supported build
        out_path: Output path to save file (default to current directory)

    Returns:
        Returns local filename of downloaded file
    """
    downloaded_files = download_bamboo_artifacts(plan.value, scheduled_builds_only=scheduled_builds_only,
                                                 artifact=BambooArtifact.ERADICATION, out_path=out_path)
    if len(downloaded_files) > 0:
        eradication_file = downloaded_files[0]
        bamboo_api.BuildArtifacts.make_exe_executable(eradication_file)
        return eradication_file
    return None


def download_latest_reporters(plan: EradicationBambooBuilds, scheduled_builds_only: bool = True,
                              out_path: str = None) -> list:
    """
    Downloads the reporter plugins for the latest successful build for a Bamboo Plan to specified path.

    Args:
        plan: Bamboo Plan key. for supported build
        out_path: Output path to save file (default to current directory)

    Returns:
        Returns list of local filenames of downloaded files
    """
    return download_bamboo_artifacts(plan.value, scheduled_builds_only=scheduled_builds_only,
                                     artifact=BambooArtifact.PLUGINS, out_path=out_path)


def download_latest_schema(plan: EradicationBambooBuilds, scheduled_builds_only: bool = True,
                           out_path: str = None) -> str:
    """
    Downloads the schema.json for the latest successful build for a Bamboo Plan to specified path.

    Args:
        plan: Bamboo Plan key. for supported build
        out_path: Output path to save file (default to current directory)

    Returns:
        Returns local filename of downloaded file
    """
    downloaded_files = download_bamboo_artifacts(plan.value, scheduled_builds_only=scheduled_builds_only,
                                                 artifact=BambooArtifact.SCHEMA, out_path=out_path)
    if len(downloaded_files) > 1:
        return downloaded_files[0]
    return None


def download_from_url(url, out_path: str = None) -> str:
    if not out_path:
        out_path = os.getcwd()
    downloaded_file = bamboo_api.BuildArtifacts.download_from_bamboo_url(url, out_path)
    return downloaded_file


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
        cache_path = os.path.join(str(Path.home()), '.local_data', "eradication-cache")
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
