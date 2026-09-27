"""Offline verifier integrity controls; temporary inputs are created by this test."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

import verify_public as verifier


class PublicIntegrity(unittest.TestCase):
    def test_manifest_resource_bounds_before_file_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = {"path": "absent", "sha256": "0" * 64, "bytes": 32 * 2**20}
            for rows in ([row] * 16001, [{**row, "bytes": 32 * 2**20 + 1}], [row] * 6):
                with self.assertRaisesRegex(ValueError, "bound"):
                    verifier.verify_files(root, rows)

    def test_git_objects_and_registered_modes(self):
        self.assertEqual(verifier.git_object("blob", b"test\n").hex(), "9daeafb9864cf43055ae93beb0afd6c7d144bfa4")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(verifier.source_tree(root, {}), "4b825dc642cb6eb9a060e54bf8d69288fbee4904")
            (root / "a").write_bytes(b"test\n")
            expected = verifier.git_object("tree", b"100644 a\0" + verifier.git_object("blob", b"test\n")).hex()
            self.assertEqual(verifier.source_tree(root, {"a": 0o100644}), expected)
            self.assertNotEqual(verifier.source_tree(root, {"a": 0o100755}), expected)
            for mode in (True, 0o120000, "100644"):
                with self.assertRaisesRegex(ValueError, "mode"):
                    verifier.source_tree(root, {"a": mode})

    def test_raw_input_source_byte_changes_and_extra_files(self):
        for name in ("raw.jsonl", "input.brs", "source.py"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / name
                data = b"original\n"
                path.write_bytes(data)
                row = {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                self.assertEqual(verifier.verify_files(root, [row]), 1)
                path.write_bytes(b"Original\n")
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    verifier.verify_files(root, [row])
                path.write_bytes(data)
                (root / "extra").write_bytes(b"x")
                with self.assertRaisesRegex(ValueError, "unregistered"):
                    verifier.verify_files(root, [row])

    def test_unsafe_duplicate_and_case_colliding_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("../x", "/absolute", "C:/drive", "a\\b", "a/../b", "a//b", "a.", "a ", "a/./b"):
                with self.assertRaises(ValueError, msg=name):
                    verifier.member(root, name)
            p = root / "one"
            p.write_bytes(b"x")
            row = {"path": "one", "sha256": hashlib.sha256(b"x").hexdigest(), "bytes": 1}
            for repeated in (row, {**row, "path": "ONE"}):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    verifier.verify_files(root, [row, repeated])
            with self.assertRaisesRegex(ValueError, "identity type"):
                verifier.verify_files(root, [{**row, "bytes": True}])

    def test_untrusted_manifest_stops_before_any_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SOURCE-MANIFEST.json").write_bytes(b"{}")
            before = {n: sys.modules.get(n) for n in verifier.MODULES}
            with self.assertRaisesRegex(ValueError, "untrusted baseline manifest"):
                verifier.verify(root, root)
            self.assertEqual(before, {n: sys.modules.get(n) for n in verifier.MODULES})

    def test_preloaded_module_and_unreviewed_import_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertNotIn("gates", sys.modules)
            sentinel = object()
            sys.modules["gates"] = sentinel
            try:
                with self.assertRaisesRegex(ValueError, "preloaded"):
                    verifier.import_baseline(root)
                self.assertIs(sys.modules["gates"], sentinel)
            finally:
                del sys.modules["gates"]
            source = root / "scripts/corpus.py"
            source.parent.mkdir()
            source.write_text("raise RuntimeError('unreviewed module was executed')\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unreviewed"):
                verifier.import_baseline(root)

    def test_run_cardinality_identity_and_consumption(self):
        row = {"build": "cand", "op": "PARSE", "case": "test", "budget": 0, "tag": "rep0",
               "report": {"pid": 1, "creation_filetime": 100}}
        with self.assertRaisesRegex(ValueError, "duplicate native"):
            verifier.Replay([row, row])
        with self.assertRaisesRegex(ValueError, "budget type"):
            verifier.Replay([{**row, "budget": False}])
        replay = verifier.Replay([row])
        self.assertIs(replay.run("cand", "PARSE", "test", 0, "rep0"), row)
        with self.assertRaisesRegex(ValueError, "missing registered"):
            replay.run("cand", "PARSE", "test", 0, "rep0")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            replay.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
