import sys
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[1]
ADAPTIVE_MEMORY_DIR = PYTHON_DIR / "AdaptiveMemory"
sys.path.insert(0, str(ADAPTIVE_MEMORY_DIR))

from Core.AMA import split_sentences  # noqa: E402
from StoreFunc.SQLite.sqliteFunc import normalize_table_name  # noqa: E402


class CoreUtilityTests(unittest.TestCase):
    def test_split_sentences_supports_mixed_punctuation(self):
        self.assertEqual(
            split_sentences("Hello world! 你好世界。Still here?"),
            ["Hello world!", "你好世界。", "Still here?"],
        )

    def test_table_names_are_sanitized(self):
        self.assertEqual(normalize_table_name("alice@example.com"), "alice_example_com")
        self.assertEqual(normalize_table_name("123"), "user_123")


if __name__ == "__main__":
    unittest.main()
