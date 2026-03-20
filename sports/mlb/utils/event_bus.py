"""
STACKSNIPER MLB — Event Bus for Live Data Changes
Publishes events when lineup changes, odds movements, weather updates, or injuries are detected.
"""
import time
import threading
from typing import Dict, List, Callable
from sports.mlb.utils.logger import get_logger

log = get_logger("EventBus")


class EventBus:
    """Thread-safe pub/sub event bus for real-time data change notifications."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._poll_thread = None
        self._recent_events: List[dict] = []
        self._max_recent = 100

    def subscribe(self, event_type: str, callback: Callable):
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)
            log.info(f"Subscriber added for '{event_type}'")

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type] if cb != callback
                ]

    def publish(self, event_type: str, data: dict):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        with self._lock:
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_recent:
                self._recent_events = self._recent_events[-self._max_recent:]
            callbacks = list(self._subscribers.get(event_type, []))

        for cb in callbacks:
            try:
                cb(event)
            except Exception as e:
                log.error(f"Event callback error ({event_type}): {e}")

    def get_recent_events(self, since_timestamp: float = 0, event_type: str = None) -> list:
        with self._lock:
            events = [
                e for e in self._recent_events
                if e["timestamp"] > since_timestamp
                and (event_type is None or e["type"] == event_type)
            ]
        return events

    def start_polling(self, interval_seconds: int = 60):
        if self._running:
            return
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, args=(interval_seconds,), daemon=True)
        self._poll_thread.start()
        log.info(f"Event bus polling started (interval={interval_seconds}s)")

    def stop_polling(self):
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
            self._poll_thread = None

    def _poll_loop(self, interval: int):
        """Background polling loop for data changes."""
        from sports.mlb.data.mlb_api import mlb_api
        last_lineups = {}
        last_odds = {}

        while self._running:
            try:
                self._check_lineup_changes(mlb_api, last_lineups)
                self._check_odds_movements(last_odds)
            except Exception as e:
                log.error(f"Poll error: {e}")
            time.sleep(interval)

    def _check_lineup_changes(self, mlb_api, last_lineups: dict):
        """Check for lineup changes (SP scratches, lineup card updates)."""
        from datetime import date
        try:
            games = mlb_api.get_schedule(date.today())
            for game in games:
                game_pk = game.get("game_pk")
                if not game_pk:
                    continue
                away_sp = game.get("away_team", {}).get("probable_pitcher", {}).get("name", "")
                home_sp = game.get("home_team", {}).get("probable_pitcher", {}).get("name", "")
                current = f"{away_sp}|{home_sp}"
                prev = last_lineups.get(game_pk)
                if prev and prev != current:
                    self.publish("lineup_change", {
                        "game_pk": game_pk,
                        "type": "pitcher_change",
                        "previous": prev,
                        "current": current,
                        "game": f"{game.get('away_team', {}).get('abbr', '?')} @ {game.get('home_team', {}).get('abbr', '?')}",
                    })
                last_lineups[game_pk] = current
        except Exception as e:
            log.error(f"Lineup check error: {e}")

    def _check_odds_movements(self, last_odds: dict):
        """Check for significant odds movements."""
        # Placeholder — requires external odds data source
        pass


# Module singleton
event_bus = EventBus()
