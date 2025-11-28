import os
import unittest
from src.ingest import Ingestor

class TestIngestor(unittest.TestCase):
    def test_is_text_file(self):
        ingestor = Ingestor()
        self.assertTrue(ingestor._is_text_file("test.py"))
        self.assertTrue(ingestor._is_text_file("README.md"))
        self.assertFalse(ingestor._is_text_file("image.png"))
        self.assertFalse(ingestor._is_text_file("binary.exe"))
        ingestor.cleanup()

if __name__ == '__main__':
    unittest.main()
