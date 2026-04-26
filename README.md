# Sponsorship Hub

Sponsorship Hub is a full-stack platform that connects sponsors, organizers, and influencers to manage discovery, deal flow, signing, payments, reviews, and operations.

## Tech Stack
- Backend: FastAPI + SQLAlchemy
- Frontend: React + Vite
- Database: PostgreSQL (recommended) or SQLite (local fallback)
- Realtime: WebSocket notifications and chat
- Payments: Razorpay order + webhook flow

## Repository Structure
- `backend/` FastAPI app, models, routers, tests
- `frontend/` React app
- `docs/` project documentation

## Prerequisites
- Python 3.10+
- Node.js 18+
- npm 9+

## Quick Start

### 1) Start backend
From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Backend will be available at:
- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 2) Start frontend
In a new terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend will be available at:
- `http://localhost:5173`

## Environment Variables

### Backend (`backend/.env`)
Only `SECRET_KEY` should always be set explicitly. Others are optional for local development.

```env
APP_NAME="Sponsorship Management"
DEBUG=false
ENV="development"

SECRET_KEY="replace_with_a_strong_secret"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

DATABASE_URL="sqlite:///./sponsorship.db"

RAZORPAY_KEY_ID=""
RAZORPAY_KEY_SECRET=""
RAZORPAY_WEBHOOK_SECRET=""

SMTP_HOST="localhost"
SMTP_PORT=1025
SMTP_USER=""
SMTP_PASS=""
SMTP_FROM="noreply@sponsorship.com"
SMTP_USE_TLS=false
SMTP_TIMEOUT_SECONDS=10

FRONTEND_BASE_URL="http://localhost:5173"
EMAIL_VERIFICATION_EXPIRE_HOURS=24

AI_API_KEY=""
AI_MODEL="gpt-4o-mini"
AI_API_BASE_URL="https://api.openai.com/v1"
AI_TIMEOUT_SECONDS=25

CORS_ORIGINS='["http://localhost:5173","http://127.0.0.1:5173","http://localhost:5174","http://127.0.0.1:5174"]'
```

### Frontend (`frontend/.env`)

```env
VITE_API_URL="http://localhost:8000"
```

If `VITE_API_URL` is omitted, frontend falls back to `http://<current-host>:8000`.

## Testing
From repository root:

```powershell
pytest backend/tests -q
```

## Notes
- Auth is cookie-based (`withCredentials: true` on frontend API client).
- Deal payment completion is webhook-driven. Manual payment marking is disabled.
- For production, configure `SECRET_KEY`, database, and Razorpay webhook secret before deployment.
