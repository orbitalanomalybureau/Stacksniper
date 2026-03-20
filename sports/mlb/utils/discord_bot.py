"""
STACKSNIPER MLB — Discord Bot
Standalone process for Discord integration via slash commands.
Run with: python utils/discord_bot.py
Requires: pip install discord.py requests
"""

import os
import requests


class StackSniperDiscordBot:
    """Lightweight Discord bot using webhooks and slash command responses."""

    def __init__(self):
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
        self.api_base = os.getenv("API_BASE_URL", os.getenv("STACKSNIPER_API_URL", "http://localhost:5555"))

    def get_slate_summary(self):
        """Fetch today's top 5 projected plays."""
        try:
            resp = requests.get(f"{self.api_base}/api/health", timeout=5)
            if resp.status_code != 200:
                return "\u26a0\ufe0f STACKSNIPER API is not available"
            return self._format_slate_message()
        except Exception as e:
            return f"\u26a0\ufe0f Error: {str(e)}"

    def get_player_projection(self, player_name):
        """Get quick projection for a player."""
        return self._format_player_message(player_name)

    def get_top_stacks(self):
        """Get top 3 recommended stacks."""
        return self._format_stacks_message()

    def _format_slate_message(self):
        """Format slate overview as Discord embed-style text."""
        return (
            "\U0001f3af **STACKSNIPER Today's Slate**\n"
            "Run /slate after simulations complete.\n\n"
            "\U0001f517 Full analysis at stacksniper.com"
        )

    def _format_player_message(self, name):
        return (
            f"\u26be **{name}** \u2014 Run a simulation first for projections.\n\n"
            f"\U0001f517 Full analysis at stacksniper.com"
        )

    def _format_stacks_message(self):
        return (
            "\U0001f4ca **Top Stacks**\n"
            "Run /stacks after simulations complete.\n\n"
            "\U0001f517 Full analysis at stacksniper.com"
        )


# CLI entry point
if __name__ == "__main__":
    try:
        import discord
        from discord.ext import commands

        bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())
        ss = StackSniperDiscordBot()

        @bot.command(name="slate")
        async def slate(ctx):
            await ctx.send(ss.get_slate_summary())

        @bot.command(name="player")
        async def player(ctx, *, name: str):
            await ctx.send(ss.get_player_projection(name))

        @bot.command(name="stacks")
        async def stacks(ctx):
            await ctx.send(ss.get_top_stacks())

        @bot.event
        async def on_ready():
            print(f"STACKSNIPER Discord bot online as {bot.user}")

        token = os.getenv("DISCORD_BOT_TOKEN")
        if token:
            bot.run(token)
        else:
            print("Set DISCORD_BOT_TOKEN to run the bot")
    except ImportError:
        print("Install discord.py: pip install discord.py")
