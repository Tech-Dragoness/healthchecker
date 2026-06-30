<p align="center">
  <img src="frontend/src/assets/Logo.png" alt="Logo" width="120">
</p>

# HealthChecker

A simple, single-page health-prediction CRUD application. Patients submit
blood test values, an AI service (Google Gemini, with automatic key/model
rotation) generates a clinical-style remark, and a rule-based engine tags the
application's risk level. 

```
HealthChecker/
├── app/                  ← FastAPI backend
│   ├── api/routes/applications.py
│   ├── db/connection.py, setup.sql
│   ├── models/models.py
│   ├── schemas/schemas.py
│   ├── services/ai_service.py     ← Gemini integration (key/model rotation)
│   ├── services/risk_service.py   ← rule-based risk tag + fallback remark
│   ├── tasks/ai_tasks.py          ← async queue/worker for AI jobs
│   ├── main.py
│   └── requirements.txt
├── frontend/             ← Vite + React frontend
│   └── src/...
├── .env                  ← YOU create this (see below) — all backend secrets
├── .env.example
└── .gitignore
```

## Features

- 5-key rotation logic
- `gemini-2.5-flash` → `gemini-2.5-flash-lite` fallback
- Exponential backoff/retries
- Exact five-section prompt (`FINDINGS`, `RISK ASSESSMENT`, `IMMEDIATE ACTIONS`, `LIFESTYLE MODIFICATIONS`, `RECOMMENDATION`)
- No-PII-in-prompt design (only age, glucose, haemoglobin, cholesterol are ever 
sent to the AI)
- Deviation/stage labelling which prevents hallucination
- Response parsing/salvage logic

## 1. Database setup

You need PostgreSQL installed and running.

```bash
# Create the database (from a shell, using the postgres superuser)
createdb healthchecker

# Run the schema script
psql -d healthchecker -f "HealthChecker/app/db/setup.sql"
```

(Or open `psql`, run `\c healthchecker`, then paste the contents of
`setup.sql`.) The script creates the `applications` table, enums, and
indexes used for search/filtering. It also has commented-out lines to
create a dedicated low-privilege DB user — uncomment and use them if you
don't want to connect as the superuser.

## 2. Configure the .env file

Copy the example and fill in real values — **this is the only place secrets
live**; every backend module reads from it via `app/db/connection.py` and
`app/services/ai_service.py`.

```bash
cd "HealthChecker"
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY_1=your-real-key
GEMINI_API_KEY_2=...        # optional, up to 5 keys for rotation
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthchecker
DB_USER=healthchecker_user
DB_PASSWORD=your-db-password
FRONTEND_URL=http://localhost:5173
```

(Note: `frontend/.env` is a separate, non-secret file that only holds the
API base URL the browser calls — Vite needs it locally for the build, it's
listed in `.gitignore` and is not a duplicate of your Gemini/DB secrets.)

## 3. Run the backend

```bash
cd "HealthChecker/app"
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..                            # back to "HealthChecker" so "app" is importable as a package
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/health` — you should see `{"status": "ok", ...}`.
Interactive API docs: `http://localhost:8000/docs`.

## 4. Run the frontend

```bash
cd "HealthChecker/frontend"
npm install
npm run dev
```

Visit `http://localhost:5173`.

## 5. Using the system

1. Click **+ New Application**, fill in a name, DOB, email, and three blood
   values, click **Check**. You're taken to the new application's view page.
2. While the AI call is in flight, the Remarks card shows an animated
   "Analysing blood test results…" indicator and **auto-updates** (polls
   every few seconds) once the result lands — no manual refresh needed.
3. Invalid inputs are caught (e.g. empty name, future DOB, glucose = 0 or 5000,
   bad email) — and it will block submission with a message.
4. From the home page, use the **search bar** (matches name/email across
   *all* applications, not just the current page) and the **filters**
   (date range presets, AI vs fallback remark, risk tag) — results and
   pagination both reflect the filtered set.
5. Click **Edit** on an application, change a blood value, save — the
   remarks and risk tag are cleared and recomputed (re-run step 2).
6. Click **Delete** — a confirmation dialog appears; confirming removes the
   row from the list.
7. If for some reason the AI response could not be generated, the Remarks card 
   should show the auto-generated "Automated AI analysis could not be completed…" 
   fallback notice with a warning banner, and the risk tag is still computed 
   correctly from the raw values.

## Notes

- The home page carries a permanent banner: AI remarks are informational
  only and are not a substitute for professional medical advice.
- The risk tag (`normal` / `slightly_abnormal` / `high`) is **never** derived
from the AI's text — it's computed deterministically in
`app/services/risk_service.py` from the three values, and is recalculated on
every create and every edit.