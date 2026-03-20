"""
STACKSNIPER MLB — Thread-Safe Simulation Store
"""
import threading
import time
from typing import Optional

class SimulationStore:
    """Thread-safe store for simulation results with TTL expiration."""

    def __init__(self, ttl_seconds: int = 1800):
        self._store = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds

    def save(self, sim_id: int, result) -> None:
        with self._lock:
            self._store[sim_id] = {
                "result": result,
                "created_at": time.time(),
            }
            self._cleanup()

    def get(self, sim_id: int) -> Optional[object]:
        with self._lock:
            entry = self._store.get(sim_id)
            if not entry:
                return None
            if time.time() - entry["created_at"] > self._ttl:
                del self._store[sim_id]
                return None
            return entry["result"]

    def get_latest(self) -> Optional[object]:
        with self._lock:
            if not self._store:
                return None
            latest_id = max(self._store.keys())
            return self.get(latest_id)

    def list_ids(self) -> list:
        with self._lock:
            self._cleanup()
            return list(self._store.keys())

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v["created_at"] > self._ttl]
        for k in expired:
            del self._store[k]

sim_store = SimulationStore()
