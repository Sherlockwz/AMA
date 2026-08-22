import json
import sys
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from server import _parse_forward_user_output, health  # noqa: E402


class SidecarUtilityTests(unittest.TestCase):
    def test_health_payload(self):
        self.assertEqual(health(), {"status": "ok"})

    def test_forward_user_payload_parser(self):
        retrievals = [{"content": "remembered fact"}]
        memory_window = [{"speaker": "user", "text": "hello"}]
        raw = (
            "Retrieval results:\n"
            + json.dumps(retrievals)
            + "\nMemory Window:\n"
            + json.dumps(memory_window)
        )
        self.assertEqual(
            _parse_forward_user_output(raw),
            {"retrievals": retrievals, "memoryWindow": memory_window},
        )


if __name__ == "__main__":
    unittest.main()
