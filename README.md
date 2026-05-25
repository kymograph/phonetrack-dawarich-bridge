# PhoneTrack → Dawarich Bridge

A lightweight Dockerized bridge that polls Nextcloud PhoneTrack for the latest device position and forwards it to Dawarich using an OwnTracks‑compatible payload.

---

## 🚀 Features

- Polls PhoneTrack at a configurable interval
- Converts data to OwnTracks JSON
- Sends to Dawarich or logs in debug mode
- Minimal Python 3.12 image
- Clean logging for Docker environments

---

## 🔧 Configuration

Copy `.env.example` to  `.env` file and adapt the environment variables as needed.

### Required

- NEXTCLOUD_URL: Nextcloud base URL
- SESSION_TOKEN: PhoneTrack session token
- DEVICE_NAME: Device name inside the session

### Optional

- DAWARICH_URL: Dawarich base URL
- DAWARICH_API_KEY: API key
- POLL_INTERVAL: Poll interval in seconds (default: 30)
- VERIFY_SSL: true / false

---

## 🐳 Docker Compose

see `docker-compose.yaml` and start with

docker compose up -d

The log should show

```
 [INFO] Sent to Dawarich: 200
```

upon successful sending to Dawarich.

---

## 📝 Notes

- Missing Dawarich variables -> debug mode (no sending)
- SSL verification can be disabled with VERIFY_SSL=false
- Script only sends when a new timestamp is detected

---

## 📄 License

GPLv3V
