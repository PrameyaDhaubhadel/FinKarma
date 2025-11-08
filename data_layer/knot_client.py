import os, base64, requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("KNOT_BASE", "https://development.knotapi.com")  # dev per docs
TIMEOUT = 20

def _creds():
    cid = (os.getenv("KNOT_CLIENT_ID") or "").strip()
    sec = (os.getenv("KNOT_SECRET") or "").strip()
    if not cid or not sec:
        raise RuntimeError("Set KNOT_CLIENT_ID and KNOT_SECRET in your .env")
    return cid, sec

def _headers() -> Dict[str, str]:
    cid, sec = _creds()
    token = base64.b64encode(f"{cid}:{sec}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",  # explicit Basic header
        "Content-Type": "application/json",
        "Knot-Version": "2.0",               # some endpoints require version header
    }

# ---- Merchants ----
def list_merchants(product_type: str = "transaction_link",
                   platform: str = "web",
                   search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    POST /merchant/list with Basic auth. Docs: List Merchants.  :contentReference[oaicite:0]{index=0}
    """
    payload: Dict[str, Any] = {"type": product_type, "platform": platform}
    if search:
        payload["search"] = search
    r = requests.post(f"{BASE}/merchant/list", json=payload, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ---- Sessions (for Web SDK) ----
def create_session(external_user_id: str, product_type: str = "transaction_link") -> Dict[str, Any]:
    """
    POST /session/create with Basic auth + Knot-Version:2.0.  :contentReference[oaicite:1]{index=1}
    """
    r = requests.post(
        f"{BASE}/session/create",
        json={"type": product_type, "external_user_id": external_user_id},
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()  # {"session": "<uuid>"}

# ---- Accounts ----
def get_merchant_accounts(external_user_id: str, product_type: str = "transaction_link") -> List[Dict[str, Any]]:
    """
    GET /accounts/get?external_user_id=...&type=transaction_link with Basic auth.  :contentReference[oaicite:2]{index=2}
    """
    params = {"external_user_id": external_user_id, "type": product_type}
    r = requests.get(f"{BASE}/accounts/get", params=params, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ---- Transactions ----
def sync_transactions(external_user_id: str, merchant_id: int,
                      cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    """
    POST /transactions/sync with Basic auth.  :contentReference[oaicite:3]{index=3}
    """
    payload: Dict[str, Any] = {"merchant_id": int(merchant_id), "external_user_id": external_user_id, "limit": limit}
    if cursor:
        payload["cursor"] = cursor
    r = requests.post(f"{BASE}/transactions/sync", json=payload, headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_transactions_for_merchant(external_user_id: str, merchant_id: int, max_items: int = 100) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    while len(items) < max_items:
        page = sync_transactions(external_user_id, merchant_id, cursor=cursor, limit=min(100, max_items - len(items)))
        items.extend(page.get("transactions", []))
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return items

# ---- Dev helper ----
def dev_bootstrap(user_id: str) -> Dict[str, Any]:
    merchants = list_merchants(product_type="transaction_link", platform="web")
    session = create_session(user_id, product_type="transaction_link")
    return {"merchants": merchants, "session": session}

# ---- Auth sanity check ----
def test_auth(user_id: str) -> Dict[str, Any]:
    """
    Minimal call that should return 200 if creds+headers are correct.
    """
    r = requests.post(f"{BASE}/session/create",
                      json={"type": "transaction_link", "external_user_id": user_id},
                      headers=_headers(),
                      timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
