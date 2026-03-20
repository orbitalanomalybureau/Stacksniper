"""
STACKSNIPER MLB — Multi-Provider LLM Service
"""
import json
import time
from sports.mlb.utils.logger import get_logger

log = get_logger("LLM")

SYSTEM_PROMPT = """You are STACKSNIPER's AI analyst — an expert MLB DFS briefing engine.

Analyze the provided game data and produce a structured DFS briefing in JSON format.

Your response must be ONLY valid JSON with these exact keys:
{
  "headline": "One sentence summary of the slate",
  "slate_rating": "A/B/C/D/F rating of the slate for DFS",
  "top_plays": [{"player": "...", "team": "...", "reason": "..."}],
  "value_plays": [{"player": "...", "team": "...", "salary_range": "...", "reason": "..."}],
  "injury_impact": [{"player": "...", "status": "...", "dfs_impact": "..."}],
  "weather_alerts": [{"game": "...", "condition": "...", "impact": "..."}],
  "vegas_movers": [{"game": "...", "movement": "...", "implication": "..."}],
  "stack_of_the_day": {"team": "...", "reason": "...", "players": ["..."]},
  "fade_of_the_day": {"team": "...", "reason": "..."},
  "contrarian_angle": "One unique angle most people will miss",
  "generated_at": "ISO timestamp"
}

Be specific with player names. Be concise. No fluff. DFS-focused only."""

COPILOT_SYSTEM_PROMPT = """You are STACKSNIPER CoPilot — an expert MLB DFS assistant embedded in the STACKSNIPER simulation dashboard.

You have access to the current simulation data. Use it to give specific, actionable DFS advice.

Rules:
- Reference actual player names, projected points, and salaries from the provided context
- Be specific and quantitative — cite numbers
- Never hallucinate stats — only use data from the provided context
- When suggesting player locks, format as: [ACTION:lock:PLAYER_ID:Player Name]
- When suggesting player excludes, format as: [ACTION:exclude:PLAYER_ID:Player Name]
- Keep responses concise and DFS-focused
- Use markdown formatting for readability"""


