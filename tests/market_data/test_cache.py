import time

from stock_screener.market_data.infrastructure.cache import FileCache


class TestFileCache:
    def test_set_and_get(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        cache.set("test_key", {"value": 42})
        result = cache.get("test_key")
        assert result == {"value": 42}

    def test_get_nonexistent_key(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        assert cache.get("missing") is None

    def test_ttl_expired(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=0)
        cache.set("expired", {"value": 1})
        time.sleep(0.01)
        assert cache.get("expired") is None

    def test_cache_dir_created(self, tmp_path):
        cache_dir = tmp_path / "sub" / "dir"
        cache = FileCache(cache_dir=cache_dir, ttl_hours=24)
        cache.set("key", "value")
        assert cache_dir.exists()

    def test_clear(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"
