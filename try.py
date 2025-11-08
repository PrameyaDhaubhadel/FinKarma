# quick_knot_check.py
import base64, os, json, requests
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("KNOT_BASE", "https://development.knotapi.com")
cid = (os.getenv("KNOT_CLIENT_ID") or "").strip()
sec = (os.getenv("KNOT_SECRET") or "").strip()
assert cid and sec, "Missing KNOT_CLIENT_ID or KNOT_SECRET"

auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

print("Using client_id prefix:", cid[:8], "…")
r = requests.post(f"{BASE}/merchant/list",
                  headers=headers,
                  json={"type":"transaction_link","platform":"web"},
                  timeout=20)

print("Status:", r.status_code)
print("Response text:", r.text)
r.raise_for_status()
print("OK. Sample merchant:", (r.json() if r.text else None)[:1])