class LLMService:
    """Multi-provider LLM client for STACKSNIPER."""

    def __init__(self, settings_manager):
        self.settings = settings_manager

    def generate_brief(self, context: dict) -> dict:
        """Generate daily DFS brief from game context."""
        provider = self.settings.get_setting("llm.provider") or "anthropic"
        # Google key uses 'google_ai_api_key' not 'google_api_key'
        key_name = "google_ai_api_key" if provider == "google" else f"{provider}_api_key"
        key = self.settings.get_setting(f"llm.{key_name}")
        model = self.settings.get_setting("llm.model") or "claude-sonnet-4-20250514"

        if not key:
            return {"error": "no_llm_key", "message": "Configure an LLM API key in Settings"}

        user_prompt = self._build_context_prompt(context)
        start = time.time()

        try:
            if provider == "anthropic":
                result = self._call_anthropic(key, model, SYSTEM_PROMPT, user_prompt)
            elif provider == "openai":
                result = self._call_openai(key, model, SYSTEM_PROMPT, user_prompt)
            elif provider == "google":
                result = self._call_google(key, model, SYSTEM_PROMPT, user_prompt)
            else:
                return {"error": f"Unknown LLM provider: {provider}"}

            elapsed = round(time.time() - start, 2)
            result["_meta"] = {
                "provider": provider,
                "model": model,
                "generation_time_seconds": elapsed,
            }
            return result
        except Exception as e:
            log.error(f"LLM error ({provider}): {e}")
            return {"error": str(e), "provider": provider}

    def _build_context_prompt(self, context: dict) -> str:
        parts = [f"Date: {context.get('date', 'today')}\n"]

        games = context.get("games", [])
        if games:
            parts.append(f"## Slate: {len(games)} Games\n")
            for g in games:
                away = g.get("away_team", {})
                home = g.get("home_team", {})
                parts.append(
                    f"- {away.get('abbr','?')} @ {home.get('abbr','?')} | "
                    f"SP: {away.get('probable_pitcher',{}).get('name','TBD')} vs {home.get('probable_pitcher',{}).get('name','TBD')} | "
                    f"Venue: {g.get('venue',{}).get('name','')} | "
                    f"Weather: {g.get('weather',{}).get('temp','')}F {g.get('weather',{}).get('condition','')}"
                )

        injuries = context.get("injuries", [])
        if injuries:
            parts.append(f"\n## Injuries ({len(injuries)})\n")
            for inj in injuries[:20]:
                parts.append(f"- {inj.get('player','')} ({inj.get('team','')}) — {inj.get('status','')}")

        vegas = context.get("vegas", {})
        if vegas:
            parts.append("\n## Vegas Lines\n")
            for game_id, line in list(vegas.items())[:20]:
                parts.append(f"- Game {game_id}: O/U {line.get('total','?')}, Home ML {line.get('home_ml','?')}")

        return "\n".join(parts)

    def _call_anthropic(self, key: str, model: str, system: str, user: str) -> dict:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        max_tokens = self.settings.get_setting("llm.max_tokens") or 4096
        temp = self.settings.get_setting("llm.temperature") or 0.3

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temp,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text
        return self._parse_json_response(text)

    def _call_openai(self, key: str, model: str, system: str, user: str) -> dict:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        max_tokens = self.settings.get_setting("llm.max_tokens") or 4096
        temp = self.settings.get_setting("llm.temperature") or 0.3

        response = client.chat.completions.create(
            model=model if "gpt" in model else "gpt-4o",
            max_tokens=max_tokens,
            temperature=temp,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = response.choices[0].message.content
        return self._parse_json_response(text)

    def _call_google(self, key: str, model: str, system: str, user: str) -> dict:
        import google.generativeai as genai
        genai.configure(api_key=key)
        gmodel = genai.GenerativeModel(
            model if "gemini" in model else "gemini-1.5-flash",
            system_instruction=system,
        )
        response = gmodel.generate_content(user)
        text = response.text
        return self._parse_json_response(text)

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"raw_response": text, "error": "Failed to parse LLM response as JSON"}

    def chat(self, system_prompt: str, context: dict, message: str, history: list = None) -> str:
        """Interactive chat with simulation context."""
        provider = self.settings.get_setting("llm.provider") or "anthropic"
        key_name = "google_ai_api_key" if provider == "google" else f"{provider}_api_key"
        key = self.settings.get_setting(f"llm.{key_name}")
        model = self.settings.get_setting("llm.model") or "claude-sonnet-4-20250514"

        if not key:
            return "⚠️ No LLM API key configured. Add one in Settings to use CoPilot."

        # Build context-enriched system prompt
        context_str = json.dumps(context, indent=2, default=str)
        full_system = f"{system_prompt}\n\n## CURRENT SIMULATION DATA\n{context_str}"

        try:
            if provider == "anthropic":
                return self._chat_anthropic(key, model, full_system, message, history)
            elif provider == "openai":
                return self._chat_openai(key, model, full_system, message, history)
            elif provider == "google":
                return self._chat_google(key, model, full_system, message, history)
            else:
                return f"Unknown LLM provider: {provider}"
        except Exception as e:
            log.error(f"CoPilot chat error ({provider}): {e}")
            return f"⚠️ Chat error: {str(e)}"

    def _chat_anthropic(self, key, model, system, message, history=None):
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        response = client.messages.create(
            model=model, max_tokens=2048, temperature=0.4,
            system=system, messages=messages,
        )
        return response.content[0].text

    def _chat_openai(self, key, model, system, message, history=None):
        from openai import OpenAI
        client = OpenAI(api_key=key)
        messages = [{"role": "system", "content": system}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": message})
        response = client.chat.completions.create(
            model=model if "gpt" in model else "gpt-4o",
            max_tokens=2048, temperature=0.4, messages=messages,
        )
        return response.choices[0].message.content

    def _chat_google(self, key, model, system, message, history=None):
        import google.generativeai as genai
        genai.configure(api_key=key)
        gmodel = genai.GenerativeModel(
            model if "gemini" in model else "gemini-1.5-flash",
            system_instruction=system,
        )
        # Build conversation from history
        chat_history = []
        for msg in (history or []):
            chat_history.append({"role": msg["role"], "parts": [msg["content"]]})
        chat = gmodel.start_chat(history=chat_history)
        response = chat.send_message(message)
        return response.text
