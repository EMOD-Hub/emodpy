from functools import partial
import logging
from pathlib import Path
from typing import List, Optional, Union

from emod_api.demographics.demographics import Demographics as EMODAPIDemographics
from emod_api.demographics.node import Node

from emodpy.utils.emod_enum import MigrationType, MigrationPattern, InterpolationType

logger = logging.getLogger(__name__)


def _set_migration_config(config, migration_type, filename, x_modifier,
                          migration_pattern,
                          roundtrip_duration, roundtrip_probability, roundtrip_waypoints):
    """Implicit config function registered by add_migration().

    Called at task build time to set all EMOD config parameters for one migration type:
    Migration_Model, Enable_*_Migration, *_Migration_Filename, x_*_Migration,
    and Migration_Pattern with its dependent parameters.

    Args:
        config: simulation config object with a ``parameters`` attribute
        migration_type: MigrationType enum value
        filename: binary migration filename (name only, not full path)
        x_modifier: rate multiplier (x_*_Migration)
        migration_pattern: MigrationPattern enum value
        roundtrip_duration: days at destination, or None to skip (SINGLE_ROUND_TRIPS only)
        roundtrip_probability: probability of return trip, or None to skip (SINGLE_ROUND_TRIPS only)
        roundtrip_waypoints: max waypoints before returning home, or None to skip (WAYPOINTS_HOME only)

    Returns:
        config with migration parameters set
    """
    prefix = migration_type.value.title()
    config.parameters.Migration_Model = "FIXED_RATE_MIGRATION"
    setattr(config.parameters, f"Enable_{prefix}_Migration", 1)
    setattr(config.parameters, f"{prefix}_Migration_Filename", filename)
    setattr(config.parameters, f"x_{prefix}_Migration", x_modifier)
    config.parameters.Migration_Pattern = str(migration_pattern)
    if migration_pattern == MigrationPattern.SINGLE_ROUND_TRIPS:
        if roundtrip_duration is not None:
            setattr(config.parameters, f"{prefix}_Migration_Roundtrip_Duration", roundtrip_duration)
        if roundtrip_probability is not None:
            setattr(config.parameters, f"{prefix}_Migration_Roundtrip_Probability", roundtrip_probability)
    elif migration_pattern == MigrationPattern.WAYPOINTS_HOME:
        if roundtrip_waypoints is not None:
            config.parameters.Roundtrip_Waypoints = roundtrip_waypoints
    return config


class Demographics(EMODAPIDemographics):

    def __init__(self, nodes: List[Node], default_node: Node = None, idref: str = None, set_defaults: bool = True):
        super().__init__(nodes=nodes, default_node=default_node, idref=idref, set_defaults=set_defaults)

    # Forces emodpy-layer Demographics instantiation to use Node object-route for default node . Cannot use
    # the old self.raw dict representation of a default node.

    @property
    def raw(self):
        raise AttributeError("raw is not a valid attribute for Demographics objects")

    @raw.setter
    def raw(self, value):
        raise AttributeError("raw is not a valid attribute for Demographics objects")

    def add_migration(self, data, migration_type: Union[MigrationType, str],
                      x_modifier: float = 1.0,
                      interpolation_type: Union[InterpolationType, str] = InterpolationType.PIECEWISE_CONSTANT,
                      migration_pattern: Union[MigrationPattern, str] = MigrationPattern.RANDOM_WALK_DIFFUSION,
                      roundtrip_duration: Optional[float] = None,
                      roundtrip_probability: Optional[float] = None,
                      roundtrip_waypoints: Optional[int] = None,
                      filename: Optional[str] = None,
                      user_notes: Optional[str] = None):
        """Assign migration data to a migration type, write the file, and set config params.

        Args:
            data: MigrationData object containing the rate data
            migration_type: MigrationType enum or string ("LOCAL", "AIR", "REGIONAL", "SEA", "FAMILY")
            x_modifier: migration rate multiplier (x_*_Migration config param). Default 1.0
            interpolation_type: InterpolationType enum or string. Default PIECEWISE_CONSTANT.
            migration_pattern: MigrationPattern enum or string. Default RANDOM_WALK_DIFFUSION.
                SINGLE_ROUND_TRIPS: uses roundtrip_duration and roundtrip_probability.
                WAYPOINTS_HOME: uses roundtrip_waypoints.
                RANDOM_WALK_DIFFUSION: no additional parameters.
            roundtrip_duration: days at destination (*_Roundtrip_Duration).
                Only used with SINGLE_ROUND_TRIPS. Default None.
            roundtrip_probability: probability of return trip (*_Roundtrip_Probability).
                Only used with SINGLE_ROUND_TRIPS. Default None.
            roundtrip_waypoints: max waypoints before returning home (Roundtrip_Waypoints).
                Only used with WAYPOINTS_HOME. Default None.
            filename: output path for the binary file. If None, auto-generates based on migration_type.
            user_notes: free-text description of this migration file — motivation, data source,
                assumptions, etc. We encourage you to record why this file was created so
                the context is preserved for future reference. Stored in the JSON metadata
                sidecar as USER_NOTES.
        """
        if not isinstance(migration_type, MigrationType):
            try:
                migration_type = MigrationType(migration_type.upper())
            except ValueError:
                raise ValueError(f"Invalid migration_type '{migration_type}'. "
                                 f"Valid options: {list(MigrationType)}")
        if not isinstance(interpolation_type, InterpolationType):
            try:
                interpolation_type = InterpolationType(interpolation_type)
            except ValueError:
                raise ValueError(f"Invalid interpolation_type '{interpolation_type}'. "
                                 f"Valid options: {list(InterpolationType)}")
        if not isinstance(migration_pattern, MigrationPattern):
            try:
                migration_pattern = MigrationPattern(migration_pattern.upper())
            except ValueError:
                raise ValueError(f"Invalid migration_pattern '{migration_pattern}'. "
                                 f"Valid options: {list(MigrationPattern)}")

        if migration_pattern != MigrationPattern.SINGLE_ROUND_TRIPS:
            if roundtrip_duration is not None or roundtrip_probability is not None:
                raise ValueError("roundtrip_duration and roundtrip_probability are only valid "
                                 "with migration_pattern=SINGLE_ROUND_TRIPS.")
        if migration_pattern != MigrationPattern.WAYPOINTS_HOME:
            if roundtrip_waypoints is not None:
                raise ValueError("roundtrip_waypoints is only valid "
                                 "with migration_pattern=WAYPOINTS_HOME.")

        valid_ids = {n.id for n in self.nodes if n.id != 0}
        data_ids = set(data.node_ids)
        unknown = data_ids - valid_ids
        if unknown:
            raise ValueError(f"Migration data contains node IDs not in demographics: {sorted(unknown)}")

        if data.idref != self.idref:
            logger.warning(f"MigrationData idref '{data.idref}' does not match demographics "
                           f"idref '{self.idref}', but the Nodes match. Updating migration idref to '{self.idref}'.")
            data._idref = self.idref

        if filename is None:
            filename = f"{str(migration_type).lower()}_migration.bin"
        path = Path(filename).absolute()

        data.to_migration_file(path, migration_type=migration_type, interpolation_type=interpolation_type,
                               user_notes=user_notes)
        self.migration_files.append(path)

        bin_filename = path.name
        self.implicits.append(partial(
            _set_migration_config,
            migration_type=migration_type,
            filename=bin_filename,
            x_modifier=x_modifier,
            migration_pattern=migration_pattern,
            roundtrip_duration=roundtrip_duration,
            roundtrip_probability=roundtrip_probability,
            roundtrip_waypoints=roundtrip_waypoints,
        ))
