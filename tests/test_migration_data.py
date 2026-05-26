import os
import tempfile
import unittest
from pathlib import Path

from emod_api.demographics.node import Node
from emodpy.demographics.demographics import Demographics
from emodpy.migration.migration_data import MigrationData, MALE, FEMALE, SAME_FOR_BOTH_GENDERS, ONE_FOR_EACH_GENDER
from emodpy.utils.emod_enum import MigrationType, MigrationPattern, InterpolationType


def _make_demographics(num_nodes=3):
    """Create a simple Demographics with nodes at known lat/lon."""
    nodes = []
    for i in range(num_nodes):
        nodes.append(Node(lat=float(i), lon=float(i), pop=10000 * (i + 1), forced_id=i + 1))
    return Demographics(nodes=nodes, idref="test_migration")


class TestMigrationDataGravity(unittest.TestCase):

    def test_basic_gravity(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, gravity_params=[1e-4, 1, 1, -1])

        self.assertEqual(data.idref, "test_migration")
        self.assertEqual(data.gender_data_type, SAME_FOR_BOTH_GENDERS)
        self.assertEqual(data.ages, [])
        self.assertEqual(data.num_layers, 1)
        self.assertTrue(len(data.node_ids) > 0)

        layer = data.get_layer()
        self.assertGreater(len(layer), 0)
        for (src, dst), rate in layer.items():
            self.assertGreater(rate, 0)
            self.assertLessEqual(rate, 1.0)
            self.assertNotEqual(src, dst)

    def test_gravity_with_female_multiplier(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.5)

        self.assertEqual(data.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(data.num_layers, 2)

        male_layer = data.get_layer(gender=MALE)
        female_layer = data.get_layer(gender=FEMALE)

        for key, male_rate in male_layer.items():
            self.assertIn(key, female_layer)
            self.assertAlmostEqual(female_layer[key], male_rate * 0.5, places=10)

    def test_gravity_too_few_nodes(self):
        nodes = [Node(lat=0, lon=0, pop=1000, forced_id=1)]
        demog = Demographics(nodes=nodes, idref="test")
        with self.assertRaises(ValueError):
            MigrationData.from_gravity_model(demog, [1, 1, 1, -1])

    def test_gravity_bad_params(self):
        demog = _make_demographics()
        with self.assertRaises(ValueError):
            MigrationData.from_gravity_model(demog, [1, 1, 1])

    def test_to_file_rejects_node_zero(self):
        # Manually inject node ID=0 into migration data; verify to_file rejects it
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        data._layers[0][(0, 1)] = 0.1

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "bad.bin")
            with self.assertRaises(ValueError):
                data.to_migration_file(binpath, migration_type=MigrationType.LOCAL)

    def test_combine_rejects_node_zero(self):
        # Manually inject node ID=0 into migration data; verify combine rejects it
        demog = _make_demographics(3)
        male_data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        male_data._layers[0][(0, 2)] = 0.3

        female_data = MigrationData.from_gravity_model(demog, [5e-5, 1, 1, -1])
        with self.assertRaises(ValueError):
            MigrationData.combine({(MALE, 0): male_data, (FEMALE, 0): female_data})


