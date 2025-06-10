import unittest
import time
import os
import tempfile
from server.timed_lru_cache import TimedLruCache

class TestTimedLruCache(unittest.TestCase):
    def setUp(self):
        self.cache = TimedLruCache(maxsize=3)

    def test_add_and_get_item(self):
        self.cache.add_item("key1", "value1", ttl=1.0)
        self.assertEqual(self.cache.get_item("key1"), "value1")
        self.assertIn("key1", self.cache)

    def test_ttl_expiration(self):
        self.cache.add_item("key1", "value1", ttl=0.1)
        time.sleep(0.2)
        self.assertIsNone(self.cache.get_item("key1"))
        self.assertNotIn("key1", self.cache)

    def test_lru_eviction(self):
        self.cache.add_item("key1", "value1", ttl=1.0)
        self.cache.add_item("key2", "value2", ttl=1.0)
        self.cache.add_item("key3", "value3", ttl=1.0)
        self.cache.add_item("key4", "value4", ttl=1.0)
        
        self.assertNotIn("key1", self.cache)
        self.assertIn("key2", self.cache)
        self.assertIn("key3", self.cache)
        self.assertIn("key4", self.cache)

    def test_update_existing_item(self):
        self.cache.add_item("key1", "value1", ttl=1.0)
        self.cache.add_item("key1", "value2", ttl=1.0)
        self.assertEqual(self.cache.get_item("key1"), "value2")

    def test_file_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            filename = tmp.name

        try:
            self.cache.add_item("key1", "value1", ttl=1.0)
            self.cache.add_item("key2", "value2", ttl=1.0)
            self.cache.save_to_file(filename)

            new_cache = TimedLruCache.load_from_file(filename)
            self.assertEqual(new_cache.get_item("key1"), "value1")
            self.assertEqual(new_cache.get_item("key2"), "value2")
            self.assertEqual(new_cache.maxsize, self.cache.maxsize)

        finally:
            os.unlink(filename)

    def test_try_load_from_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            filename = tmp.name

        try:
            cache = TimedLruCache.try_load_from_file(filename, maxsize=5)
            self.assertEqual(cache.maxsize, 5)
            self.assertEqual(len(cache.entries), 0)

        finally:
            os.unlink(filename)

    def test_thread_safety(self):
        import threading
        
        def add_items():
            for i in range(100):
                self.cache.add_item(f"key{i}", f"value{i}", ttl=1.0)

        threads = [threading.Thread(target=add_items) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertLessEqual(len(self.cache.entries), self.cache.maxsize)

    def test_edge_cases(self):
        self.assertIsNone(self.cache.get_item("nonexistent"))
        self.assertNotIn("nonexistent", self.cache)

        self.cache.add_item("key1", "value1", ttl=0)
        self.assertIsNone(self.cache.get_item("key1"))

        self.cache.add_item("key2", "value2", ttl=-1)
        self.assertIsNone(self.cache.get_item("key2"))

if __name__ == '__main__':
    unittest.main() 