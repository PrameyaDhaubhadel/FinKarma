import os, json, time, requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Try Nessie’s current + legacy hosts (docs point to nessieisreal; reimaginebanking used historically)
# Reconfigurable via NESSIE_BASE if needed.  :contentReference[oaicite:1]{index=1}
DEFAULT_BASES = [
    os.getenv("NESSIE_BASE") or "https://api.nessieisreal.com",
    "https://api.reimaginebanking.com",
]
TIMEOUT = 12
RETRIES = 3

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"
SAMPLE_DIR.mkdir(exist_ok=True)
SAMPLE_FILE = SAMPLE_DIR / "nessie_purchases.json"

def _key() -> str:
    key = os.getenv("NESSIE_API_KEY")
    if not key:
        raise RuntimeError("Set NESSIE_API_KEY in your .env")
    return key

def _http_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    params = dict(params or {})
    params["key"] = _key()
    last_err = None
    for base in DEFAULT_BASES:
        url = f"{base}{path}?{urlencode(params)}"
        for _ in range(RETRIES):
            try:
                r = requests.get(url, timeout=TIMEOUT)
                r.raise_error = r.raise_for_status  # compat
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
                time.sleep(0.8)
        # try next base
    raise last_err or RuntimeError("Nessie GET failed")

def list_accounts() -> List[Dict[str, Any]]:
    # Some deployments require /customers/{id}/accounts; try global /accounts first, then fallback
    try:
        return _http_get("/accounts")
    except Exception:
        # fallback: fetch first customer, then its accounts
        customers = _http_get("/customers")
        if not customers:
            raise
        cid = customers[0]["_id"]
        return _http_get(f"/customers/{cid}/accounts")

def list_purchases(account_id: str) -> List[Dict[str, Any]]:
    return _http_get(f"/accounts/{account_id}/purchases")

def get_sample_transactions() -> List[Dict[str, Any]]:
    try:
        accounts = list_accounts()
        if not accounts:
            raise RuntimeError("No accounts from Nessie")
        acc = accounts[0]
        txns = list_purchases(acc["_id"])
        norm = []
        for t in txns:
            norm.append({
                "amount": float(t.get("amount", 0)),
                "merchant": (t.get("merchant") or {}).get("name") or t.get("description") or "Unknown",
                "timestamp": t.get("purchase_date") or t.get("transaction_date") or t.get("date") or "",
            })
        # cache a small sample for offline fallback
        try:
            SAMPLE_FILE.write_text(json.dumps(norm[:200], indent=2))
        except Exception:
            pass
        return norm
    except Exception:
        # graceful offline fallback
        if SAMPLE_FILE.exists():
            return json.loads(SAMPLE_FILE.read_text())
        # ship a minimal inline sample if no cache yet
        return [
            {"amount": 12.49, "merchant": "DoorDash", "timestamp": "2025-11-01T01:12:00"},
            {"amount": 18.90, "merchant": "UberEats", "timestamp": "2025-11-03T00:47:00"},
            {"amount": 7.15,  "merchant": "Starbucks", "timestamp": "2025-11-04T14:10:00"},
            {"amount": 24.00, "merchant": "Lyft", "timestamp": "2025-11-05T23:35:00"},
        ]
