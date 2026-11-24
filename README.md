# OpportunityIQ

A full stack job discovery MVP that indexes real public employer job boards, supports full-text search and explainable skill overlap, and optionally requests live LLM recommendations. No seeded jobs or simulated recommendations appear in the application.

## Quick start

Requires Python 3.11+ with SQLite FTS5 and Node.js 22.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.ingest
uvicorn backend.main:app --reload
```

On Windows PowerShell activate with `.venv\Scripts\Activate.ps1`. In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000. API documentation: http://localhost:8000/docs. A failed board refresh preserves its previous successful records; results older than the configured freshness window are hidden. An empty database returns zero jobs.

## Architecture

Employer Greenhouse and Lever public APIs → normalized records → transactional SQLite and FTS5 index → FastAPI → Next.js/React.

- Source-specific stable identifiers prevent repeat ingestion of the same posting. Cross-board semantic deduplication is not implemented.
- BM25 ranks text results; optional profile matching ranks recognized skill overlap, not probability of hiring.
- Saved job IDs persist in browser storage; the saved-only filter operates on the current page.
- Source health reports last attempt, last successful refresh, and record counts.
- An optional live model request considers up to 25 indexed jobs, validates returned IDs, and does not fall back to simulated answers.

## Configuration

Edit boards.json to configure public employer board identifiers. Board availability can change. Never commit credentials or candidate profiles.

| Variable | Default |
|---|---|
| DATABASE_PATH | data/jobs.db |
| MAX_AGE_DAYS | 7 |
| FRONTEND_ORIGIN | http://localhost:3000 |
| NEXT_PUBLIC_API_URL | http://localhost:8000 |
| OPENAI_API_KEY | unset (AI disabled) |
| OPENAI_MODEL | gpt-4.1-mini |

Set environment variables in the shell before starting the relevant process. The API key is server-side only. External AI requests require explicit profile-sharing consent. Remove personal details from profiles. Model-generated explanations may be inaccurate even when job IDs are validated. This is a local MVP; public deployment requires authentication, rate limits, HTTPS, privacy controls and abuse protection.

## Tests and live measurements

```bash
python -m pytest -q
python -m backend.ingest
python -m scripts.benchmark
cd frontend && npm run build
```

CI runs backend tests and the frontend build. The separate Live employer benchmark workflow runs weekly or manually via Actions, and uploads benchmark.json only after successful ingestion. Test fixtures are confined to temporary databases. No live job count, latency, model accuracy or deployment status is claimed until the relevant run succeeds. The benchmark measures local search execution, not end-to-end production latency.

## Scope

SQLite FTS5 is intentionally used for this MVP. Elasticsearch, Redis, Firebase, Stripe, vector embedding search, public hosting and bulk LLM extraction are future work, not implemented features. The project was developed with AI assistance; review and validate the implementation before relying on it.
