import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from dedalus_labs import AsyncDedalus, DedalusRunner
from data_layer.model_features import to_df, risk_score, cluster_persona

load_dotenv()
MODEL = os.getenv("DEDALUS_MODEL", "openai/gpt-5-mini")

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
                "Auto-prepare a 2-minute grocery list for tomorrow morning.",
                "Swap 1 late-night delivery/week for ready meals → save ~$40/wk."]
    elif persona == "weekend_splurger":
        base = ["Pre-commit a fixed 'treat budget' on Fridays.",
                "Surface cheaper bundle alternatives on Sat/Sun afternoons.",
                "Delay purchases >$30 by 24 hours."]
    elif persona == "daytime_convenience":
        base = ["Batch errands; avoid 3 small rideshares with 1 planned ride.",
                "Pack snacks/lunch 2 days/week.",
                "Auto-cancel duplicate convenience subscriptions."]
    else:
        base = ["Track one category this week and cap at 80% of average.",
                "Enable alerts for purchases > median ticket size."]
    if risk_score >= 1.2:
        base.insert(0, "⚠️ High-risk window this week. Try one micro-rule today.")
    return base[:4]

async def run_agent(user_text: str, nessie_txns, knot_txns, persona_style: str = "Zen Monk") -> str:
    """
    New approach: precompute risk/persona in Python, inject into prompt.
    No `system` and no `tool_context` (not supported by current Runner).
    """
    ctx = compute_fin_risk(nessie_txns, knot_txns)
    recos = micro_recos(ctx["persona"], ctx["risk_score"])

    prompt = f"""
You are **FinKarma**, a friendly finance guardian. Persona: {persona_style}.
Be supportive, not judgmental. Use specific, behavioral suggestions.
Context you can rely on (precomputed from user transactions):
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

    async with AsyncDedalus() as client:
        runner = DedalusRunner(client)
        result = await runner.run(input=prompt, model=MODEL)  # ✅ no `system`, no `tool_context`
        return result.final_output
