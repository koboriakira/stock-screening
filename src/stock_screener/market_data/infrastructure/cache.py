from __future__ import annotations

import json
import time
from pathlib import Path


class FileCache:
    """JSON ファイルベースのキャッシュ。TTL 付きでデータを保存・取得する。"""

    def __init__(self, cache_dir: Path | None = None, ttl_hours: int = 24) -> None:
        self._cache_dir = cache_dir or Path.home() / ".cache" / "stock-screener"
        self._ttl_seconds = ttl_hours * 3600

    def get(self, key: str) -> object | None:
        """キーに対応するキャッシュ値を取得する。TTL 超過時は None を返す。"""
        path = self._key_path(key)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        if time.time() - data["timestamp"] > self._ttl_seconds:
            path.unlink()
            return None
        return data["value"]

    def set(self, key: str, value: object) -> None:
        """キーに対応する値をキャッシュに保存する。"""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._key_path(key)
        data = {"timestamp": time.time(), "value": value}
        path.write_text(json.dumps(data))

    def clear(self) -> None:
        """全キャッシュファイルを削除する。"""
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink()

    def _key_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._cache_dir / f"{safe_key}.json"
