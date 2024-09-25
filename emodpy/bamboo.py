import os
import sys
from logging import getLogger
from emodpy.utils import bamboo_api_login, download_latest_eradication, download_latest_schema, download_latest_reporters
from emod_api.schema import get_schema as gs

user_logger = getLogger('user')


def get_model_files(plan, manifest, scheduled_builds_only=True, skip_build_schema=True):
    bamboo_api_login()
    download_latest_eradication(plan=plan, scheduled_builds_only=scheduled_builds_only, out_path=manifest.eradication_path)
    download_latest_reporters(plan=plan, scheduled_builds_only=scheduled_builds_only, out_path=manifest.plugins_folder)
    # if not on same platform as binary get schema from remote.
    if skip_build_schema or os.name != "posix" or sys.version_info.major != 3 or sys.version_info.minor != 6:
        download_latest_schema(plan=plan, scheduled_builds_only=scheduled_builds_only, out_path=manifest.schema_file)
    else:  # very much hardcoding SLURM target
        gs.dtk_to_schema(manifest.eradication_path, path_to_write_schema=manifest.schema_file)
