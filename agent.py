import os, asyncio
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
    client = AsyncDedalus()
    runner = DedalusRunner(client)
    tools = [compute_fin_risk, micro_recos]
    system_prompt = f"""
You are FinKarma, a friendly finance guardian. Speak in the persona: {persona_style}.
Be supportive, not judgmental. Use specific, behavioral suggestions.
"""
    result = await runner.run(
        input=user_text,
        system=system_prompt,
        model=MODEL,
        tools=tools,
        tool_context={"nessie_txns": nessie_txns, "knot_txns": knot_txns}
    )
    return result.final_output
