import os, requests
from typing import Dict, Any, List, Optional
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("KNOT_BASE", "https://development.knotapi.com")
TIMEOUT = 20

def _auth():
    cid = (os.getenv("KNOT_CLIENT_ID") or "").strip()
    sec = (os.getenv("KNOT_SECRET") or "").strip()
    if not cid or not sec:
        raise RuntimeError("Set KNOT_CLIENT_ID and KNOT_SECRET in .env")
    return HTTPBasicAuth(cid, sec)

def _headers() -> Dict[str, str]:
    return {"Content-Type": "application/json", "Knot-Version": "2.0"}

def list_merchants(product_type: str="transaction_link", platform: str="web", search: Optional[str]=None) -> List[Dict[str,Any]]:
    payload: Dict[str,Any] = {"type": product_type, "platform": platform}
    if search: payload["search"] = search
    r = requests.post(f"{BASE}/merchant/list", json=payload, auth=_auth(), headers=_headers(), timeout=TIMEOUT)
    if r.status_code == 401:
        raise RuntimeError(f"Knot 401 Unauthorized. Check dev keys & env. Body: {r.text}")
    r.raise_for_status()
    return r.json()

def create_session(external_user_id: str, product_type: str="transaction_link") -> Dict[str,Any]:
    r = requests.post(f"{BASE}/session/create",
                      json={"type": product_type, "external_user_id": external_user_id},
                      auth=_auth(), headers=_headers(), timeout=TIMEOUT)
    if r.status_code == 401:
        raise RuntimeError(f"Knot 401 Unauthorized. Body: {r.text}")
    r.raise_for_status()
    return r.json()

def get_merchant_accounts(external_user_id: str, product_type: str="transaction_link") -> List[Dict[str,Any]]:
    r = requests.get(f"{BASE}/accounts/get",
                     params={"external_user_id": external_user_id, "type": product_type},
                     auth=_auth(), headers=_headers(), timeout=TIMEOUT)
    if r.status_code == 401:
        raise RuntimeError(f"Knot 401 Unauthorized. Body: {r.text}")
    r.raise_for_status()
    return r.json()

def sync_transactions(external_user_id: str, merchant_id: int, cursor: Optional[str]=None, limit: int=25) -> Dict[str,Any]:
    payload: Dict[str,Any] = {"merchant_id": int(merchant_id), "external_user_id": external_user_id, "limit": limit}
    if cursor: payload["cursor"] = cursor
    r = requests.post(f"{BASE}/transactions/sync", json=payload, auth=_auth(), headers=_headers(), timeout=TIMEOUT)
    if r.status_code == 401:
        raise RuntimeError(f"Knot 401 Unauthorized. Body: {r.text}")
    r.raise_for_status()
    return r.json()

def list_transactions_for_merchant(external_user_id: str, merchant_id: int, max_items: int=100) -> List[Dict[str,Any]]:
    items: List[Dict[str,Any]] = []; cursor: Optional[str] = None
    while len(items) < max_items:
        page = sync_transactions(external_user_id, merchant_id, cursor=cursor, limit=min(100, max_items-len(items)))
        items += page.get("transactions", [])
        cursor = page.get("next_cursor")
        if not cursor: break
    return items

def dev_bootstrap(user_id: str) -> Dict[str,Any]:
    merchants = list_merchants("transaction_link","web")
    session = create_session(user_id, "transaction_link")
    return {"merchants": merchants, "session": session}
