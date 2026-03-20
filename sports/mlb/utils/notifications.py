"""
STACKSNIPER MLB — Webhook & Push Notifications
"""
import requests
from typing import Optional
from sports.mlb.utils.logger import get_logger

log = get_logger("Notifications")


class NotificationService:
    """Send notifications via Discord webhook and browser push."""

    def __init__(self, settings_manager=None):
        self.settings = settings_manager

    def _get_discord_url(self) -> Optional[str]:
        if self.settings:
            return self.settings.get_setting("notifications.discord_webhook_url")
        return None

    def send_discord(self, title: str, message: str, color: int = 0x00FF88,
                     fields: list = None) -> bool:
        url = self._get_discord_url()
        if not url:
            return False

        embed = {
            "title": f"⚾ {title}",
            "description": message,
            "color": color,
            "footer": {"text": "STACKSNIPER MLB v6.0"},
        }
        if fields:
            embed["fields"] = [
                {"name": f["name"], "value": f["value"], "inline": f.get("inline", True)}
                for f in fields
            ]

        payload = {"embeds": [embed]}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            log.info(f"Discord notification sent: {title}")
            return True
        except Exception as e:
            log.error(f"Discord notification failed: {e}")
            return False

    def notify_simulation_complete(self, sim_result) -> bool:
        return self.send_discord(
            "Simulation Complete",
            f"{sim_result.num_sims} sims · {len(sim_result.player_projections)} players",
            color=0x00FF88,
            fields=[
                {"name": "Games", "value": str(len(sim_result.games))},
                {"name": "Confidence", "value": f"{(sim_result.confidence_score or 0) * 100:.0f}%"},
            ],
        )

    def notify_lineup_change(self, change: dict) -> bool:
        return self.send_discord(
            "⚠️ Lineup Change Detected",
            f"{change.get('player', 'Unknown')} ({change.get('team', '')})",
            color=0xFF6600,
            fields=[
                {"name": "Type", "value": change.get("type", "scratch")},
                {"name": "Impact", "value": change.get("impact", "unknown")},
            ],
        )

    def notify_odds_movement(self, movement: dict) -> bool:
        return self.send_discord(
            "📊 Odds Movement",
            f"{movement.get('game', '')}",
            color=0x3366FF,
            fields=[
                {"name": "Old Total", "value": str(movement.get("old_total", "?"))},
                {"name": "New Total", "value": str(movement.get("new_total", "?"))},
                {"name": "Change", "value": str(movement.get("delta", "?"))},
            ],
        )


# Module singleton (lazy init)
_notification_service = None


def get_notification_service(settings_manager=None):
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(settings_manager)
    return _notification_service
