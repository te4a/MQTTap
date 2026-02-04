# MQTTap

MQTTap is an MQTT consumer with a FastAPI backend and a Svelte UI. It subscribes to MQTT topics, stores data in PostgreSQL, adapts tables to evolving JSON payloads, and provides history and charts with optional aggregation.

## Features

- MQTT ingestion with automatic topic subscription and reconnect
- PostgreSQL storage with per-topic tables
- Dynamic schema for JSON payloads (new fields become new columns; missing fields stay as NULL)
- Scalar topics stored in a generic value table
- History and chart API with optional aggregation (min/max/avg)
- User authentication (JWT) and role-based access (admin/user)
- Admin UI for service settings and user management
- Saved charts per user
- Frontend served by the backend from `frontend/dist`

## Quick Start (Local, uv)

```powershell
uv sync
uv run python main.py
```

Open:
- API: `http://localhost:8000/health`
- UI (after build): `http://localhost:8000/`

## Frontend (Svelte + Vite)

Development svelte only:
```powershell
cd frontend
pnpm install
pnpm dev
```

Build for production (served by backend):
```powershell
cd frontend
pnpm build
```

## Docker (without Dockerfile)

```powershell
docker compose up --build
```

### Example docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_DB: mqttap
      POSTGRES_USER: mqttap
      POSTGRES_PASSWORD: mqttap
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"

  mqttx:
    image: python:latest
    working_dir: /app
    volumes:
      - ./:/app
    environment:
      MQTTAP_DATABASE_DSN: postgresql+asyncpg://mqttap:mqttap@postgres:5432/mqttap
      MQTTAP_ADMIN_USERNAME: admin
      MQTTAP_ADMIN_PASSWORD: admin123
    depends_on:
      - postgres
      - mosquitto
    ports:
      - "8000:8000"
    command: >
      sh -c "pip install --no-cache-dir -U pip &&
             pip install --no-cache-dir . &&
             python main.py"

volumes:
  postgres_data:
```

## Configuration

### Environment Variables

These are **bootstrap** values. Runtime settings (MQTT host, topics, etc.) are stored in the database and can be changed via the admin UI. The backend **seeds** the settings table on first start if it is empty.

- `MQTTAP_DATABASE_DSN` — Postgres DSN for the main DB
- `MQTTAP_ADMIN_DATABASE_DSN` — optional DSN with `createdb` rights (used only if DB does not exist)
- `MQTTAP_JWT_SECRET` — secret for JWT tokens
- `MQTTAP_JWT_EXP_MINUTES` — token lifetime (minutes)
- `MQTTAP_CORS_ORIGINS` — comma-separated allowed origins

Admin bootstrap (only if **users table is empty**):
- `MQTTAP_ADMIN_USERNAME`
- `MQTTAP_ADMIN_EMAIL` (optional)
- `MQTTAP_ADMIN_PASSWORD`

### Settings Stored in Database

These are editable in the UI (Admin → Settings):
- `mqtt_host`
- `mqtt_port`
- `mqtt_topics` (comma-separated)
- `mqtt_username`
- `mqtt_password`
- `float_precision` (rounding for floats)
- `default_agg` (avg/min/max)
- `default_interval` (minute/hour/day)

> Note: Database DSN is **not** part of runtime settings.

## Data Model

### JSON Topics

- One table per topic.
- Columns are created on-the-fly for each JSON key.
- When a field disappears from payloads, the column remains for history and new rows contain NULL.

### Scalar Topics

- One table per topic (last path segment).
- Columns: `ts`, `value_type`, `value_int`, `value_float`, `value_bool`, `value_text`, `value_json`.

## MQTT Connection

- The service logs connection errors (e.g., auth failures).
- If the MQTT broker is unavailable, the app will **not crash**; it retries.

## Troubleshooting

### "Frontend not built" message
Build the UI:
```powershell
cd frontend
pnpm build
```

## License

GNU GPLv3