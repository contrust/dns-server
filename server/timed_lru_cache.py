from threading import RLock
from time import time


class TimedLruCacheEntry:
    def __init__(self, value, expiration_time: float):
        self.value = value
        self.expiration_time = time() + expiration_time


class TimedLruCache:
    def __init__(self, maxsize):
        self.entries = {}
        self.maxsize = maxsize
        self.lock = RLock()

    def add_item(self, key, value, ttl):
        with self.lock:
            if key not in self:
                if len(self.entries) >= self.maxsize:
                    del self.entries[next(iter(self.entries.keys()))]
                self.entries[key] = TimedLruCacheEntry(value, ttl)
            else:
                del self.entries[key]
                self.entries[key] = TimedLruCacheEntry(value, ttl)

    def get_item(self, key):
        with self.lock:
            self.update()
            entry = self.entries.get(key, None)
            return (entry.value if isinstance(entry, TimedLruCacheEntry)
                    else None)

    def update(self):
        with self.lock:
            self.entries = {k: v for k, v in self.entries.items()
                            if v.expiration_time > time()}

    def __contains__(self, item):
        with self.lock:
            self.update()
            return item in self.entries
