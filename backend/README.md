# Sponsorship Management Backend

This directory contains a FastAPI application providing a CRUD API over a PostgreSQL (or other SQL) database.

## Setup

1. Create a virtual environment and install requirements:
   ```bash
   cd backend
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure environment variables (see `.env.example` if provided). At minimum:
   ```env
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   ```
   If `DATABASE_URL` is not set, the code will fall back to `sqlite:///./development.db`.

3. Run database migrations or allow `models.Base.metadata.create_all()` to create tables (development only).

4. Start the server:
   ```bash
   uvicorn backend.main:app --reload
   ```

## API Endpoints

### Authentication / Users
- `POST /auth/register` (create user)
- `POST /auth/login` (verify credentials)
- `GET /users/{id}`
- `PUT /users/{id}`

### Events
- `POST /events`
- `GET /events`
- `GET /events/{id}`
- `PUT /events/{id}`
- `DELETE /events/{id}`

### Deals
- `POST /deals`
- `GET /deals`
- `GET /deals/{id}`
- `PUT /deals/{id}`
- `DELETE /deals/{id}`
- `PUT /deals/{id}/accept`
- `PUT /deals/{id}/sign`
- `POST /payments/create-intent`

### Reviews
- `POST /reviews`
- `GET /reviews/{deal_id}`

## Testing

A comprehensive automated test suite is provided in `backend/tests/`.

### Run tests:
```bash
pytest --cov=backend --cov-report=term-missing
```

## Security Implementation
- **State Machine**: Deals follow a strict proposed -> accepted -> payment -> sign sequence.
- **Role Control**: CRUD operations are protected by role-based ownership checks.
- **Stripe Integration**: Production-ready PaymentIntent and signature-verified webhooks.
- **Auth**: Dual-token JWT (Access/Refresh) with 1-hour password reset expiration.