class TestMigrationDataModifier(unittest.TestCase):

    def test_apply_modifier_ages(self):
        demog = _make_demographics(3)
        base = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        def age_mod(base_rate, age, gender):
            if age < 15:
                return base_rate * 0.5
            return base_rate

        modified = base.apply_modifier(ages=[0, 15, 65], modifier_fn=age_mod)

        self.assertEqual(modified.ages, [0, 15, 65])
        self.assertEqual(modified.num_layers, 3)
        self.assertEqual(modified.gender_data_type, SAME_FOR_BOTH_GENDERS)

        base_layer = base.get_layer()
        young_layer = modified.get_layer(gender=0, age_index=0)
        adult_layer = modified.get_layer(gender=0, age_index=1)

        for key in base_layer:
            self.assertAlmostEqual(young_layer[key], base_layer[key] * 0.5, places=10)
            self.assertAlmostEqual(adult_layer[key], base_layer[key], places=10)

    def test_apply_modifier_gender_and_age(self):
        demog = _make_demographics(3)
        base = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.8)

        def mod_fn(base_rate, age, gender):
            return base_rate * (0.5 if age < 15 else 1.0)

        modified = base.apply_modifier(ages=[0, 15], modifier_fn=mod_fn)

        self.assertEqual(modified.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(modified.num_layers, 4)  # 2 genders × 2 ages


class TestMigrationDataCombine(unittest.TestCase):

    def test_combine_gender(self):
        demog = _make_demographics(3)
        male_data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        female_data = MigrationData.from_gravity_model(demog, [5e-5, 1, 1, -1])

        combined = MigrationData.combine({
            (MALE, 0): male_data,
            (FEMALE, 0): female_data,
        })

        self.assertEqual(combined.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(combined.ages, [0])
        self.assertEqual(combined.num_layers, 2)

    def test_combine_age_and_gender(self):
        demog = _make_demographics(3)
        young_m = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        old_m = MigrationData.from_gravity_model(demog, [5e-5, 1, 1, -1])
        young_f = MigrationData.from_gravity_model(demog, [8e-5, 1, 1, -1])
        old_f = MigrationData.from_gravity_model(demog, [3e-5, 1, 1, -1])

        combined = MigrationData.combine({
            (MALE, 0): young_m,
            (MALE, 30): old_m,
            (FEMALE, 0): young_f,
            (FEMALE, 30): old_f,
        })

        self.assertEqual(combined.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(combined.ages, [0, 30])
        self.assertEqual(combined.num_layers, 4)  # 2 genders × 2 ages

    def test_combine_mismatched_idref(self):
        nodes_a = [Node(lat=0, lon=0, pop=1000, forced_id=1),
                   Node(lat=1, lon=1, pop=2000, forced_id=2)]
        nodes_b = [Node(lat=0, lon=0, pop=1000, forced_id=1),
                   Node(lat=1, lon=1, pop=2000, forced_id=2)]
        demog_a = Demographics(nodes=nodes_a, idref="ref_a")
        demog_b = Demographics(nodes=nodes_b, idref="ref_b")

        data_a = MigrationData.from_gravity_model(demog_a, [1e-4, 1, 1, -1])
        data_b = MigrationData.from_gravity_model(demog_b, [1e-4, 1, 1, -1])

        with self.assertRaises(ValueError):
            MigrationData.combine({(MALE, 0): data_a, (FEMALE, 0): data_b})

    def test_combine_missing_key(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        with self.assertRaises(ValueError):
            MigrationData.combine({(MALE, 0): data, (FEMALE, 30): data})


class TestMigrationDataFromRates(unittest.TestCase):

    def test_simple_rates(self):
        rates = {(1, 2): 0.01, (2, 1): 0.005, (1, 3): 0.02}
        data = MigrationData.from_rates(rates, idref="test_ref")

        self.assertEqual(data.idref, "test_ref")
        self.assertEqual(data.gender_data_type, SAME_FOR_BOTH_GENDERS)
        self.assertEqual(data.ages, [])
        self.assertEqual(data.num_layers, 1)
        layer = data.get_layer()
        self.assertAlmostEqual(layer[(1, 2)], 0.01)
        self.assertAlmostEqual(layer[(2, 1)], 0.005)
        self.assertAlmostEqual(layer[(1, 3)], 0.02)

    def test_with_female_rates(self):
        male = {(1, 2): 0.01, (2, 1): 0.005}
        female = {(1, 2): 0.02, (2, 1): 0.01}
        data = MigrationData.from_rates(male, female_rates=female)

        self.assertEqual(data.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(data.num_layers, 2)
        self.assertAlmostEqual(data.get_layer(gender=MALE)[(1, 2)], 0.01)
        self.assertAlmostEqual(data.get_layer(gender=FEMALE)[(1, 2)], 0.02)

    def test_with_ages(self):
        young = {(1, 2): 0.01}
        old = {(1, 2): 0.005}
        data = MigrationData.from_rates([young, old], ages=[0, 15])

        self.assertEqual(data.gender_data_type, SAME_FOR_BOTH_GENDERS)
        self.assertEqual(data.ages, [0, 15])
        self.assertEqual(data.num_layers, 2)
        self.assertAlmostEqual(data.get_layer(gender=0, age_index=0)[(1, 2)], 0.01)
        self.assertAlmostEqual(data.get_layer(gender=0, age_index=1)[(1, 2)], 0.005)

    def test_with_ages_and_gender(self):
        m_young = {(1, 2): 0.01}
        m_old = {(1, 2): 0.005}
        f_young = {(1, 2): 0.02}
        f_old = {(1, 2): 0.01}
        data = MigrationData.from_rates(
            [m_young, m_old],
            female_rates=[f_young, f_old],
            ages=[0, 15],
        )

        self.assertEqual(data.gender_data_type, ONE_FOR_EACH_GENDER)
        self.assertEqual(data.ages, [0, 15])
        self.assertEqual(data.num_layers, 4)
        self.assertAlmostEqual(data.get_layer(gender=MALE, age_index=0)[(1, 2)], 0.01)
        self.assertAlmostEqual(data.get_layer(gender=MALE, age_index=1)[(1, 2)], 0.005)
        self.assertAlmostEqual(data.get_layer(gender=FEMALE, age_index=0)[(1, 2)], 0.02)
        self.assertAlmostEqual(data.get_layer(gender=FEMALE, age_index=1)[(1, 2)], 0.01)

    def test_roundtrip_file(self):
        rates = {(1, 2): 0.01, (2, 1): 0.005}
        data = MigrationData.from_rates(rates, idref="roundtrip")

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test_migration.bin"
            data.to_migration_file(path)
            loaded = MigrationData.from_migration_file(path)

        self.assertEqual(loaded.idref, "roundtrip")
        layer = loaded.get_layer()
        self.assertAlmostEqual(layer[(1, 2)], 0.01)
        self.assertAlmostEqual(layer[(2, 1)], 0.005)

    def test_rejects_node_zero(self):
        with self.assertRaises(ValueError):
            MigrationData.from_rates({(0, 1): 0.01})

    def test_rejects_rate_out_of_range(self):
        with self.assertRaises(ValueError):
            MigrationData.from_rates({(1, 2): 1.5})
        with self.assertRaises(ValueError):
            MigrationData.from_rates({(1, 2): -0.1})

    def test_ages_rates_length_mismatch(self):
        with self.assertRaises(ValueError):
            MigrationData.from_rates([{(1, 2): 0.01}], ages=[0, 15])

    def test_ages_requires_list(self):
        with self.assertRaises(TypeError):
            MigrationData.from_rates({(1, 2): 0.01}, ages=[0, 15])

    def test_no_ages_requires_dict(self):
        with self.assertRaises(TypeError):
            MigrationData.from_rates([{(1, 2): 0.01}])


class TestMigrationDataFileIO(unittest.TestCase):

    def test_write_and_read_simple(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "test.bin")
            data.to_migration_file(binpath, migration_type=MigrationType.LOCAL)

            self.assertTrue(os.path.exists(binpath))
            self.assertTrue(os.path.exists(binpath + ".json"))

            loaded = MigrationData.from_migration_file(binpath)
            self.assertEqual(loaded.idref, data.idref)
            self.assertEqual(loaded.gender_data_type, data.gender_data_type)

            orig_layer = data.get_layer()
            loaded_layer = loaded.get_layer()
            for key in orig_layer:
                self.assertAlmostEqual(loaded_layer.get(key, 0), orig_layer[key], places=10)

    def test_write_and_read_gender(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.5)

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "test_gender.bin")
            data.to_migration_file(binpath, migration_type=MigrationType.REGIONAL)

            loaded = MigrationData.from_migration_file(binpath)
            self.assertEqual(loaded.gender_data_type, ONE_FOR_EACH_GENDER)

            for gender in [MALE, FEMALE]:
                orig = data.get_layer(gender=gender)
                read = loaded.get_layer(gender=gender)
                for key in orig:
                    self.assertAlmostEqual(read.get(key, 0), orig[key], places=10)

    def test_write_and_read_age_gender(self):
        demog = _make_demographics(3)
        base = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.7)
        modified = base.apply_modifier(ages=[0, 15, 65], modifier_fn=lambda r, a, g: r * (0.5 if a < 15 else 1.0))

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "test_age_gender.bin")
            modified.to_migration_file(binpath, migration_type=MigrationType.AIR)

            loaded = MigrationData.from_migration_file(binpath)
            self.assertEqual(loaded.gender_data_type, ONE_FOR_EACH_GENDER)
            self.assertEqual(loaded.ages, [0, 15, 65])
            self.assertEqual(loaded.num_layers, 6)  # 2 genders × 3 ages


class TestAddMigration(unittest.TestCase):

    def test_add_migration_basic(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "local_migration.bin")
            demog.add_migration(data, MigrationType.LOCAL, filename=binpath)

            self.assertTrue(os.path.exists(binpath))
            self.assertTrue(os.path.exists(binpath + ".json"))
            self.assertEqual(len(demog.migration_files), 1)
            self.assertEqual(len(demog.implicits), 1)

    def test_add_migration_idref_mismatch_updates(self):
        demog = _make_demographics(3)
        nodes2 = [Node(lat=0, lon=0, pop=1000, forced_id=1),
                  Node(lat=1, lon=1, pop=2000, forced_id=2)]
        demog2 = Demographics(nodes=nodes2, idref="other_ref")
        data = MigrationData.from_gravity_model(demog2, [1e-4, 1, 1, -1])

        self.assertNotEqual(data.idref, demog.idref)

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "local_migration.bin")
            demog.add_migration(data, "LOCAL", filename=binpath)
            self.assertEqual(data.idref, demog.idref)

    def test_add_migration_unknown_nodes(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        # manually add a fake node
        data._layers[0][(999, 1)] = 0.5

        with self.assertRaises(ValueError):
            demog.add_migration(data, "LOCAL")

    def test_add_migration_bad_type(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])
        with self.assertRaises(ValueError):
            demog.add_migration(data, "INVALID")

    def test_add_migration_implicit_config_single_round_trips(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "local_migration.bin")
            demog.add_migration(data, MigrationType.LOCAL, x_modifier=2.5,
                                interpolation_type=InterpolationType.LINEAR_INTERPOLATION,
                                migration_pattern=MigrationPattern.SINGLE_ROUND_TRIPS,
                                roundtrip_duration=3.0, roundtrip_probability=0.9,
                                filename=binpath)

            # Simulate config application
            class Params:
                pass
            class Config:
                def __init__(self):
                    self.parameters = Params()
            config = Config()
            for fn in demog.implicits:
                config = fn(config)

            self.assertEqual(config.parameters.Migration_Model, "FIXED_RATE_MIGRATION")
            self.assertEqual(config.parameters.Enable_Local_Migration, 1)
            self.assertEqual(config.parameters.x_Local_Migration, 2.5)
            self.assertEqual(config.parameters.Migration_Pattern, "SINGLE_ROUND_TRIPS")
            self.assertEqual(config.parameters.Local_Migration_Roundtrip_Duration, 3.0)
            self.assertEqual(config.parameters.Local_Migration_Roundtrip_Probability, 0.9)

    def test_add_migration_implicit_config_waypoints_home(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            binpath = os.path.join(tmpdir, "regional_migration.bin")
            demog.add_migration(data, MigrationType.REGIONAL,
                                migration_pattern=MigrationPattern.WAYPOINTS_HOME,
                                roundtrip_waypoints=5,
                                filename=binpath)

            class Params:
                pass
            class Config:
                def __init__(self):
                    self.parameters = Params()
            config = Config()
            for fn in demog.implicits:
                config = fn(config)

            self.assertEqual(config.parameters.Migration_Pattern, "WAYPOINTS_HOME")
            self.assertEqual(config.parameters.Roundtrip_Waypoints, 5)
            self.assertEqual(config.parameters.Enable_Regional_Migration, 1)

    def test_add_migration_roundtrip_params_wrong_pattern(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with self.assertRaises(ValueError):
            demog.add_migration(data, MigrationType.LOCAL,
                                migration_pattern=MigrationPattern.RANDOM_WALK_DIFFUSION,
                                roundtrip_duration=3.0)

        with self.assertRaises(ValueError):
            demog.add_migration(data, MigrationType.LOCAL,
                                migration_pattern=MigrationPattern.SINGLE_ROUND_TRIPS,
                                roundtrip_waypoints=5)


class TestMigrationDataCSV(unittest.TestCase):

    def test_to_csv(self):
        import csv
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "test.csv")
            data.to_csv(csvpath)

            with open(csvpath) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertGreater(len(rows), 0)
            self.assertIn('source_node', rows[0])
            self.assertIn('destination_node', rows[0])
            self.assertIn('rate', rows[0])


    def test_from_csv_with_header(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1])

        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "test.csv")
            data.to_csv(csvpath)

            loaded = MigrationData.from_csv(csvpath, idref="test_migration")
            self.assertEqual(loaded.idref, "test_migration")
            self.assertEqual(loaded.gender_data_type, SAME_FOR_BOTH_GENDERS)

            orig_layer = data.get_layer()
            loaded_layer = loaded.get_layer()
            for key in orig_layer:
                self.assertAlmostEqual(loaded_layer[key], orig_layer[key], places=10)

    def test_from_csv_no_header_3_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "noheader.csv")
            with open(csvpath, 'w', newline='') as f:
                f.write("1,2,0.5\n")
                f.write("2,1,0.3\n")
                f.write("1,3,0.1\n")

            loaded = MigrationData.from_csv(csvpath, idref="test")
            self.assertEqual(loaded.gender_data_type, SAME_FOR_BOTH_GENDERS)
            self.assertEqual(loaded.ages, [])
            layer = loaded.get_layer()
            self.assertAlmostEqual(layer[(1, 2)], 0.5)
            self.assertAlmostEqual(layer[(2, 1)], 0.3)
            self.assertAlmostEqual(layer[(1, 3)], 0.1)

    def test_from_csv_no_header_4_columns_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "noheader4.csv")
            with open(csvpath, 'w', newline='') as f:
                f.write("1,0,2,0.5\n")

            with self.assertRaises(ValueError) as ctx:
                MigrationData.from_csv(csvpath)
            self.assertIn("header row", str(ctx.exception))

    def test_from_csv_gender(self):
        demog = _make_demographics(3)
        data = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.5)

        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "gender.csv")
            data.to_csv(csvpath)

            loaded = MigrationData.from_csv(csvpath, idref="test_migration")
            self.assertEqual(loaded.gender_data_type, ONE_FOR_EACH_GENDER)

            for gender in [MALE, FEMALE]:
                orig = data.get_layer(gender=gender)
                read = loaded.get_layer(gender=gender)
                for key in orig:
                    self.assertAlmostEqual(read[key], orig[key], places=10)

    def test_from_csv_rejects_node_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "bad.csv")
            with open(csvpath, 'w', newline='') as f:
                f.write("source_node,destination_node,rate\n")
                f.write("0,1,0.5\n")

            with self.assertRaises(ValueError) as ctx:
                MigrationData.from_csv(csvpath)
            self.assertIn("ID=0", str(ctx.exception))

    def test_from_csv_roundtrip_age_gender(self):
        demog = _make_demographics(3)
        base = MigrationData.from_gravity_model(demog, [1e-4, 1, 1, -1], female_multiplier=0.7)
        modified = base.apply_modifier(ages=[0, 15], modifier_fn=lambda r, a, g: r * (0.5 if a < 15 else 1.0))

        with tempfile.TemporaryDirectory() as tmpdir:
            csvpath = os.path.join(tmpdir, "age_gender.csv")
            modified.to_csv(csvpath)

            loaded = MigrationData.from_csv(csvpath, idref="test_migration")
            self.assertEqual(loaded.gender_data_type, ONE_FOR_EACH_GENDER)
            self.assertEqual(loaded.ages, [0, 15])
            self.assertEqual(loaded.num_layers, 4)


if __name__ == "__main__":
    unittest.main()
