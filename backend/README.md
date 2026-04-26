# Sponsorship Hub Backend

This backend is a FastAPI application for auth, user management, marketplace flows, deal lifecycle, trust/KYC, billing/ops, reporting, and realtime features.

## Run Locally

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Available at:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Core Router Prefixes

- `/auth`
- `/users`
- `/events`
- `/campaigns`
- `/deals`
- `/payments`
- `/chat`
- `/notifications` and `/ws/notifications/{user_id}`
- `/reviews`
- `/stats`
- `/ops`
- `/billing`
- `/trust`
- `/proposal`
- `/revenue`
- `/collaboration`
- `/retention`
- `/reports`
- `/integrations`
- `/ai-assistant`

Use `/docs` for the full request/response schemas and up-to-date endpoint list.

## Payments (Current)

The backend uses Razorpay-style order flow (not Stripe PaymentIntent flow):

- `GET /payments/checkout-config`
- `POST /payments/create-order?deal_id=<id>`
- `POST /payments/webhook`

Notes:
- Order creation validates ownership and deal state.
- Final payment settlement is webhook-driven.
- In non-production, local mock order fallback is allowed when gateway keys are not configured.

## Environment Variables

Configured in `backend/config.py`. Common keys:

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

## Testing

From repository root:

```powershell
pytest backend/tests -q
```

For coverage:

```powershell
pytest --cov=backend --cov-report=term-missing
```
