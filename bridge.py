import os
import time
import json
import sys
import logging
import traceback
import requests

# -----------------------------------------------------------------------------
# Logging FIRST — so even startup errors appear in Docker logs
# -----------------------------------------------------------------------------

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[handler],
    force=True,
)
logger = logging.getLogger("phonetrack-bridge")

logger.info("Starting Phonetrack bridge (debug mode)")

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DAWARICH_ENDPOINT = "/api/v1/owntracks/points"


# -----------------------------------------------------------------------------
# Environment variables
# -----------------------------------------------------------------------------

def require_env(name):
    value = os.getenv(name)
    if not value:
        logger.error("Missing required environment variable: %s", name)
        raise SystemExit(1)
    return value.strip()

NEXTCLOUD_URL = require_env("NEXTCLOUD_URL").rstrip("/")
SESSION_TOKEN = require_env("SESSION_TOKEN")
DEVICE_NAME = require_env("DEVICE_NAME")

# Dawarich vars not required in debug mode, but we load them anyway
DAWARICH_URL = normalize_dawarich_url(os.getenv("DAWARICH_URL", "").rstrip("/"))
API_KEY = os.getenv("DAWARICH_API_KEY", "")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

logger.info("Config loaded: device=%s poll=%s", DEVICE_NAME, POLL_INTERVAL)

# -----------------------------------------------------------------------------
# Fetch position from Nextcloud
# -----------------------------------------------------------------------------

def fetch_position():
    url = f"{NEXTCLOUD_URL}/apps/phonetrack/api/getlastpositions/{SESSION_TOKEN}"
    logger.debug("Fetching: %s", url)

    r = requests.get(url, timeout=10, verify=VERIFY_SSL)
    r.raise_for_status()

    # Parse JSON safely
    try:
        data = r.json()
    except Exception:
        logger.error("Nextcloud did NOT return JSON. Raw response:")
        logger.error(r.text)
        raise

    # Extract the correct top-level key (your session token)
    token_data = data.get(SESSION_TOKEN)
    if token_data is None:
        raise ValueError(
            f"Nextcloud response does not contain expected session token key '{SESSION_TOKEN}'. "
            f"Raw response: {data!r}"
        )

    # token_data must be a dict of devices
    if not isinstance(token_data, dict):
        raise ValueError(
            f"Expected a dict of devices under session token key, got {type(token_data)}: {token_data!r}"
        )

    # Ensure the device exists
    if DEVICE_NAME not in token_data:
        raise ValueError(
            f"Device '{DEVICE_NAME}' not found. Available devices: {list(token_data.keys())}"
        )

    # Extract and return the position
    pos = dict(token_data[DEVICE_NAME])
    pos["device"] = DEVICE_NAME
    return pos


# -----------------------------------------------------------------------------
# Build OwnTracks-like payload
# -----------------------------------------------------------------------------

def build_payload(pos):
    # Timestamp
    try:
        tst = int(pos.get("timestamp", time.time()))
    except Exception:
        tst = int(time.time())

    # Speed: PhoneTrack stores m/s → Dawarich expects km/h
    try:
        speed_ms = float(pos.get("speed", 0.0))
        vel = round(speed_ms * 3.6, 3)
    except Exception:
        vel = 0.000

    # Course (bearing)
    try:
        cog = round(float(pos.get("bearing", 0.0)), 3)
    except Exception:
        cog = 0.000

    return {
        "_type": "location",
        "lat": pos.get("lat"),
        "lon": pos.get("lon"),
        "tst": tst,
        "alt": pos.get("altitude"),
        "vel": vel,
        "cog": cog,
        "acc": pos.get("accuracy") or 0,
        "batt": pos.get("batterylevel") or 0,
        "tid": DEVICE_NAME[:2].upper(),
        "device": DEVICE_NAME,
    }
    
    
def normalize_dawarich_url(raw):
    if not raw:
        return ""
    url = raw.strip().rstrip("/")

    # Strip endpoint if user mistakenly included it
    if url.endswith(DAWARICH_ENDPOINT):
        url = url[: -len(DAWARICH_ENDPOINT)]

    return url



def send_to_dawarich(payload):
    if not DAWARICH_URL or not API_KEY:
        logger.info("Debug mode: not sending to Dawarich")
        return

    url = f"{DAWARICH_URL}{DAWARICH_ENDPOINT}"
    params = {"api_key": API_KEY}

    try:
        r = requests.post(url, params=params, json=payload, timeout=10, verify=VERIFY_SSL)
        r.raise_for_status()
        logger.info("Sent to Dawarich: %s", r.status_code)
    except Exception as e:
        logger.error("Failed to send to Dawarich: %s", e)


# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

last_ts = None

print(">>> BRIDGE SCRIPT STARTED <<<", flush=True)

while True:
    try:
        pos = fetch_position()
        ts = int(pos.get("timestamp", 0))

        if ts != last_ts:
            payload = build_payload(pos)
            logger.info("New position:\n%s", json.dumps(payload, indent=2))
            send_to_dawarich(payload)
            last_ts = ts
        else:
            logger.debug("No new position")

    except Exception as e:
        logger.error("Error: %s", e)
        logger.error(traceback.format_exc())

    time.sleep(POLL_INTERVAL)
