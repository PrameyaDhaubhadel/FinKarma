import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

IMPULSE_MERCHANT_HINTS = {
    "food": ["doordash","ubereats","grubhub","postmates","pizza","kfc","mcdonald","burger","taco"],
    "rideshare": ["uber","lyft"],
    "fast_fashion": ["shein","h&m","zara","fashion nova","uniqlo"],
    "alcohol": ["liquor","bar","pub","brew","wine"],
}

def _infer_bucket(merchant: str) -> str:
    m = (merchant or "").lower()
    for bucket, hints in IMPULSE_MERCHANT_HINTS.items():
        if any(h in m for h in hints):
            return bucket
    return "other"

def to_df(nessie_txns, knot_txns) -> pd.DataFrame:
    rows = []
    def push(src, t):
        ts = t.get("timestamp") or t.get("date") or t.get("createdAt") or ""
        rows.append({
            "source": src,
            "amount": float(t.get("amount", 0)),
            "merchant": t.get("merchant") or t.get("merchantName") or "Unknown",
            "timestamp": ts
        })
    for t in nessie_txns: push("nessie", t)
    for t in knot_txns:   push("knot", t)

    df = pd.DataFrame(rows)
    if df.empty: return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    if df.empty: return df
    df["hour"] = df["timestamp"].dt.hour
    df["dow"]  = df["timestamp"].dt.dayofweek
    df["bucket"] = df["merchant"].apply(_infer_bucket)
    return df

def risk_score(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    df["impulse_hour"] = df["hour"].apply(lambda h: 1 if (h>=22 or h<=3) else 0)
    df["impulse_bucket"] = df["bucket"].isin({"food","rideshare","fast_fashion","alcohol"}).astype(int)
    cutoff = df["timestamp"].max() - pd.Timedelta(days=14)
    df["recent"] = (df["timestamp"] >= cutoff).astype(int)
    w = 1.0*df["impulse_hour"] + 0.8*df["impulse_bucket"] + 0.5*df["recent"]
    raw = (df["amount"] * (1 + w)).sum()
    norm = np.clip(raw / (df["amount"].sum() + 1e-6), 0, 2)
    return float(norm)

def cluster_persona(df: pd.DataFrame, k: int = 3) -> str:
    if len(df) < k: return "insufficient_data"
    X = df[["hour","dow"]].copy()
    X["is_impulse"] = df["bucket"].isin({"food","rideshare","fast_fashion","alcohol"}).astype(int)
    km = KMeans(n_clusters=k, n_init=10, random_state=7)
    _ = km.fit_predict(X)
    centers = km.cluster_centers_
    scores = centers[:,0]/24 + centers[:,2]
    top = int(np.argmax(scores))
    if centers[top,0] >= 20 or centers[top,0] <= 3: return "late_night_impulse"
    if centers[top,1] >= 5: return "weekend_splurger"
    return "daytime_convenience"
