# ai_helper.py
"""AI features powered by Groq (OpenAI-compatible chat API).

Set your key in the environment (or in a .env file next to app.py):

    GROQ_API_KEY=gsk_...
    GROQ_MODEL=llama-3.3-70b-versatile     # optional

Two features:
  * explain_results()  : writes a plain-English case report from the computed statistics
  * suggest_variables(): maps a free-text question ("are my summers getting hotter?") to variables

The AI never calculates anything. It only receives numbers already computed by stats_engine.py
and is told not to invent any. If no key is set, or Groq is unreachable, the caller falls back to
the rule-based text in plain.py and keyword matching below.
"""
import json
import os
import re

import requests

try:                                  # optional: load GROQ_API_KEY from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

AUDIENCES = {
    "a curious beginner": ("about 120 words, everyday words only, no statistics jargon. Say 'how sure we are' "
                           "instead of p-value."),
    "a 12-year-old": ("about 90 words, short sentences and one friendly everyday analogy. No jargon."),
    "a scientist": ("about 150 words. You may use the method name, Kendall's tau, p-value and confidence "
                    "interval. Mention the key caveats precisely."),
}


class AIUnavailable(RuntimeError):
    """Raised when the AI feature cannot be used (no key, network error, API error)."""


def ai_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def _chat(messages, max_tokens=500, temperature=0.3, json_mode=False) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise AIUnavailable("No GROQ_API_KEY found in the environment, so the built-in explanation is shown.")
    body = {
        "model": os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(GROQ_URL, json=body, timeout=45,
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    except requests.RequestException as e:
        raise AIUnavailable(f"Could not reach Groq ({e.__class__.__name__}).")
    if r.status_code == 401:
        raise AIUnavailable("Groq rejected the API key (401). Check GROQ_API_KEY.")
    if r.status_code == 429:
        raise AIUnavailable("Groq rate limit reached (429). Wait a moment and try again.")
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:200])
        except ValueError:
            msg = r.text[:200]
        raise AIUnavailable(f"Groq error {r.status_code}: {msg}")
    try:
        return r.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError):
        raise AIUnavailable("Unexpected response from Groq.")


# ---------------------------------------------------------------- explanation
EXPLAIN_SYSTEM = """You are a friendly science communicator inside a NASA Earth-data tool.
You receive JSON "facts" that were computed by a statistics engine. Write a short explanation.

Strict rules:
- Use ONLY numbers and place names that appear in the facts. Never invent or recompute numbers.
- If a region is NOT statistically significant, say plainly that no real trend was detected there. Do not
  describe it as rising or falling as if it were established.
- You may suggest possible physical reasons, but only as possibilities ("may be linked to...", "one possible
  reason..."). Never state a cause as proven.
- Mention once, briefly, that the data are model-based (MERRA-2 reanalysis) and describe a large grid cell.
- If there are two regions, compare them directly.
- If "robustness" is present, mention whether the result holds up across different start years.
- If "time_to_significance" is present, mention it in one sentence.
- Plain text only: no headings, no bullet lists, no markdown bold."""


def explain_results(facts: dict, audience: str = "a curious beginner") -> str:
    style = AUDIENCES.get(audience, AUDIENCES["a curious beginner"])
    messages = [
        {"role": "system", "content": EXPLAIN_SYSTEM},
        {"role": "user", "content": f"Audience: {audience}. Length/style: {style}\n\n"
                                    f"FACTS (JSON):\n{json.dumps(facts, ensure_ascii=False, indent=1)}"},
    ]
    return _chat(messages, max_tokens=450, temperature=0.3)


# ---------------------------------------------------------------- variable suggestion
def _keyword_suggest(question: str, variables: dict, top: int = 3):
    q = question.lower()
    scored = []
    for label, info in variables.items():
        score = sum(2 if re.search(r"\b" + re.escape(k), q) else 0 for k in info["keywords"])
        score += 3 if info["plain_name"] in q else 0
        if score:
            scored.append((score, label))
    scored.sort(reverse=True)
    return [lab for _, lab in scored[:top]]


def suggest_variables(question: str, variables: dict, top: int = 3):
    """Return (list of variable labels, explanation text, used_ai: bool)."""
    question = (question or "").strip()
    if not question:
        return [], "", False

    catalog = {info["param"]: f"{info['plain_name']}: {info['definition']}" for info in variables.values()}
    by_param = {info["param"]: label for label, info in variables.items()}
    system = ("You match a person's question about the Earth system to the most relevant variables in a catalog. "
              "Reply ONLY with JSON: {\"variables\": [up to 3 catalog codes, most relevant first], "
              "\"why\": \"one friendly sentence explaining the choice\"}. Use only codes from the catalog. "
              "If nothing fits, return an empty list.")
    try:
        raw = _chat([{"role": "system", "content": system},
                     {"role": "user", "content": f"Question: {question}\n\nCatalog:\n{json.dumps(catalog)}"}],
                    max_tokens=200, temperature=0.0, json_mode=True)
        data = json.loads(raw)
        labels = [by_param[c] for c in data.get("variables", []) if c in by_param][:top]
        if labels:
            return labels, str(data.get("why", "")), True
    except (AIUnavailable, ValueError, TypeError):
        pass
    labels = _keyword_suggest(question, variables, top)
    why = "Matched by keywords in your question." if labels else ""
    return labels, why, False
