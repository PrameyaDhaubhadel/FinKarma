import os, requests
from typing import List, Dict, Any
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()
BASE = "https://api.nessieisreal.com"  # official Nessie base

def _get_key() -> str:
    key = os.getenv("NESSIE_API_KEY")
    if not key:
        raise RuntimeError("Set NESSIE_API_KEY in environment (e.g., in .env)")
    return key

def _get(path: str, params: Dict[str, Any] = None):
    params = params or {}
    params["key"] = _get_key()
    url = f"{BASE}{path}?{urlencode(params)}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def list_accounts() -> List[Dict[str, Any]]:
    return _get("/accounts")

def list_purchases(account_id: str) -> List[Dict[str, Any]]:
    return _get(f"/accounts/{account_id}/purchases")

def get_sample_transactions() -> List[Dict[str, Any]]:
    accounts = list_accounts()
    if not accounts:
        return []
    acc = accounts[0]
    txns = list_purchases(acc["_id"])
    norm = []
    for t in txns:
        norm.append({
            "amount": float(t.get("amount", 0)),
            "merchant": (t.get("merchant") or {}).get("name") or t.get("description") or "Unknown",
            "timestamp": t.get("purchase_date") or t.get("transaction_date") or t.get("date") or "",
        })
    return norm
