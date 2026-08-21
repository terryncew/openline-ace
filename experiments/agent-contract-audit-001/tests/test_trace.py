import json
import tempfile
import unittest
from pathlib import Path

from aca001.trace import build_proposer_packet


class TraceTests(unittest.TestCase):
    def test_otlp_like_packet(self):
        fixture = {
            "resourceSpans": [{
                "scopeSpans": [{
                    "spans": [{
                        "name": "tool.execute",
                        "spanId": "abc",
                        "attributes": {"tool": "test"},
                        "events": [{"name": "result"}],
                    }]
                }]
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            packet = build_proposer_packet(path)
            self.assertEqual(packet["span_count"], 1)
            self.assertEqual(packet["proposer_authority"], "NONE")
            self.assertEqual(packet["spans"][0]["name"], "tool.execute")


if __name__ == "__main__":
    unittest.main()
