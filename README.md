# PrizmBet v2

PrizmBet is a crypto sports betting product for the PRIZM ecosystem.
This repository contains the static frontend, backend data ingestion/parsing services, and the foundation for DB-backed bet intake.

## Repository at a glance

- Frontend: `frontend/`
- Backend: `backend/`
- Database migrations: `supabase/migrations/`
- Android client: `mobile/android/`
- Documentation: `docs/`
- Helper scripts: `scripts/`

See full map: [`docs/REPO_STRUCTURE.md`](docs/REPO_STRUCTURE.md)

## Current architecture docs

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)

## Quick start

```bash
cp .env.example .env
pip install -r requirements.txt
python -m backend.run_parsers
python3 -m http.server 8000 -d frontend
```

## Main service entrypoints

```bash
# Parser pipeline
python -m backend.run_parsers

# Bet Intent API
python -m backend.api.bet_intents_api

# PRIZM Tx listener
python -m backend.bot.tx_listener
```

## Notes

- Legacy operational notes are archived in `docs/legacy/`.
- Current docs intentionally keep sensitive operational details at a high level.
