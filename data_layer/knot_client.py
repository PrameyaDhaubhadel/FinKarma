import os, requests
from typing import Dict, Any, List

KNOT_CLIENT_ID = os.getenv("KNOT_CLIENT_ID")
KNOT_SECRET = os.getenv("KNOT_SECRET")
AUTH = (KNOT_CLIENT_ID, KNOT_SECRET)
BASE = "https://api.knotapi.com"

def _check_auth():
    if not (KNOT_CLIENT_ID and KNOT_SECRET):
        raise RuntimeError("Set KNOT_CLIENT_ID and KNOT_SECRET in environment")

def list_tl_merchants() -> List[Dict[str, Any]]:
    _check_auth()
    r = requests.get(f"{BASE}/merchants?type=transaction_link", auth=AUTH, timeout=20)
    r.raise_for_status()
    return r.json()

def create_session(user_id: str) -> Dict[str, Any]:
    _check_auth()
    r = requests.post(f"{BASE}/sessions", json={"userId": user_id}, auth=AUTH, timeout=20)
    r.raise_for_status()
    return r.json()

def get_merchant_accounts(user_id: str) -> List[Dict[str, Any]]:
    _check_auth()
    r = requests.get(f"{BASE}/users/{user_id}/merchant-accounts", auth=AUTH, timeout=20)
    r.raise_for_status()
    return r.json()

def sync_transactions(user_id: str, merchant_account_id: str) -> Dict[str, Any]:
    _check_auth()
    r = requests.post(
        f"{BASE}/users/{user_id}/merchant-accounts/{merchant_account_id}/transactions/sync",
        auth=AUTH, timeout=30
    )
    r.raise_for_status()
    return r.json()

def list_transactions(user_id: str, merchant_account_id: str, limit=200) -> List[Dict[str, Any]]:
    _check_auth()
    r = requests.get(
        f"{BASE}/users/{user_id}/merchant-accounts/{merchant_account_id}/transactions?limit={limit}",
        auth=AUTH, timeout=30
    )
    r.raise_for_status()
    return r.json()

def dev_bootstrap_first_account(user_id: str) -> Dict[str, Any]:
    merchants = list_tl_merchants()
    session = create_session(user_id)
    return {"merchants": merchants, "session": session}
