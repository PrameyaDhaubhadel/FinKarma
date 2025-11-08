import os, asyncio, pandas as pd, streamlit as st
from dotenv import load_dotenv
from data_layer.nessie_client import get_sample_transactions
from data_layer.knot_client import dev_bootstrap_first_account, get_merchant_accounts, list_transactions
from agent import run_agent

load_dotenv()
st.set_page_config(page_title="FinKarma", layout="centered")
st.title("FinKarma — Finance Guardian")
st.caption("Nessie (mock banking) + Knot (merchant/SKU) + Dedalus (AI agent)")

user_id = "demo-user-123"

with st.expander("🔗 Bootstrap Knot (dev)"):
    if st.button("Create Knot session & list TL merchants"):
        res = dev_bootstrap_first_account(user_id)
        st.json(res)
        st.info("Use this session with Knot Web SDK in a real UI to link a merchant (dev mode).")

persona = st.selectbox("Choose agent persona", ["Zen Monk","Savage Best Friend","Investor Dad"])

if st.button("Fetch transactions (Nessie + Knot)"):
    nessie_txns = get_sample_transactions()
    st.write(f"Nessie transactions: {len(nessie_txns)}")
    st.dataframe(pd.DataFrame(nessie_txns)[:50])

    knot_txns = []
    try:
        accts = get_merchant_accounts(user_id)
        st.write("Knot merchant accounts:", accts)
        if accts:
            ma_id = accts[0].get("id") or accts[0].get("merchantAccountId")
            if ma_id:
                knot_txns = list_transactions(user_id, ma_id)
                st.write(f"Knot transactions: {len(knot_txns)}")
                st.dataframe(pd.DataFrame(knot_txns)[:50])
    except Exception as e:
        st.warning(f"Knot dev: {e}")

    st.session_state["nessie_txns"] = nessie_txns
    st.session_state["knot_txns"]   = knot_txns

user_text = st.text_input("Tell FinKarma what you want help with", "I think I overspend at night on delivery apps.")
if st.button("Ask FinKarma"):
    nessie_txns = st.session_state.get("nessie_txns", [])
    knot_txns = st.session_state.get("knot_txns", [])
    if not (nessie_txns or knot_txns):
        st.warning("Fetch transactions first.")
    else:
        out = asyncio.run(run_agent(user_text, nessie_txns, knot_txns, persona_style=persona))
        st.success(out)
