# agent.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from data_layer.model_features import to_df, risk_score, cluster_persona

# LLM is optional; we’ll fall back gracefully
try:
    from dedalus_labs import AsyncDedalus, DedalusRunner
    from dedalus_labs import APIStatusError
except Exception:
    AsyncDedalus = None
    DedalusRunner = None
    class APIStatusError(Exception): ...
    pass

load_dotenv()
MODEL = os.getenv("DEDALUS_MODEL", "openai/gpt-5-mini")
USE_LLM = os.getenv("DEDALUS_USE_LLM", "true").lower() in {"1","true","yes","on"}

def compute_fin_risk(nessie_txns: List[Dict[str,Any]], knot_txns: List[Dict[str,Any]]) -> Dict[str, Any]:
    df = to_df(nessie_txns, knot_txns)
    rs = risk_score(df)
    persona = cluster_persona(df)
    top = df.groupby("bucket")["amount"].sum().sort_values(ascending=False).head(3).to_dict() if not df.empty else {}
    return {"risk_score": rs, "persona": persona, "top_buckets": top}

def micro_recos(persona: str, risk_score: float) -> List[str]:
    base = []
    if persona == "late_night_impulse":
        base = ["Set a food cut-off at 10:30pm with a 5-min reflection timer.",
                "Prep a 2-minute grocery list for tomorrow morning.",
                "Swap 1 late-night delivery/week for a ready meal → save ~$40/wk."]
    elif persona == "weekend_splurger":
        base = ["Pre-commit a fixed 'treat budget' on Fridays.",
                "Compare 2 cheaper bundle options before checkout.",
                "Delay purchases >$30 by 24 hours."]
    elif persona == "daytime_convenience":
        base = ["Batch errands; replace 3 short rideshares with 1 planned ride.",
                "Pack snacks/lunch 2 days/week.",
                "Auto-cancel duplicate convenience subscriptions."]
    else:
        base = ["Track one category this week and cap at 80% of your average.",
                "Enable alerts for purchases > your median ticket size."]
    if risk_score >= 1.2:
        base.insert(0, "⚠️ You’re in a high-risk window this week. Try one micro-rule today.")
    return base[:4]

def _render_offline_reply(user_text: str, ctx: Dict[str, Any], recos: List[str], persona_style: str) -> str:
    badge = "🧘" if persona_style == "Zen Monk" else "🔥" if persona_style == "Savage Best Friend" else "📈"
    lines = [
        f"{badge} **FinKarma ({persona_style})**",
        "",
        f"Risk score: **{ctx['risk_score']:.2f}** · Persona: **{ctx['persona']}** · Top spend: **{ctx['top_buckets']}**",
        ""
    ]
    if ctx["risk_score"] >= 1.2:
        lines.append("⚠️ You’re trending toward a low-balance week. Small tweaks now will prevent regret later.")
    lines.append(f"**You said:** {user_text}")
    lines.append("")
    lines.append("**Try this next:**")
    for r in recos:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("_(LLM temporarily offline or disabled — showing smart rule-based tips so you can keep demoing.)_")
    return "\n".join(lines)

async def run_agent(user_text: str, nessie_txns, knot_txns, persona_style: str = "Zen Monk") -> str:
    ctx = compute_fin_risk(nessie_txns, knot_txns)
    recos = micro_recos(ctx["persona"], ctx["risk_score"])

    if not USE_LLM or AsyncDedalus is None or DedalusRunner is None:
        return _render_offline_reply(user_text, ctx, recos, persona_style)

    prompt = f"""
You are **FinKarma**, a friendly finance guardian. Persona: {persona_style}.
Be supportive, not judgmental. Use specific, behavioral suggestions.
Context (precomputed from user transactions):
- risk_score: {ctx['risk_score']:.2f}  (0–2 scale; >1.2 = high risk)
- persona: {ctx['persona']}
- top_spend_buckets (last 14–30 days): {ctx['top_buckets']}
- example_micro_recommendations: {recos}

User said:
\"\"\"{user_text}\"\"\"

Task:
1) In 2–4 concise bullets, give tailored, behavior-level tips.
2) Refer to the relevant spend buckets if useful.
3) If risk is high (>1.2), open with a quick ⚠️ heads-up.
4) Keep the tone aligned with persona = {persona_style}.
"""
    try:
        async with AsyncDedalus() as client:
            runner = DedalusRunner(client)
            result = await runner.run(input=prompt, model=MODEL)
            return result.final_output
    except APIStatusError:
        return _render_offline_reply(user_text, ctx, recos, persona_style)
    except Exception:
        return _render_offline_reply(user_text, ctx, recos, persona_style)
