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
