# server/timed_lru_cache.py
from threading import RLock
from time import time
import pickle

class TimedLruCacheEntry:
    def __init__(self, value, expiration_time: float):
        self.value = value
        self.expiration_time = time() + expiration_time

    def to_dict(self):
        return {
            'value': self.value,
            'expiration_time': self.expiration_time
        }

    @classmethod
    def from_dict(cls, data):
        entry = cls(data['value'], data['expiration_time'] - time())
        entry.expiration_time = data['expiration_time']  # Keep original expiration
        return entry

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

    def save_to_file(self, filename):
        with self.lock:
            with open(filename, 'wb') as f:
                pickle.dump({'entries': self.entries,
                             'maxsize': self.maxsize}, f)

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        cache = TimedLruCache(data['maxsize'])
        cache.entries = data['entries']
        return cache

    @classmethod
    def try_load_from_file(cls, filename, maxsize):
        try:
            cache = cls.load_from_file(filename)
            cache.maxsize = maxsize
            return cache
        except Exception as e:
            print(e)
        print("Ignoring cache file")
        print(f"Initializing cache with {maxsize} size")
        return cls(maxsize)
