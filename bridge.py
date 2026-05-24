import time
import requests
import os

NEXTCLOUD_URL = os.environ["NEXTCLOUD_URL"]
SESSION_TOKEN = os.environ["SESSION_TOKEN"]
DEVICE_NAME = os.getenv("DEVICE_NAME", "").strip()

DAWARICH_URL = os.environ["DAWARICH_URL"]
API_KEY = os.environ["DAWARICH_API_KEY"]

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

last_ts = None

def fetch_position():
    url = f"{NEXTCLOUD_URL}/apps/phonetrack/api/getlastpositions/{SESSION_TOKEN}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

    token_data = data.get("token", {})

    if DEVICE_NAME not in token_data:
        raise ValueError(f"Device {DEVICE_NAME} not found")

    pos = token_data[DEVICE_NAME]
    pos["device"] = DEVICE_NAME
    return pos


def send(pos):
    payload = {
        "_type": "location",
        "lat": pos["lat"],
        "lon": pos["lon"],
        
        "tst": int(pos.get("timestamp", time.time())),
        
        # extended fields
        "alt": pos.get("altitude"),
        "vel": pos.get("speed") or pos.get("vel"),
        "cog": pos.get("bearing") or pos.get("cog"),
        "acc": pos.get("accuracy") or pos.get("acc"),
        "batt": pos.get("batterylevel") or pos.get("batt"),
        
        # device identity
        "tid": (pos.get("device") or "ph")[:2].upper(),
        "device": pos.get("device"),
    }

    requests.post(
        DAWARICH_URL,
        params={"api_key": API_KEY},
        json=payload,
        timeout=10,
    )


while True:
    try:
        pos = fetch_position()
        ts = int(pos.get("timestamp", 0))

        if ts != last_ts:
            send(pos)
            last_ts = ts

    except Exception as e:
        print("error:", e)

    time.sleep(POLL_INTERVAL)
    