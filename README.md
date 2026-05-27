# SentinelAI

Autonomous AI incident response agent for the TMLS Agentic Hackathon.

## Stack

- Backend: FastAPI, SQLAlchemy, SQLite, OpenAI API
- Frontend: React, Vite, React Router, Recharts
- Integrations: Jira REST API, Slack webhook

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Interactive API docs:

```text
http://localhost:8000/docs
```

Run backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest --basetemp=.\\.tmp_pytest -p no:cacheprovider
```

Demo helpers:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/demo/full-seed
Invoke-RestMethod -Method Post "http://localhost:8000/api/demo/trigger?delay_seconds=30"
Invoke-RestMethod -Method Post "http://localhost:8000/api/demo/reset?keep_config=true"
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```
