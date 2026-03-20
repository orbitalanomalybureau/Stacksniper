"""
STACKSNIPER MLB — Lineup Sharing
Generates share images, shareable URLs, and Open Graph meta tags for social sharing.
"""
import hashlib
from datetime import datetime
from pathlib import Path
from sports.mlb.utils.logger import get_logger

log = get_logger("Share")

SHARES_DIR = Path(__file__).parent.parent / "data" / "shares"


class LineupSharer:
    def __init__(self):
        SHARES_DIR.mkdir(parents=True, exist_ok=True)

    def generate_share_image(self, lineup_data):
        """
        Generate a styled PNG image of a lineup using Pillow.
        Returns the file path to the generated image, or None if Pillow is not installed.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            log.warning("Pillow not installed — share image generation unavailable")
            return None

        WIDTH, HEIGHT = 600, 800
        BG_COLOR = (10, 14, 23)         # #0a0e17
        CARD_BG = (19, 26, 43)          # #131a2b
        BORDER_COLOR = (34, 34, 51)     # #222233
        ACCENT = (255, 51, 51)          # #ff3333
        CYAN = (0, 240, 255)            # #00f0ff
        GREEN = (0, 255, 136)           # #00ff88
        WHITE = (255, 255, 255)
        MUTED = (136, 136, 136)
        DARK_TEXT = (102, 102, 102)

        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Try to load a font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 22)
            font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 11)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 28)
        except (OSError, IOError):
            try:
                font_large = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
                font_med = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
                font_small = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
                font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 28)
            except (OSError, IOError):
                font_large = ImageFont.load_default()
                font_med = ImageFont.load_default()
                font_small = ImageFont.load_default()
                font_title = ImageFont.load_default()

        # ── Header: STACKSNIPER branding ──
        draw.rectangle([(0, 0), (WIDTH, 80)], fill=CARD_BG)
        draw.line([(0, 80), (WIDTH, 80)], fill=BORDER_COLOR, width=1)

        # Title
        draw.text((24, 20), "STACK", fill=WHITE, font=font_title)
        title_w = draw.textlength("STACK", font=font_title)
        draw.text((24 + title_w, 20), "SNIPER", fill=ACCENT, font=font_title)

        # Subtitle
        draw.text((24, 54), "MLB OPTIMIZED LINEUP", fill=MUTED, font=font_small)

        # Date
        date_str = lineup_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        date_text = f"{date_str}"
        date_w = draw.textlength(date_text, font=font_small)
        draw.text((WIDTH - 24 - date_w, 54), date_text, fill=DARK_TEXT, font=font_small)

        # ── Player rows ──
        players = lineup_data.get("players", [])
        y_start = 100
        row_height = 60
        col_pos_x = 24
        col_name_x = 70
        col_team_x = 300
        col_salary_x = 380
        col_proj_x = 490

        # Column headers
        header_y = y_start
        draw.text((col_pos_x, header_y), "POS", fill=DARK_TEXT, font=font_small)
        draw.text((col_name_x, header_y), "PLAYER", fill=DARK_TEXT, font=font_small)
        draw.text((col_team_x, header_y), "TEAM", fill=DARK_TEXT, font=font_small)
        draw.text((col_salary_x, header_y), "SALARY", fill=DARK_TEXT, font=font_small)
        draw.text((col_proj_x, header_y), "PROJ", fill=DARK_TEXT, font=font_small)

        draw.line([(24, header_y + 18), (WIDTH - 24, header_y + 18)], fill=BORDER_COLOR, width=1)

        total_salary = 0
        total_proj = 0.0

        for i, player in enumerate(players[:10]):  # max 10 players
            y = y_start + 28 + i * row_height

            # Alternate row background
            if i % 2 == 1:
                draw.rectangle([(12, y - 6), (WIDTH - 12, y + row_height - 14)], fill=(13, 13, 26))

            pos = player.get("position", "")
            name = player.get("name", "Unknown")
            team = player.get("team", "")
            salary = player.get("salary", 0)
            proj = player.get("projection", 0.0)

            total_salary += salary
            total_proj += proj

            # Position badge
            is_pitcher = pos in ("SP", "RP", "P")
            pos_color = (170, 68, 255) if is_pitcher else CYAN
            draw.text((col_pos_x, y + 4), pos, fill=pos_color, font=font_med)

            # Player name
            display_name = name[:25] if len(name) > 25 else name
            draw.text((col_name_x, y + 4), display_name, fill=WHITE, font=font_med)

            # Team
            draw.text((col_team_x, y + 4), team, fill=MUTED, font=font_med)

            # Salary
            salary_str = f"${salary:,}" if salary else "--"
            draw.text((col_salary_x, y + 4), salary_str, fill=MUTED, font=font_med)

            # Projection
            proj_str = f"{proj:.1f}"
            draw.text((col_proj_x, y + 4), proj_str, fill=GREEN, font=font_med)

        # ── Footer: totals ──
        footer_y = y_start + 28 + min(len(players), 10) * row_height + 10
        draw.line([(24, footer_y), (WIDTH - 24, footer_y)], fill=BORDER_COLOR, width=1)

        footer_text_y = footer_y + 12
        draw.text((col_pos_x, footer_text_y), "TOTAL", fill=ACCENT, font=font_med)
        draw.text((col_salary_x, footer_text_y), f"${total_salary:,}", fill=WHITE, font=font_med)
        draw.text((col_proj_x, footer_text_y), f"{total_proj:.1f}", fill=GREEN, font=font_large)

        # Remaining salary
        remaining = 50000 - total_salary
        remaining_text = f"Remaining: ${remaining:,}"
        draw.text((col_name_x, footer_text_y + 4), remaining_text, fill=DARK_TEXT, font=font_small)

        # ── Branding footer bar ──
        bar_y = HEIGHT - 50
        draw.rectangle([(0, bar_y), (WIDTH, HEIGHT)], fill=CARD_BG)
        draw.line([(0, bar_y), (WIDTH, bar_y)], fill=BORDER_COLOR, width=1)
        draw.text((24, bar_y + 16), "stacksniper.com", fill=MUTED, font=font_small)
        draw.text((WIDTH - 24 - draw.textlength("AI-POWERED DFS", font=font_small), bar_y + 16),
                  "AI-POWERED DFS", fill=DARK_TEXT, font=font_small)

        # Save
        lineup_id = lineup_data.get("id", hashlib.md5(str(lineup_data).encode()).hexdigest()[:8])
        filename = f"lineup_{lineup_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = SHARES_DIR / filename

        img.save(str(filepath), "PNG", quality=95)
        log.info(f"Share image generated: {filepath}")
        return str(filepath)

    def generate_share_url(self, lineup_id):
        """Generate a shareable URL for a lineup."""
        share_hash = hashlib.md5(
            f"{lineup_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        return f"/share/{share_hash}"

    def get_og_meta(self, lineup_data):
        """Generate Open Graph meta tags for rich social sharing."""
        players = lineup_data.get("players", [])
        total = sum(p.get("projection", 0) for p in players)
        lineup_id = lineup_data.get("id", "")

        # Build a short description with top players
        top_names = [p.get("name", "") for p in sorted(
            players, key=lambda p: p.get("projection", 0), reverse=True
        )[:3]]
        top_str = ", ".join(n for n in top_names if n)

        description = f"{len(players)} players optimized by AI"
        if top_str:
            description += f" | Top plays: {top_str}"

        return {
            "title": f"STACKSNIPER Lineup \u2014 {total:.1f} projected pts",
            "description": description,
            "image": f"/api/lineup/share/{lineup_id}/image",
            "url": f"/share/{lineup_id}",
            "type": "website",
            "site_name": "STACKSNIPER MLB",
        }

    def get_share_html(self, lineup_data):
        """
        Generate a self-contained HTML page for a shared lineup with OG tags.
        Used when someone visits a /share/<hash> URL.
        """
        meta = self.get_og_meta(lineup_data)
        players = lineup_data.get("players", [])
        total_proj = sum(p.get("projection", 0) for p in players)
        total_salary = sum(p.get("salary", 0) for p in players)

        rows = ""
        for p in players:
            pos = p.get("position", "")
            name = p.get("name", "Unknown")
            team = p.get("team", "")
            sal = f"${p.get('salary', 0):,}"
            proj = f"{p.get('projection', 0):.1f}"
            rows += f"<tr><td>{pos}</td><td>{name}</td><td>{team}</td><td>{sal}</td><td>{proj}</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{meta['title']}</title>
<meta property="og:title" content="{meta['title']}">
<meta property="og:description" content="{meta['description']}">
<meta property="og:image" content="{meta['image']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="STACKSNIPER MLB">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{meta['title']}">
<meta name="twitter:description" content="{meta['description']}">
<style>
body {{ margin:0; background:#0a0e17; color:#e0e0e0; font-family:sans-serif; padding:20px; }}
.card {{ max-width:600px; margin:40px auto; background:#111122; border:1px solid #222233; border-radius:10px; padding:24px; }}
h1 {{ font-size:24px; letter-spacing:4px; }} h1 span {{ color:#ff3333; }}
table {{ width:100%; border-collapse:collapse; margin-top:16px; font-size:13px; }}
th {{ text-align:left; padding:8px; border-bottom:1px solid #333; color:#888; font-size:10px; text-transform:uppercase; }}
td {{ padding:8px; border-bottom:1px solid #1a1a2e; }}
.total {{ margin-top:16px; font-size:18px; color:#00ff88; font-weight:700; }}
.cta {{ display:inline-block; margin-top:20px; padding:12px 30px; background:linear-gradient(135deg,#ff3333,#cc0000); color:#fff; text-decoration:none; border-radius:6px; font-weight:700; letter-spacing:2px; font-size:12px; }}
</style>
</head>
<body>
<div class="card">
<h1>STACK<span>SNIPER</span></h1>
<p style="color:#666; font-size:12px; letter-spacing:2px;">OPTIMIZED LINEUP</p>
<table><thead><tr><th>Pos</th><th>Player</th><th>Team</th><th>Salary</th><th>Proj</th></tr></thead><tbody>{rows}</tbody></table>
<div class="total">{total_proj:.1f} projected pts | ${total_salary:,} salary</div>
<a href="/" class="cta">BUILD YOUR OWN LINEUP</a>
</div>
</body>
</html>"""


lineup_sharer = LineupSharer()
