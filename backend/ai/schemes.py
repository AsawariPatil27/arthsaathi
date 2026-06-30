import json
import os
import re

from ai.config.llm import llm

# ── Data ──────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


SCHEMES = _load("schemes.json")
SCHEMES_BY_SLUG = {s["slug"]: s for s in SCHEMES}
PERSONA_SCHEMES = _load("persona_schemes.json")


def _reply(text, buttons=None):
    return {"reply": text, "buttons": buttons or []}


# ── Public entry point ────────────────────────────────────────────────────────
def scheme_reply(user, message):
    msg = str(message or "").strip().lower()
    if msg.startswith("scheme:"):
        return _details(user, msg.split(":", 1)[1].strip())
    return _top_schemes(user)


# ── Step 1 – scheme list ──────────────────────────────────────────────────────
def _top_schemes(user):
    occ = str(user.get("occupation") or "other").lower()
    slugs = PERSONA_SCHEMES.get(occ, [])[:3]

    if not slugs:
        return _reply("No schemes found for your profile. Contact your nearest CSC centre.")

    found = [s for s in (SCHEMES_BY_SLUG.get(sl) for sl in slugs) if s]
    missing = len(slugs) - len(found)

    if not found:
        return _reply("Scheme data is being updated. Try again soon or visit myscheme.gov.in.")

    occ_display = occ.replace("_", " ").title()
    lines = [
        f"*Top Government Schemes for {occ_display}*",
        "─────────────────────────",
    ]
    buttons = []

    for i, s in enumerate(found):
        num = i + 1
        ministry = s.get("ministry", s.get("schemeCategory", ""))
        lines += [
            "",
            f"{num}. *{s.get('scheme_name', '—')}*",
            f"_{ministry}_" if ministry else "",
            f"Benefit: {_short(s.get('benefits', ''), 120)}",
            f"Who can apply: {_short(s.get('eligibility', ''), 100)}",
        ]
        buttons.append([{"text": f"View Scheme {num} Details", "data": f"scheme:{s['slug']}"}])

    lines += ["", "─────────────────────────", "Tap a button below to see full details, documents & how to apply."]

    if missing:
        lines.append(f"\n{missing} scheme(s) from your profile not yet in our database — coming soon.")

    return _reply("\n".join(l for l in lines if l != ""), buttons)


# ── Step 2 – scheme detail ────────────────────────────────────────────────────
def _details(user, slug):
    s = SCHEMES_BY_SLUG.get(slug)

    if not s:
        name = slug.replace("-", " ").title()
        return _reply(
            f"*{name}* is not yet in our database.\n\n"
            "Our team is adding it soon. Meanwhile:\n"
            "https://myscheme.gov.in\n"
            "PM helpline: *1800-11-1555* (toll-free)"
        )

    name = s.get("scheme_name", "—")
    videos = "\n".join(f"▶️ {u}" for u in s.get("youtube_links", []))
    apply_link = s.get("applicationLink", "").strip()

    parts = [
        f"*{name}*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        _llm_explain(user, s),
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    if apply_link:
        parts += ["", f"Apply Online: {apply_link}"]
    if videos:
        parts += ["", f"Watch & Learn:\n{videos}"]
    parts += ["", "Share this scheme with someone who needs it!"]

    return _reply("\n".join(parts))


# ── LLM ───────────────────────────────────────────────────────────────────────
_SYSTEM = (
    "You are ArthSaathi, a friendly Indian government scheme advisor. "
    "Reply for Telegram using exactly these sections:\n"
    "📌 *What is this scheme?* – 2 sentences.\n"
    "✅ *Key Benefits:* – max 4 bullets starting with •\n"
    "📋 *Who Can Apply:* – max 3 bullets starting with •\n"
    "📄 *Documents Needed:* – max 4 bullets starting with •\n"
    "🚀 *How to Apply:* – max 4 numbered steps.\n"
    "Use simple Hinglish. No tables. Each bullet under 10 words. End with 💪 line."
)


def _llm_explain(user, s):
    occ = str(user.get("occupation") or "general public").replace("_", " ")
    try:
        return llm(
            [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Occupation: {occ}\n\nScheme:\n{json.dumps(s, ensure_ascii=False)}",
                },
            ]
        )
    except Exception:
        return (
            f"📌 *What is this scheme?*\n{_short(s.get('details', ''), 200)}\n\n"
            f"✅ *Key Benefits:*\n• {_short(s.get('benefits', ''), 200)}\n\n"
            f"📋 *Who Can Apply:*\n• {_short(s.get('eligibility', ''), 200)}\n\n"
            f"📄 *Documents Needed:*\n• {_short(s.get('documents', ''), 200)}\n\n"
            f"🚀 *How to Apply:*\n{_short(s.get('application', ''), 300)}\n\n"
            "💪 Check the official portal for the latest updates!"
        )


# ── Util ──────────────────────────────────────────────────────────────────────
def _short(value, size=260):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= size else text[:size].rsplit(" ", 1)[0] + "…"
