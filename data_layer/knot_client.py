import os, requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

BASE = "https://development.knotapi.com"  # dev host per docs
TIMEOUT = 20

def _auth():
    cid = os.getenv("KNOT_CLIENT_ID")
    sec  = os.getenv("KNOT_SECRET")
    if not (cid and sec):
        raise RuntimeError("Set KNOT_CLIENT_ID and KNOT_SECRET in your environment (.env)")
    return (cid, sec)  # requests will send Basic auth

# -------- Merchants --------

def list_merchants(product_type: str = "transaction_link", platform: str = "web", search: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    POST /merchant/list  (dev host)
    Body: { type: 'transaction_link' | 'card_switcher' | 'shopping' | 'vault', platform: 'web'|'ios'|'android', search?: 'string' }
    """
    payload: Dict[str, Any] = {"type": product_type, "platform": platform}
    if search:
        payload["search"] = search
    r = requests.post(f"{BASE}/merchant/list", json=payload, auth=_auth(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# -------- Sessions (for Web SDK init) --------

def create_session(external_user_id: str, product_type: str = "transaction_link") -> Dict[str, Any]:
    """
    POST /session/create   (dev host)
    Body must include type + external_user_id
    """
    r = requests.post(
        f"{BASE}/session/create",
        json={"type": product_type, "external_user_id": external_user_id},
        auth=_auth(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()  # { "session": "<uuid>" }

# -------- Accounts (linked merchants for a user) --------

def get_merchant_accounts(external_user_id: str, product_type: str = "transaction_link") -> List[Dict[str, Any]]:
    """
    GET /accounts/get?external_user_id=...&type=transaction_link
    Returns array of merchant accounts with merchant.id + connection.status, etc.
    """
    params = {"external_user_id": external_user_id, "type": product_type}
    r = requests.get(f"{BASE}/accounts/get", params=params, auth=_auth(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# -------- Transactions (sync) --------

def sync_transactions(external_user_id: str, merchant_id: int, cursor: Optional[str] = None, limit: int = 25) -> Dict[str, Any]:
    """
    POST /transactions/sync
    Body: { merchant_id, external_user_id, cursor?, limit? }
    Returns: { merchant, transactions: [...], next_cursor }
    """
    payload: Dict[str, Any] = {"merchant_id": int(merchant_id), "external_user_id": external_user_id, "limit": limit}
    if cursor:
        payload["cursor"] = cursor
    r = requests.post(f"{BASE}/transactions/sync", json=payload, auth=_auth(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def list_transactions_for_merchant(external_user_id: str, merchant_id: int, max_items: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience: page through sync until we collect ~max_items or cursor ends.
    """
    items: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    while len(items) < max_items:
        page = sync_transactions(external_user_id, merchant_id, cursor=cursor, limit=min(100, max_items - len(items)))
        items.extend(page.get("transactions", []))
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return items

# -------- Dev helper (for your Streamlit button) --------

def dev_bootstrap(user_id: str) -> Dict[str, Any]:
    merchants = list_merchants(product_type="transaction_link", platform="web")
    session = create_session(user_id, product_type="transaction_link")
    return {"merchants": merchants, "session": session}
