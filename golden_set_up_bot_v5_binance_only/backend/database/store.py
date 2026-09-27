import os
from datetime import datetime, timezone
from typing import Any

class Store:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.enabled = bool(self.url and self.key)
        self._local_events: list[dict[str, Any]] = []
        self._state = None

    def _headers(self):
        return {"apikey": self.key, "Authorization": f"Bearer {self.key}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"}

    def save_state(self, state):
        self._state = state
        if not self.enabled:
            return
        try:
            import requests
            requests.post(self.url + "/rest/v1/bot_state", headers=self._headers(), json={"id": 1, "state": state}, timeout=5).raise_for_status()
        except Exception:
            pass

    def load_state(self):
        if not self.enabled:
            return self._state
        try:
            import requests
            r = requests.get(self.url + "/rest/v1/bot_state?id=eq.1&select=state", headers=self._headers(), timeout=5)
            r.raise_for_status()
            rows = r.json()
            return rows[0]["state"] if rows else None
        except Exception:
            return None

    def log_event(self, event: dict[str, Any]):
        event = dict(event)
        event["logged_at"] = datetime.now(timezone.utc).isoformat()
        self._local_events.append(event)
        if not self.enabled:
            return
        try:
            import requests
            requests.post(self.url + "/rest/v1/trade_events", headers=self._headers(), json={"event": event}, timeout=5).raise_for_status()
        except Exception:
            pass

    def recent_events(self, limit=100):
        if self.enabled:
            try:
                import requests
                r = requests.get(self.url + f"/rest/v1/trade_events?select=event,created_at&order=created_at.desc&limit={limit}", headers=self._headers(), timeout=5)
                r.raise_for_status()
                return [row["event"] for row in r.json()]
            except Exception:
                pass
        return self._local_events[-limit:][::-1]
