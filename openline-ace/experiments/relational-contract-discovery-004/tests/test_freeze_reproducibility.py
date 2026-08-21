import gzip
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
SOURCE_003 = EXPERIMENT.parent / "relational-contract-discovery-003"
sys.path.insert(0, str(SOURCE_003))
SPEC = importlib.util.spec_from_file_location(
    "rcdl004_freeze_corpus", EXPERIMENT / "scripts" / "freeze_corpus.py"
)
assert SPEC is not None and SPEC.loader is not None
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest_payload(manifest: dict, compressed: bytes) -> bytes:
    bound = dict(manifest)
    bound["compressed_sha256"] = _sha256(compressed)
    return FREEZE.canonical_json(bound) + b"\n"


class FrozenCorpusReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = b'{"schema":"example/0.1","value":1}\n'
        self.generated = gzip.compress(self.payload, compresslevel=9, mtime=0)
        self.manifest = {
            "schema": "test.frozen-corpus/0.1",
            "compressed_sha256": _sha256(self.generated),
            "payload_sha256": _sha256(self.payload),
        }

    def test_equivalent_gzip_container_is_accepted_and_bound(self) -> None:
        alternate_bytes = gzip.compress(self.payload, compresslevel=1, mtime=0)
        self.assertNotEqual(_sha256(alternate_bytes), _sha256(self.generated))
        self.assertEqual(gzip.decompress(alternate_bytes), self.payload)

        FREEZE._verify_frozen_artifacts(
            self.generated,
            self.manifest,
            alternate_bytes,
            _manifest_payload(self.manifest, alternate_bytes),
        )

    def test_changed_payload_is_rejected(self) -> None:
        changed = gzip.compress(self.payload + b"{}\n", compresslevel=9, mtime=0)
        with self.assertRaisesRegex(SystemExit, "payload differs"):
            FREEZE._verify_frozen_artifacts(
                self.generated,
                self.manifest,
                changed,
                _manifest_payload(self.manifest, changed),
            )

    def test_stale_container_digest_is_rejected(self) -> None:
        alternate = gzip.compress(self.payload, compresslevel=1, mtime=0)
        with self.assertRaisesRegex(SystemExit, "manifest differs"):
            FREEZE._verify_frozen_artifacts(
                self.generated,
                self.manifest,
                alternate,
                _manifest_payload(self.manifest, self.generated),
            )


if __name__ == "__main__":
    unittest.main()
