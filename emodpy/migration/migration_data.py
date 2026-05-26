from collections import defaultdict
from datetime import datetime
from functools import partial
import json
import logging
from os import environ
from pathlib import Path
from platform import system
from typing import Optional, Union

import numpy as np
from geographiclib.geodesic import Geodesic

from emodpy.utils.emod_enum import MigrationType, InterpolationType

logger = logging.getLogger(__name__)

MALE = 0
FEMALE = 1

SAME_FOR_BOTH_GENDERS = "SAME_FOR_BOTH_GENDERS"
ONE_FOR_EACH_GENDER = "ONE_FOR_EACH_GENDER"

_MIGRATION_TYPE_STRINGS = {
    MigrationType.LOCAL: "LOCAL_MIGRATION",
    MigrationType.AIR: "AIR_MIGRATION",
    MigrationType.REGIONAL: "REGIONAL_MIGRATION",
    MigrationType.SEA: "SEA_MIGRATION",
    MigrationType.FAMILY: "FAMILY_MIGRATION",
}


def _author():
    """Return the current OS username for metadata authorship."""
    if system() == "Windows":
        return environ.get("USERNAME", "Unknown")
    return environ.get("USER", "Unknown")


def _compute_gravity_rate(grav_params, from_pop, to_pop, distance_km):
    """Compute a single migration rate using the gravity model formula.

    rate = g[0] * from_pop^g[1] * to_pop^g[2] * distance_km^g[3], capped at 1.0.
    Returns 0.0 if any of from_pop, to_pop, or distance_km is zero.

    Args:
        grav_params: list of 4 floats [g0, g1, g2, g3]
        from_pop: population of the source node
        to_pop: population of the destination node
        distance_km: geodesic distance between nodes in kilometers

    Returns:
        float migration rate in [0.0, 1.0]
    """
    if from_pop == 0 or to_pop == 0 or distance_km == 0:
        return 0.0
    rate = (grav_params[0]
            * (from_pop ** grav_params[1])
            * (to_pop ** grav_params[2])
            * (distance_km ** grav_params[3]))
    return float(min(1.0, rate))


