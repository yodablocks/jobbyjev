"""Minimal Jev HTTP client: one request per (candidate, company) pair, cached.

Why not batch companies into one state: jev-orderby-bench measured the same
rows through a 40-rows-per-state layout and the ranking gate failed
(inversion 0.171 vs 0.15) while one row per request passed. Ranking is the
whole point here, so every company gets its own request. Jev evaluates all
questions for one state in parallel, so the six questions per pair still
cost one round trip.

API contract (docs.typesafe.ai/api, read 2026-09-19):
  POST https://api.typesafe.ai/v1/systemone
  Authorization: Bearer <key>
  {"state": ..., "model": "jev-latest", "questions": {id: {...}}}
  -> {"model", "answers": {id: {...}}, "usage": {input_tokens, output_tokens}}
Pricing: $0.042 per million input tokens, output free (docs.typesafe.ai/models).
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000
KEY_VARS = ("TYPESAFE_API_KEY", "TYPESAFE_AI_API_KEY")
HERE = Path(__file__).resolve().parent


class NoAPIKey(RuntimeError):
    pass


def _load_dotenv() -> None:
    env = HERE / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip().removeprefix("export ").strip(), v.strip().strip("'\""))


def api_key() -> str:
    if not any(os.environ.get(v) for v in KEY_VARS):
        _load_dotenv()
    for var in KEY_VARS:
        if os.environ.get(var):
            return os.environ[var]
    raise NoAPIKey(
        "No TypeSafe API key. Export TYPESAFE_API_KEY (or TYPESAFE_AI_API_KEY), "
        f"or put it in {HERE / '.env'}. Keys: https://console.typesafe.ai/"
    )


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    cache_hits: int = 0

    @property
    def cost_usd(self) -> float:
        return self.input_tokens * USD_PER_INPUT_TOKEN


class Cache:
    """Content-addressed SQLite cache so re-running a resume is free."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._local = threading.local()
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS responses ("
                "key TEXT PRIMARY KEY, model TEXT, response TEXT, "
                "input_tokens INTEGER, latency_ms REAL, created_at REAL)"
            )

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.path, timeout=30)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @staticmethod
    def key(model: str, state: Any, questions: dict) -> str:
        blob = json.dumps({"model": model, "state": state, "questions": questions},
                          sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> dict | None:
        row = self._conn().execute("SELECT response FROM responses WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, model: str, response: dict, latency_ms: float) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?,?)",
                (key, model, json.dumps(response, ensure_ascii=False),
                 response.get("usage", {}).get("input_tokens"), latency_ms, time.time()),
            )


class JevClient:
    def __init__(self, cache_path: Path, model: str = DEFAULT_MODEL,
                 max_retries: int = 6, timeout: float = 90.0):
        self.cache = Cache(cache_path)
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.usage = Usage()
        self._lock = threading.Lock()
        self._session = requests.Session()

    def ask(self, state: Any, questions: dict, use_cache: bool = True) -> dict:
        key = Cache.key(self.model, state, questions)
        if use_cache and (hit := self.cache.get(key)) is not None:
            with self._lock:
                self.usage.cache_hits += 1
            return hit
        response = self._post({"state": state, "model": self.model, "questions": questions}, key)
        usage = response.get("usage", {})
        with self._lock:
            self.usage.input_tokens += usage.get("input_tokens", 0)
            self.usage.output_tokens += usage.get("output_tokens", 0)
            self.usage.requests += 1
        return response

    def _post(self, body: dict, key: str) -> dict:
        headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
        last: Exception | None = None
        for attempt in range(self.max_retries):
            started = time.time()
            try:
                r = self._session.post(ENDPOINT, headers=headers, json=body, timeout=self.timeout)
            except requests.RequestException as exc:
                last = exc
                self._backoff(attempt)
                continue
            if r.status_code == 200:
                payload = r.json()
                self.cache.put(key, self.model, payload, (time.time() - started) * 1000)
                return payload
            if r.status_code in (429, 529) or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                self._backoff(attempt, r.headers.get("retry-after"))
                continue
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        raise RuntimeError(f"Failed after {self.max_retries} attempts: {last}")

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                time.sleep(min(float(retry_after), 60))
                return
            except ValueError:
                pass
        time.sleep(min(2 ** attempt, 30) * (0.5 + random.random()))
