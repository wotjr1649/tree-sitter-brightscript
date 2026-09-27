"""Exact 0.1.2 metadata and archive boundary controls; no native execution."""
import copy
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from check_maintenance import ROOT
import check_maintenance_012 as maintenance
import prepare_public_replay as package


class Maintenance012(unittest.TestCase):
    def test_exact_delta_and_rejected_mutations(self):
        old = {n: (ROOT / n).read_bytes() for n in maintenance.COMPONENTS}
        old["src/parser.c"] = old["src/parser.c"].replace(
            maintenance.METADATA_011.replace(b".patch_version = 1", b".patch_version = 2"), maintenance.METADATA_011)
        for name in maintenance.POINTERS:
            old[name] = old[name].replace(b'"0.1.2"', b'"0.1.1"')
        new = copy.deepcopy(old)
        new["src/parser.c"] = old["src/parser.c"].replace(
            maintenance.METADATA_011, maintenance.METADATA_011.replace(b".patch_version = 1", b".patch_version = 2"))
        for name in maintenance.POINTERS:
            new[name] = new[name].replace(b'"0.1.1"', b'"0.1.2"')
        self.assertEqual(len(maintenance.compare(old, new)["changed"]), 4)
        for name in maintenance.COMPONENTS:
            mutant = copy.deepcopy(new)
            mutant[name] += b" "
            with self.assertRaises(ValueError, msg=name):
                maintenance.compare(old, mutant)
        for before, after in ((b"ts_parse_table", b"tx_parse_table"), (b".major_version = 0", b".major_version = 1"),
                              (b".metadata =", b".metadata  ="), (b".patch_version = 2", b".patch_version = 3")):
            mutant = copy.deepcopy(new)
            self.assertIn(before, mutant["src/parser.c"])
            mutant["src/parser.c"] = mutant["src/parser.c"].replace(before, after, 1)
            with self.assertRaises(ValueError):
                maintenance.compare(old, mutant)
        for data in (b'{"version":"0.1.2","version":"0.1.2"}', b'{"version":1.2}', b'{"version":NaN}'):
            mutant = {**new, "package.json": data}
            with self.assertRaises(ValueError):
                maintenance.compare(old, mutant)

    def test_archive_paths_types_duplicates_and_determinism(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for n, names in enumerate((("root/../escape",), ("root/a\\b",), ("root/a.",), ("/root/a",),
                                       ("root/a", "root/A"), ("other/a",), ("root/link",))):
                archive = root / f"bad-{n}.zip"
                with zipfile.ZipFile(archive, "x") as z:
                    for name in names:
                        info = zipfile.ZipInfo(name)
                        # Windows ZipInfo normalizes backslashes at construction;
                        # retain the hostile archive spelling for this control.
                        info.filename = name
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777 if name.endswith("/link") else 0o100644) << 16
                        z.writestr(info, b"x")
                with self.assertRaises(ValueError, msg=str(names)):
                    package.unzip(archive, "root", root / f"out-{n}")
                self.assertFalse((root / f"out-{n}").exists(), "all members must be checked before any extraction")
            for name in ("a.zip", "b.zip"):
                package.deterministic_zip(root / name, [("input", b"bytes", 0o100644)], "root")
            self.assertEqual((root / "a.zip").read_bytes(), (root / "b.zip").read_bytes())
            with zipfile.ZipFile(root / "a.zip") as z:
                self.assertTrue(all(r.compress_type == zipfile.ZIP_STORED for r in z.infolist()))
            package.unzip(root / "a.zip", "root", root / "valid")
            self.assertEqual((root / "valid/input").read_bytes(), b"bytes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