class MigrationData:
    """Type-agnostic container for migration rate data.

    Holds rates as (from_node, to_node) -> rate with optional gender and age layers.
    The layer order mirrors EMOD binary format: gender-major, age-minor.

    Create via classmethods: ``from_gravity_model``, ``from_rates``, ``from_migration_file``,
    ``from_csv``, ``combine``.
    Modify via ``apply_modifier``.
    Assign to a simulation via ``Demographics.add_migration``.
    """

    MALE = MALE
    FEMALE = FEMALE

    def __init__(self):
        self._idref = ""
        self._gender_data_type = SAME_FOR_BOTH_GENDERS
        self._ages = []
        self._layers = [{}]
        self._user_notes = None

    @property
    def idref(self):
        """The IdReference string, must match the demographics idref."""
        return self._idref

    @property
    def gender_data_type(self):
        """SAME_FOR_BOTH_GENDERS or ONE_FOR_EACH_GENDER."""
        return self._gender_data_type

    @property
    def ages(self):
        """List of age boundary values (years), or empty if no age dependence."""
        return list(self._ages)

    @property
    def user_notes(self):
        """Free-text description of this migration data, or None."""
        return self._user_notes

    @property
    def node_ids(self):
        """Sorted list of all unique node IDs (source and destination) across all layers."""
        ids = set()
        for layer in self._layers:
            for from_id, to_id in layer:
                ids.add(from_id)
                ids.add(to_id)
        return sorted(ids)

    @property
    def num_layers(self):
        """Total number of rate layers: num_genders * max(len(ages), 1)."""
        return len(self._layers)

    def get_layer(self, gender=0, age_index=0):
        """Get the rate dict for a specific gender/age combination.

        Args:
            gender: MALE (0) or FEMALE (1)
            age_index: index into self.ages (0 if no age dependence)

        Returns:
            dict of {(from_id, to_id): rate}
        """
        num_ages = max(len(self._ages), 1)
        index = gender * num_ages + age_index
        return self._layers[index]

    @classmethod
    def from_gravity_model(cls, demographics, gravity_params, female_multiplier=None):
        """Generate migration rates from a gravity model using demographics node data.

        Args:
            demographics: Demographics object with .nodes and .idref
            gravity_params: list of 4 floats [g0, g1, g2, g3].
                rate = g0 * from_pop^g1 * to_pop^g2 * distance_km^g3, capped at 1.0
            female_multiplier: if provided, creates ONE_FOR_EACH_GENDER data where
                female_rate = male_rate * female_multiplier

        Returns:
            MigrationData
        """
        if len(gravity_params) != 4:
            raise ValueError(f"gravity_params must have exactly 4 values, got {len(gravity_params)}")

        nodes = [n for n in demographics.nodes if n.id != 0]
        if len(nodes) < 2:
            raise ValueError(f"Need at least 2 non-default nodes for migration, got {len(nodes)}")

        geodesic = Geodesic.WGS84
        male_rates = {}

        for src in nodes:
            for dst in nodes:
                if src is dst:
                    continue
                dist_m = geodesic.Inverse(src.lat, src.lon, dst.lat, dst.lon, Geodesic.DISTANCE)['s12']
                dist_km = dist_m / 1000.0
                rate = _compute_gravity_rate(gravity_params, src.pop, dst.pop, dist_km)
                if rate > 0:
                    male_rates[(src.id, dst.id)] = rate

        data = cls()
        data._idref = demographics.idref

        if female_multiplier is not None:
            data._gender_data_type = ONE_FOR_EACH_GENDER
            female_rates = {k: min(1.0, v * female_multiplier) for k, v in male_rates.items()}
            data._layers = [male_rates, female_rates]
        else:
            data._layers = [male_rates]

        return data

    @classmethod
    def from_rates(cls, rates, idref="", female_rates=None, ages=None):
        """Create migration data from explicit rate dictionaries.

        Args:
            rates: migration rates for male vectors (or all if female_rates is None).
                Without ages: a single dict of ``{(from_node_id, to_node_id): rate}``.
                With ages: a list of such dicts, one per age in ``ages``, ordered by age.
            idref: IdReference string
            female_rates: optional female-specific rates (creates ONE_FOR_EACH_GENDER data).
                Same format as ``rates``: a single dict without ages, or a list of dicts with ages.
            ages: optional list of age boundary values (years), sorted ascending.
                When provided, ``rates`` (and ``female_rates``) must be lists of dicts with
                length matching ``len(ages)``.

        Returns:
            MigrationData
        """
        if ages is not None:
            ages = sorted(ages)
            if not isinstance(rates, list):
                raise TypeError("When ages is provided, rates must be a list of dicts (one per age).")
            if len(rates) != len(ages):
                raise ValueError(f"rates has {len(rates)} layers but ages has {len(ages)} entries.")
            if female_rates is not None:
                if not isinstance(female_rates, list):
                    raise TypeError("When ages is provided, female_rates must be a list of dicts (one per age).")
                if len(female_rates) != len(ages):
                    raise ValueError(f"female_rates has {len(female_rates)} layers but ages has {len(ages)} entries.")
            all_layers = list(rates)
        else:
            if not isinstance(rates, dict):
                raise TypeError("Without ages, rates must be a single dict of {(from, to): rate}.")
            all_layers = [rates]

        if female_rates is not None:
            if ages is not None:
                all_layers.extend(female_rates)
            else:
                if not isinstance(female_rates, dict):
                    raise TypeError("Without ages, female_rates must be a single dict of {(from, to): rate}.")
                all_layers.append(female_rates)

        for i, layer in enumerate(all_layers):
            for k, v in layer.items():
                if k[0] == 0 or k[1] == 0:
                    raise ValueError(f"Layer {i}: migration to/from default node (ID=0) is not allowed.")
                if v < 0 or v > 1.0:
                    raise ValueError(f"Layer {i}: rate must be in [0.0, 1.0], got {v} for pair {k}.")

        data = cls()
        data._idref = idref
        data._layers = [dict(layer) for layer in all_layers]
        data._ages = ages if ages else []

        if female_rates is not None:
            data._gender_data_type = ONE_FOR_EACH_GENDER

        return data

    def apply_modifier(self, ages, modifier_fn):
        """Create age (and optionally gender) dependent rates from base rates.

        Args:
            ages: list of age boundary values (e.g. [0, 15, 65]). Must be sorted ascending.
            modifier_fn: callable(base_rate, age, gender) -> modified_rate
                Called for each (from, to, age, gender) combination.
                gender is 0 (MALE) or 1 (FEMALE).
                If base data is SAME_FOR_BOTH_GENDERS, gender is always 0.

        Returns:
            New MigrationData with age layers (and gender layers if base had them)
        """
        if not ages:
            raise ValueError("ages must be a non-empty list")
        if 0 in self.node_ids:
            raise ValueError("Migration data must not contain default node (ID=0).")
        ages = sorted(ages)

        num_genders = 2 if self._gender_data_type == ONE_FOR_EACH_GENDER else 1
        new_layers = []

        for gender in range(num_genders):
            base_layer = self._layers[gender] if len(self._layers) > gender else self._layers[0]
            for age in ages:
                new_layer = {}
                for (from_id, to_id), base_rate in base_layer.items():
                    new_rate = modifier_fn(base_rate, age, gender)
                    if new_rate > 0:
                        new_layer[(from_id, to_id)] = min(1.0, new_rate)
                new_layers.append(new_layer)

        result = MigrationData()
        result._idref = self._idref
        result._gender_data_type = self._gender_data_type
        result._ages = ages
        result._layers = new_layers
        return result

    @classmethod
    def combine(cls, layers_dict):
        """Merge multiple MigrationData objects into one age+gender file.

        Args:
            layers_dict: dict of {(gender, age): MigrationData}
                gender: MALE (0) or FEMALE (1)
                age: float age boundary value
                Each MigrationData must be simple (no age/gender layers of its own).

        Returns:
            Combined MigrationData with appropriate age and gender layers.
        """
        if not layers_dict:
            raise ValueError("layers_dict must not be empty")

        genders = sorted(set(g for g, a in layers_dict.keys()))
        ages = sorted(set(a for g, a in layers_dict.keys()))

        if genders == [MALE]:
            gender_data_type = SAME_FOR_BOTH_GENDERS
        elif genders == [MALE, FEMALE]:
            gender_data_type = ONE_FOR_EACH_GENDER
        else:
            raise ValueError(f"Invalid gender values in keys: {genders}. Use MigrationData.MALE (0) and/or MigrationData.FEMALE (1).")

        idrefs = set()
        for md in layers_dict.values():
            if md.num_layers != 1:
                raise ValueError("Each MigrationData in layers_dict must be simple (1 layer, no age/gender).")
            if 0 in md.node_ids:
                raise ValueError("Migration data must not contain default node (ID=0).")
            idrefs.add(md.idref)

        if len(idrefs) > 1:
            raise ValueError(f"All MigrationData must share the same idref, got: {idrefs}")

        new_layers = []
        for gender in genders:
            for age in ages:
                key = (gender, age)
                if key not in layers_dict:
                    raise ValueError(f"Missing layer for (gender={gender}, age={age}). "
                                     f"All gender/age combinations must be provided.")
                new_layers.append(dict(layers_dict[key]._layers[0]))

        result = cls()
        result._idref = idrefs.pop()
        result._gender_data_type = gender_data_type
        result._ages = ages
        result._layers = new_layers
        return result

    @classmethod
    def from_migration_file(cls, binary_path, metafile=None):
        """Load migration data from an existing EMOD binary + JSON metadata file.

        Args:
            binary_path: path to the binary migration file
            metafile: path to JSON metadata file (default: binary_path + ".json"). Default is to look for a .json
                file with the same name as the binary in the same directory.

        Returns:
            MigrationData
        """
        binary_path = Path(binary_path).absolute()
        metafile = Path(metafile) if metafile else binary_path.parent / (binary_path.name + ".json")

        if not binary_path.exists():
            raise FileNotFoundError(f"Binary file not found: {binary_path}")
        if not metafile.exists():
            raise FileNotFoundError(f"Metadata file not found: {metafile}")

        with metafile.open("r") as f:
            jason = json.load(f)

        metadata = jason["Metadata"]
        node_count = metadata["NodeCount"]
        datavalue_count = metadata["DatavalueCount"]
        gender_data_type = metadata.get("GenderDataType", SAME_FOR_BOTH_GENDERS)
        ages = metadata.get("AgesYears", [])
        idref = metadata.get("IdReference", "")

        # NodeOffsets is a hex string: each node is 8 hex chars for ID + 8 hex chars for byte offset
        node_offsets_str = jason["NodeOffsets"]
        offsets = {}
        for i in range(node_count):
            base = 16 * i
            node_id = int(node_offsets_str[base:base + 8], 16)
            offset = int(node_offsets_str[base + 8:base + 16], 16)
            offsets[node_id] = offset

        num_genders = 2 if gender_data_type == ONE_FOR_EACH_GENDER else 1
        num_ages = len(ages) if ages else 1
        # Each node's data is datavalue_count entries of (uint32 dest + float64 rate) = 12 bytes each
        age_data_size = node_count * datavalue_count * 12
        # Binary layout: [gender0_age0, gender0_age1, ..., gender1_age0, gender1_age1, ...]
        gender_data_size = num_ages * age_data_size

        # Skip default node (ID=0) — it must never appear as source or destination
        offsets.pop(0, None)

        layers = []
        with binary_path.open("rb") as f:
            for gender in range(num_genders):
                for age_idx in range(num_ages):
                    layer = {}
                    for node_id, node_offset in offsets.items():
                        file_offset = gender * gender_data_size + age_idx * age_data_size + node_offset
                        f.seek(file_offset)
                        destinations = np.fromfile(f, dtype=np.uint32, count=datavalue_count)
                        rates = np.fromfile(f, dtype=np.float64, count=datavalue_count)
                        for dest, rate in zip(destinations, rates):
                            if rate > 0 and dest > 0:
                                layer[(node_id, int(dest))] = float(rate)
                    layers.append(layer)

        data = cls()
        data._idref = idref
        data._gender_data_type = gender_data_type
        data._ages = ages
        data._layers = layers
        data._user_notes = metadata.get("USER_NOTES", None)
        return data

    @classmethod
    def from_csv(cls, csv_path, idref=""):
        """Load migration data from a CSV file.

        Accepts CSV files with or without a header row. The expected column formats are:

        - 3 columns: ``source_node, destination_node, rate``
          (SAME_FOR_BOTH_GENDERS, no age dependence)
        - 4 columns: ``source_node, gender, destination_node, rate``
          (ONE_FOR_EACH_GENDER, no age dependence)
        - 4 columns: ``source_node, age, destination_node, rate``
          (SAME_FOR_BOTH_GENDERS, with age dependence)
        - 5 columns: ``source_node, gender, age, destination_node, rate``
          (ONE_FOR_EACH_GENDER, with age dependence)

        If a header row is present, column names are used to determine the format.
        If no header is present and there are exactly 3 numeric columns, assumes
        ``source_node, destination_node, rate``. For 4+ columns without a header,
        raises ValueError with the expected format.

        Args:
            csv_path: path to the CSV file
            idref: IdReference string to assign to the resulting MigrationData

        Returns:
            MigrationData
        """
        import csv

        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with csv_path.open('r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            raise ValueError("CSV file is empty.")

        # Detect whether the first row is a header
        header = None
        first_row = rows[0]
        try:
            [float(v) for v in first_row]
        except ValueError:
            header = [c.strip().lower() for c in first_row]
            rows = rows[1:]

        if not rows:
            raise ValueError("CSV file has no data rows.")

        num_cols = len(rows[0])

        if header is not None:
            has_gender = 'gender' in header
            has_age = 'age' in header
            try:
                src_idx = header.index('source_node')
                dst_idx = header.index('destination_node')
                rate_idx = header.index('rate')
            except ValueError:
                raise ValueError(
                    f"CSV header must contain 'source_node', 'destination_node', and 'rate'. "
                    f"Got: {header}")
            gender_idx = header.index('gender') if has_gender else None
            age_idx = header.index('age') if has_age else None
        else:
            if num_cols == 3:
                src_idx, dst_idx, rate_idx = 0, 1, 2
                has_gender = False
                has_age = False
                gender_idx = None
                age_idx = None
            else:
                raise ValueError(
                    f"CSV has {num_cols} columns but no header row. Cannot determine format.\n"
                    f"Expected CSV formats:\n"
                    f"  3 columns: source_node, destination_node, rate\n"
                    f"  4 columns: source_node, gender, destination_node, rate\n"
                    f"       -or-: source_node, age, destination_node, rate\n"
                    f"  5 columns: source_node, gender, age, destination_node, rate\n"
                    f"Add a header row to specify the format.")

        # Parse rows into structured records
        records = []
        for row_num, row in enumerate(rows, start=2 if header else 1):
            if len(row) != num_cols:
                raise ValueError(f"Row {row_num} has {len(row)} columns, expected {num_cols}.")
            src = int(row[src_idx])
            dst = int(row[dst_idx])
            rate = float(row[rate_idx])
            gender = int(row[gender_idx]) if gender_idx is not None else 0
            age = float(row[age_idx]) if age_idx is not None else 0.0

            if src == 0 or dst == 0:
                raise ValueError(f"Row {row_num}: migration to/from default node (ID=0) is not allowed.")
            if rate < 0 or rate > 1.0:
                raise ValueError(f"Row {row_num}: rate must be in [0.0, 1.0], got {rate}.")

            records.append((src, dst, rate, gender, age))

        # Determine structure
        genders = sorted(set(r[3] for r in records))
        ages = sorted(set(r[4] for r in records))

        if has_gender or genders == [MALE, FEMALE]:
            gender_data_type = ONE_FOR_EACH_GENDER
        else:
            gender_data_type = SAME_FOR_BOTH_GENDERS
            genders = [MALE]

        if not has_age:
            ages = []

        # Build layers in gender-major, age-minor order
        num_ages = max(len(ages), 1)
        layers = [{} for _ in range(len(genders) * num_ages)]
        age_list = ages if ages else [0.0]

        for src, dst, rate, gender, age in records:
            g_idx = genders.index(gender) if gender in genders else 0
            a_idx = age_list.index(age) if age in age_list else 0
            layer_idx = g_idx * num_ages + a_idx
            if rate > 0:
                layers[layer_idx][(src, dst)] = rate

        data = cls()
        data._idref = idref
        data._gender_data_type = gender_data_type
        data._ages = ages
        data._layers = layers
        return data

    def to_migration_file(self, path, migration_type: Union[MigrationType, str] = MigrationType.LOCAL,
                interpolation_type: Union[InterpolationType, str] = InterpolationType.PIECEWISE_CONSTANT,
                value_limit: int = 100,
                user_notes: Optional[str] = None):
        """Write migration data to EMOD binary format with JSON metadata sidecar.

        Args:
            path: output path for the binary file (metadata written to path + ".json")
            migration_type: MigrationType enum or string ("LOCAL", "AIR", "REGIONAL", "SEA", "FAMILY")
            interpolation_type: InterpolationType enum or string. Default PIECEWISE_CONSTANT.
            value_limit: max destinations per source node (default 100)
            user_notes: free-text description stored in metadata as USER_NOTES

        Returns:
            Path to binary file
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

        path = Path(path).absolute()
        metafile = path.parent / (path.name + ".json")

        if 0 in self.node_ids:
            raise ValueError("Migration data must not contain default node (ID=0). "
                             "Cannot write migration to/from the default node.")

        mig_type_str = _MIGRATION_TYPE_STRINGS[migration_type]

        source_nodes = set()
        for layer in self._layers:
            source_nodes |= set(from_id for from_id, _ in layer)
        source_nodes = sorted(source_nodes)

        # DatavalueCount = max destinations per source node, capped by value_limit
        max_dests = 0
        for layer in self._layers:
            dests_per_node = defaultdict(int)
            for from_id, _ in layer:
                dests_per_node[from_id] += 1
            if dests_per_node:
                max_dests = max(max_dests, max(dests_per_node.values()))
        actual_dvc = min(max_dests, value_limit)
        if actual_dvc == 0:
            actual_dvc = 1

        # Each node's chunk is actual_dvc * (4 bytes uint32 + 8 bytes float64) = 12 * actual_dvc bytes
        offsets = {node: 12 * i * actual_dvc for i, node in enumerate(source_nodes)}
        # Hex-encoded node offsets: 8 chars node ID + 8 chars byte offset per node
        node_offsets_str = ''.join(f"{node:08x}{offsets[node]:08x}" for node in source_nodes)

        metadata = {
            "Metadata": {
                "Author": _author(),
                "DateCreated": f"{datetime.now():%a %b %d %Y %H:%M:%S}",
                "Tool": "emodpy",
                "IdReference": self._idref,
                "MigrationType": mig_type_str,
                "NodeCount": len(source_nodes),
                "DatavalueCount": actual_dvc,
                "GenderDataType": self._gender_data_type,
                "InterpolationType": str(interpolation_type),
            },
            "NodeOffsets": node_offsets_str
        }
        if self._ages:
            metadata["Metadata"]["AgesYears"] = self._ages
        if user_notes is not None:
            metadata["Metadata"]["USER_NOTES"] = user_notes

        with metafile.open("w") as f:
            json.dump(metadata, f, indent=4, separators=(",", ": "))

        # Write binary: layers in gender-major, age-minor order.
        # Per layer, per source node: N×uint32 destination IDs then N×float64 rates.
        # Destinations are truncated to top actual_dvc by rate, then sorted ascending by rate.
        with path.open("wb") as f:
            for layer in self._layers:
                rates_by_source = defaultdict(list)
                for (from_id, to_id), rate in layer.items():
                    rates_by_source[from_id].append((to_id, rate))

                for node in source_nodes:
                    pairs = rates_by_source.get(node, [])
                    # Keep only the highest-rate destinations if exceeding value_limit
                    pairs.sort(key=lambda x: x[1], reverse=True)
                    if len(pairs) > actual_dvc:
                        pairs = pairs[:actual_dvc]
                    pairs.sort(key=lambda x: x[1])

                    destinations = np.zeros(actual_dvc, dtype=np.uint32)
                    rates = np.zeros(actual_dvc, dtype=np.float64)
                    for i, (dest, rate) in enumerate(pairs):
                        destinations[i] = dest
                        rates[i] = rate

                    destinations.tofile(f)
                    rates.tofile(f)

        return path

    def to_csv(self, path):
        """Write migration data to CSV format for inspection.

        Columns: source_node, destination_node, rate (plus gender, age when applicable).

        Args:
            path: output CSV file path
        """
        import csv

        path = Path(path)
        by_gender = self._gender_data_type == ONE_FOR_EACH_GENDER
        by_age = bool(self._ages)

        columns = ['source_node']
        if by_gender:
            columns.append('gender')
        if by_age:
            columns.append('age')
        columns.extend(['destination_node', 'rate'])

        num_genders = 2 if by_gender else 1
        ages = self._ages if by_age else [None]

        with path.open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for gender in range(num_genders):
                for age_idx, age in enumerate(ages):
                    layer = self._layers[gender * max(len(self._ages), 1) + age_idx]
                    for (from_id, to_id), rate in sorted(layer.items()):
                        row = [from_id]
                        if by_gender:
                            row.append(gender)
                        if by_age:
                            row.append(age)
                        row.extend([to_id, rate])
                        writer.writerow(row)
