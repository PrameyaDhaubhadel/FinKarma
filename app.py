import os
from dotenv import load_dotenv
load_dotenv()

import asyncio, pandas as pd, streamlit as st

from data_layer.nessie_client import get_sample_transactions
# ⬇️ updated imports
from data_layer.knot_client import dev_bootstrap, get_merchant_accounts, list_transactions_for_merchant
from agent import run_agent

st.set_page_config(page_title="FinKarma", layout="centered")
st.title("🟣 FinKarma — Finance Guardian")
st.caption("Nessie (mock banking) + Knot (merchant/SKU) + Dedalus (AI agent)")

user_id = "demo-user-123"

with st.expander("🔗 Knot (dev)"):
    if st.button("Create session & list TransactionLink merchants"):
        res = dev_bootstrap(user_id)
        st.json(res)
        st.info("Use the session with Knot Web SDK to link a merchant (dev). Merchant IDs are in the list above.")

persona = st.selectbox("Choose agent persona", ["Zen Monk","Savage Best Friend","Investor Dad"])

if st.button("Fetch transactions (Nessie + Knot)"):
    nessie_txns = get_sample_transactions()
    st.write(f"Nessie transactions: {len(nessie_txns)}")
    st.dataframe(pd.DataFrame(nessie_txns)[:50])

    knot_txns = []
    try:
        accounts = get_merchant_accounts(user_id)  # requires external_user_id
        st.write("Knot merchant accounts:", accounts)
        # For demo, if any account is connected, pull transactions via sync:
        connected = [a for a in accounts if a.get("connection", {}).get("status") == "connected"]
        if connected:
            merchant_id = connected[0]["merchant"]["id"]
            knot_txns = list_transactions_for_merchant(user_id, merchant_id, max_items=100)
            st.write(f"Knot transactions: {len(knot_txns)}")
            st.dataframe(pd.DataFrame(knot_txns)[:50])
        else:
            st.info("No connected merchants yet. Use the Knot SDK with the session to link (e.g., DoorDash id 19).")
    except Exception as e:
        st.warning(f"Knot dev: {e}")

    st.session_state["nessie_txns"] = nessie_txns
    st.session_state["knot_txns"]   = knot_txns

user_text = st.text_input("Tell FinKarma what you want help with", "I think I overspend at night on delivery apps.")
if st.button("Ask FinKarma"):
    nessie_txns = st.session_state.get("nessie_txns", [])
    knot_txns   = st.session_state.get("knot_txns", [])
    if not (nessie_txns or knot_txns):
        st.warning("Fetch transactions first.")
    else:
        out = asyncio.run(run_agent(user_text, nessie_txns, knot_txns, persona_style=persona))
        st.success(out)
