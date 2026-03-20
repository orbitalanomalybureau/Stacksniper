"""
STACKSNIPER MLB — Email Digest
Sends branded daily digest emails with accuracy data, top plays, and AI slate preview.
"""
import os
import requests
from datetime import date
from sports.mlb.utils.logger import get_logger

log = get_logger("EmailDigest")


class EmailDigest:
    def __init__(self):
        self.api_key = os.getenv("EMAIL_API_KEY", "")
        self.from_email = os.getenv("EMAIL_FROM", "noreply@stacksniper.com")
        self.provider = os.getenv("EMAIL_PROVIDER", "resend")  # resend or sendgrid

    def send_morning_digest(self, subscribers):
        """
        Send daily digest: yesterday's accuracy + today's top plays + AI slate preview.
        Returns dict with sent count and any errors.
        """
        from sports.mlb.utils.accuracy import accuracy_tracker

        # Gather data
        accuracy = accuracy_tracker.get_accuracy_summary(days=7)

        # Get top projected plays from the latest simulation store
        top_plays = self._get_top_plays()

        # Generate AI slate preview text
        preview = self._generate_slate_preview(accuracy, top_plays)

        # Build email
        subject = f"STACKSNIPER Daily Brief — {date.today().strftime('%b %d, %Y')}"
        html = self._build_html_email(accuracy, top_plays, preview)

        sent = 0
        errors = []
        for subscriber in subscribers:
            email_addr = subscriber if isinstance(subscriber, str) else subscriber.get("email", "")
            if not email_addr:
                continue
            try:
                # Build personalized unsubscribe link
                unsub_html = html.replace(
                    "{{UNSUBSCRIBE_URL}}",
                    f"https://stacksniper.com/unsubscribe?email={email_addr}",
                )
                if self.provider == "resend":
                    self._send_resend(email_addr, subject, unsub_html)
                elif self.provider == "sendgrid":
                    self._send_sendgrid(email_addr, subject, unsub_html)
                else:
                    log.warning(f"Unknown email provider: {self.provider}")
                    errors.append({"email": email_addr, "error": f"Unknown provider: {self.provider}"})
                    continue
                sent += 1
            except Exception as e:
                log.error(f"Failed to send digest to {email_addr}: {e}")
                errors.append({"email": email_addr, "error": str(e)})

        log.info(f"Digest sent to {sent}/{len(subscribers)} subscribers")
        return {"sent": sent, "total": len(subscribers), "errors": errors}

    def _get_top_plays(self, limit=5):
        """
        Get the top projected plays from the most recent simulation.
        Falls back to empty list if no sim data available.
        """
        try:
            from sports.mlb.utils.sim_store import sim_store
            latest = sim_store.get_latest()
            if not latest or not latest.get("projections"):
                return []

            projections = latest["projections"]
            # Sort by projected DK points descending
            sorted_projs = sorted(projections, key=lambda p: p.get("dk_points", 0), reverse=True)
            top = []
            for p in sorted_projs[:limit]:
                top.append({
                    "name": p.get("name", "Unknown"),
                    "team": p.get("team", ""),
                    "position": p.get("position", ""),
                    "dk_points": round(p.get("dk_points", 0), 1),
                    "salary": p.get("salary", 0),
                    "value": round(p.get("value", 0), 1),
                    "opponent": p.get("opponent", ""),
                })
            return top
        except Exception as e:
            log.warning(f"Could not load top plays: {e}")
            return []

    def _generate_slate_preview(self, accuracy, top_plays):
        """Generate a one-paragraph AI slate preview based on available data."""
        try:
            from sports.mlb.utils.llm_service import llm_service
            prompt = (
                f"Write a 2-3 sentence MLB DFS slate preview for today. "
                f"Our model MAE is {accuracy.get('mae', 'N/A')} DKFP over the last week. "
            )
            if top_plays:
                names = ", ".join(p["name"] for p in top_plays[:3])
                prompt += f"Top projected plays are: {names}. "
            prompt += "Be concise, confident, and focus on actionable insight. No disclaimers."

            response = llm_service.generate(prompt, max_tokens=200)
            if response and isinstance(response, str):
                return response.strip()
        except Exception as e:
            log.warning(f"LLM preview generation failed: {e}")

        # Fallback: static preview
        if top_plays:
            top_name = top_plays[0]["name"]
            return (
                f"Today's slate features {top_name} as our top projected play. "
                f"Our model has been tracking at {accuracy.get('mae', 'N/A')} MAE "
                f"over the past week with {accuracy.get('total_records', 0)} tracked projections. "
                f"Lock in your lineups early."
            )
        return (
            "A new MLB slate is on deck. Check the dashboard for the latest projections "
            "and build your optimized lineups."
        )

    def _build_html_email(self, accuracy, top_plays, preview):
        """Build branded HTML email template with dark theme matching STACKSNIPER design."""
        mae = accuracy.get("mae", "N/A")
        r_squared = accuracy.get("r_squared", "N/A")
        calibration = accuracy.get("calibration_score", "N/A")
        total_records = accuracy.get("total_records", 0)

        # Build top plays rows
        plays_html = ""
        for i, p in enumerate(top_plays):
            sal = f"${p['salary']:,}" if p.get("salary") else "--"
            plays_html += f"""
            <tr style="border-bottom: 1px solid #222233;">
                <td style="padding: 10px 12px; color: #00f0ff; font-weight: 600;">{i + 1}</td>
                <td style="padding: 10px 12px; color: #ffffff;">{p['name']}</td>
                <td style="padding: 10px 12px; color: #888;">{p['position']}</td>
                <td style="padding: 10px 12px; color: #888;">{p['team']} vs {p.get('opponent', '')}</td>
                <td style="padding: 10px 12px; color: #00ff88; font-weight: 600;">{p['dk_points']}</td>
                <td style="padding: 10px 12px; color: #aaa;">{sal}</td>
            </tr>"""

        if not plays_html:
            plays_html = """
            <tr>
                <td colspan="6" style="padding: 20px; text-align: center; color: #666;">
                    No projections available yet. Run today's simulation on the dashboard.
                </td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; background-color: #0a0e17; font-family: 'Helvetica Neue', Arial, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #0a0e17;">
<tr><td align="center" style="padding: 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%;">

    <!-- Header -->
    <tr><td style="padding: 30px 24px 20px; text-align: center; border-bottom: 1px solid #222233;">
        <h1 style="margin: 0; font-size: 28px; letter-spacing: 6px; color: #ffffff;">
            STACK<span style="color: #ff3333;">SNIPER</span>
        </h1>
        <p style="margin: 6px 0 0; font-size: 11px; color: #666; letter-spacing: 3px; text-transform: uppercase;">
            MLB Daily Brief &mdash; {date.today().strftime('%B %d, %Y')}
        </p>
    </td></tr>

    <!-- AI Preview -->
    <tr><td style="padding: 24px;">
        <div style="background: #131a2b; border: 1px solid #222233; border-radius: 8px; padding: 20px;">
            <h3 style="margin: 0 0 10px; font-size: 11px; color: #00f0ff; letter-spacing: 2px; text-transform: uppercase;">
                AI Slate Preview
            </h3>
            <p style="margin: 0; font-size: 14px; color: #e0e0e0; line-height: 1.6;">
                {preview}
            </p>
        </div>
    </td></tr>

    <!-- Accuracy Metrics -->
    <tr><td style="padding: 0 24px;">
        <h3 style="margin: 0 0 12px; font-size: 11px; color: #ff4444; letter-spacing: 2px; text-transform: uppercase;">
            Model Accuracy (7-Day)
        </h3>
        <table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom: 16px;">
        <tr>
            <td style="background: #131a2b; border-radius: 8px; padding: 14px; text-align: center; width: 25%;">
                <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px;">MAE</div>
                <div style="font-size: 22px; color: #00ff88; font-weight: 700;">{mae}</div>
            </td>
            <td style="background: #131a2b; border-radius: 8px; padding: 14px; text-align: center; width: 25%;">
                <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px;">R&sup2;</div>
                <div style="font-size: 22px; color: #4488ff; font-weight: 700;">{r_squared}</div>
            </td>
            <td style="background: #131a2b; border-radius: 8px; padding: 14px; text-align: center; width: 25%;">
                <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px;">Calibration</div>
                <div style="font-size: 22px; color: #aa44ff; font-weight: 700;">{calibration}%</div>
            </td>
            <td style="background: #131a2b; border-radius: 8px; padding: 14px; text-align: center; width: 25%;">
                <div style="font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px;">Tracked</div>
                <div style="font-size: 22px; color: #ffffff; font-weight: 700;">{total_records}</div>
            </td>
        </tr>
        </table>
    </td></tr>

    <!-- Top Plays -->
    <tr><td style="padding: 0 24px 24px;">
        <h3 style="margin: 0 0 12px; font-size: 11px; color: #ff4444; letter-spacing: 2px; text-transform: uppercase;">
            Top Projected Plays
        </h3>
        <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 13px;">
            <tr style="border-bottom: 1px solid #333;">
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">#</th>
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">Player</th>
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">Pos</th>
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">Matchup</th>
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">DKFP</th>
                <th style="padding: 8px 12px; color: #666; font-size: 10px; text-transform: uppercase; text-align: left;">Salary</th>
            </tr>
            {plays_html}
        </table>
    </td></tr>

    <!-- CTA -->
    <tr><td style="padding: 0 24px 30px; text-align: center;">
        <a href="https://stacksniper.com/dashboard" style="
            display: inline-block; padding: 14px 40px;
            background: linear-gradient(135deg, #ff3333, #cc0000);
            color: #ffffff; text-decoration: none; border-radius: 6px;
            font-size: 13px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
        ">Open Dashboard</a>
    </td></tr>

    <!-- Footer -->
    <tr><td style="padding: 20px 24px; border-top: 1px solid #222233; text-align: center;">
        <p style="margin: 0 0 8px; font-size: 11px; color: #444;">
            STACKSNIPER MLB &mdash; AI-Powered DFS Projections
        </p>
        <p style="margin: 0; font-size: 10px; color: #333;">
            <a href="{{{{UNSUBSCRIBE_URL}}}}" style="color: #555; text-decoration: underline;">Unsubscribe</a>
        </p>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
        return html

    def _send_resend(self, to, subject, html):
        """Send via Resend API."""
        if not self.api_key:
            log.warning("EMAIL_API_KEY not set, skipping Resend send")
            return

        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.from_email,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            log.error(f"Resend API error {resp.status_code}: {resp.text}")
            raise Exception(f"Resend API returned {resp.status_code}: {resp.text}")
        log.debug(f"Resend email sent to {to}")

    def _send_sendgrid(self, to, subject, html):
        """Send via SendGrid API."""
        if not self.api_key:
            log.warning("EMAIL_API_KEY not set, skipping SendGrid send")
            return

        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": self.from_email, "name": "STACKSNIPER MLB"},
                "subject": subject,
                "content": [{"type": "text/html", "value": html}],
            },
            timeout=15,
        )
        if resp.status_code not in (200, 201, 202):
            log.error(f"SendGrid API error {resp.status_code}: {resp.text}")
            raise Exception(f"SendGrid API returned {resp.status_code}: {resp.text}")
        log.debug(f"SendGrid email sent to {to}")


email_digest = EmailDigest()
