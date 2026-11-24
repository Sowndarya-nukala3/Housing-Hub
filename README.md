# Housing Hub — Smart Housing Management

Household management for web and mobile using Python FastAPI, SQLAlchemy, SQLite (default) or MySQL, and React Native / Expo.

## Features
- Master and guest dashboards, household invitations and property layouts.
- Chore assignments, completion history, calendar and fairness analytics.
- Shared groceries, messaging and profile editing.
- Smart Wallet with equal/custom expense splits, balances, settlements and separate household bills.
- Pastel interface and interactive selectors.

## Run locally (macOS)
Install Python 3.11+ and a compatible Node.js version. From the project root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PUBLIC_BASE_URL=http://$(ipconfig getifaddr en0):8000
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Website: http://localhost:8000/web/ — API docs: http://localhost:8000/docs.

In a second terminal, from the project root:

```sh
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://$(ipconfig getifaddr en0):8000 npx expo start --lan
```

The original mobile manifest uses Expo SDK 54. If your working local installation uses a newer SDK, retain its package.json and package-lock.json together, or follow Expo's SDK upgrade instructions. Phone and Mac must share a network. For browser access from another device, set CORS_ORIGINS to the appropriate origin if necessary.

## Tests
From backend with the virtual environment active:

```sh
python test_release.py
python test_v6.py
```

Tests use temporary SQLite databases. No existing records are included in this distribution.

## Optional MySQL
The compose.yaml is for local development only. Run `docker compose up -d` from the root, then set DATABASE_URL to `mysql+pymysql://housing:localdevpassword@127.0.0.1:3307/housing` before starting the backend. Replace development credentials before any deployment. SQLite data is not automatically migrated.

## Release scope
Consolidated original project configuration, Final RC backend and tests, and Smart Wallet frontend (including Polish changes). Backend integration tests pass with SQLite. Physical mobile and browser acceptance tests, MySQL verification and production security hardening remain necessary. No real payments or push notifications; proposed smart scheduling and predictive analytics are not included. Do not commit local databases, secrets or dependencies.
