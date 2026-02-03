# MQTTap

MQTT consumer + FastAPI backend with Postgres storage.

## Local dev (uv)

```powershell
uv sync
uv run python main.py
```

## Frontend (Svelte + Vite)

```powershell
cd frontend
npm install
npm run dev
```

## Docker

```powershell
docker compose up --build
```

## Notes

- Settings are read from env on startup and will be stored in DB later.
- MQTT topics are a comma-separated list.
- Admin bootstrap uses `MQTTAP_ADMIN_EMAIL` and `MQTTAP_ADMIN_PASSWORD`.
