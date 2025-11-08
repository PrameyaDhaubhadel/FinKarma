import os, asyncio
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()  # must be before importing any client code

from data_layer.nessie_client import get_sample_transactions
from data_layer.knot_client import dev_bootstrap, get_merchant_accounts, list_transactions_for_merchant, test_auth
from agent import run_agent 


st.set_page_config(page_title="FinKarma — Finance Guardian", layout="centered")
st.title("🟣 FinKarma — Finance Guardian")
st.caption("Nessie (mock banking) + Knot (merchant/SKU enrichment) + Dedalus (AI agent)")

# simple dev user
USER_ID = "demo-user-123"

# --- Controls ---
persona = st.selectbox("Choose agent persona", ["Zen Monk", "Savage Best Friend", "Investor Dad"])
use_llm = st.checkbox("Use Dedalus LLM (disable if out of credits)", value=True)
os.environ["DEDALUS_USE_LLM"] = "true" if use_llm else "false"

# --- Knot dev helpers ---
with st.expander("🔗 Knot (dev)"):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Test Knot auth"):
            try:
                res = test_auth(USER_ID)
                st.success("Knot auth looks good ✅ (session created).")
                st.json(res)
            except Exception as e:
                st.error(f"{e}")
                st.caption("Check KNOT_CLIENT_ID / KNOT_SECRET in your .env (dev keys, no quotes/spaces).")

    with col2:
        if st.button("Create session & list merchants"):
            try:
                res = dev_bootstrap(USER_ID)   # { merchants: [...], session: {"session": "<uuid>"} }
                st.success("Knot session created; merchants loaded.")
                st.json(res.get("merchants", []))
                session_token = (res.get("session") or {}).get("session")
                if not session_token:
                    st.error("No session token returned from Knot.")
                else:
                    html = Path("knot_link.html").read_text(encoding="utf-8").replace("%SESSION%", session_token)
                    components.html(html, height=700, scrolling=True)
                    st.info("Complete the test flow in the widget (use dev/test credentials from your Knot dashboard).")
            except Exception as e:
                st.error(f"{e}")

merchant_id = st.number_input("Dev merchant id for Knot (e.g., 19 = DoorDash)", min_value=1, value=19, step=1)

if st.button("Pull Knot demo transactions (dev sync)"):
    try:
        knot_txns = list_transactions_for_merchant(USER_ID, int(merchant_id), max_items=100)
        st.success(f"Pulled {len(knot_txns)} Knot dev transactions for merchant {merchant_id}")
        st.dataframe(pd.DataFrame(knot_txns)[:50])
        st.session_state["knot_txns"] = knot_txns
    except Exception as e:
        st.error(f"Knot dev sync failed: {e}")

# --- Nessie / Knot live fetch ---
if st.button("Fetch transactions (Nessie + Knot)"):
    # Nessie (with offline fallback)
    nessie_txns = get_sample_transactions()
    st.write(f"Nessie transactions: {len(nessie_txns)}")
    st.dataframe(pd.DataFrame(nessie_txns)[:50])

    # Knot accounts + txns (if linked)
    knot_txns = st.session_state.get("knot_txns", [])
    try:
        accounts = get_merchant_accounts(USER_ID)  # after linking via SDK
        st.write("Knot merchant accounts:", accounts)
        connected = [a for a in accounts if a.get("connection", {}).get("status") == "connected"]
        if connected:
            mid = connected[0]["merchant"]["id"]
            knot_txns = list_transactions_for_merchant(USER_ID, int(mid), max_items=100)
            st.success(f"Knot transactions: {len(knot_txns)}")
            st.dataframe(pd.DataFrame(knot_txns)[:50])
        else:
            st.info("No connected merchants yet. Link via the Knot widget above or use the dev sync button.")
    except Exception as e:
        st.warning(f"Knot accounts fetch: {e}")

    st.session_state["nessie_txns"] = nessie_txns
    st.session_state["knot_txns"] = knot_txns

# --- Agent ask ---
user_text = st.text_input("Tell FinKarma what you want help with", "I think I overspend at night on delivery apps.")
if st.button("Ask FinKarma"):
    nessie_txns = st.session_state.get("nessie_txns", [])
    knot_txns = st.session_state.get("knot_txns", [])
    if not (nessie_txns or knot_txns):
        st.warning("Fetch transactions first (or use the dev sync button).")
    else:
        out = asyncio.run(run_agent(user_text, nessie_txns, knot_txns, persona_style=persona))
        st.markdown(out)
