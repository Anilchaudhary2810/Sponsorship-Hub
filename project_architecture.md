# Project Architecture: Sponsorship Management System

## 1. PROJECT OVERVIEW
- **Project Name**: Sponsorship Management System
- **Tech Stack**:
  - **Frontend**: React (Vite-powered), Axios, React Router, jspdf (Invoicing), canvas-confetti.
  - **Backend**: FastAPI (Python), SQLAlchemy ORM, Pydantic, python-jose (JWT).
  - **Database**: SQLite (Development), PostgreSQL (Production capability detected in `requirements.txt`).
  - **Styling**: Vanilla CSS with Crystal-Glassmorphism aesthetic.
- **Architecture Style**: Monolith with separate Frontend (SPA) and Backend (REST API).
- **Deployment Type**: Local development/Custom server ready (FastAPI + Vite).

---

## 2. FOLDER & FILE STRUCTURE

### Tree Structure
```text
/ (root)
├── backend/                  # Python FastAPI Backend
│   ├── routers/              # Modular API endpoints
│   ├── auth.py               # JWT logic & Security
│   ├── crud.py               # SQLAlchemy Database Operations
│   ├── main.py               # Application Entry Point
│   ├── models.py             # SQLAlchemy Models (DB Schema)
│   ├── schemas.py            # Pydantic Schemas (Request/Response)
│   └── database.py           # Engine & Session configuration
├── frontend/                 # React SPA Frontend
│   ├── src/
│   │   ├── components/       # Reusable UI molecules (Modals, Cards)
│   │   ├── pages/            # View components (Dashboards, Auth)
│   │   ├── services/         # API abstraction (Axios instances)
│   │   └── utils/            # Mappers, Formatters, Confetti
│   ├── index.html            # SPA template
│   └── package.json          # Node dependencies
├── docs/                     # Project documentation
└── sponsorship.db            # Default SQLite database
```

### Major Folder Purpose
- **backend/routers**: Keeps API modular. Each resource (Events, Deals, etc.) has its own file.
- **frontend/src/pages**: Contains the main dashboard logic for separate user roles.
- **frontend/src/components**: Encapsulates complex logic like the **Payment Processor** and **Agreement Signer**.

### Entry Points
- **Backend**: `backend/main.py`
- **Frontend**: `frontend/src/main.jsx`

---

## 3. FEATURE BREAKDOWN

### Authentication & RBAC
- **Description**: Secure login/register with roles: `sponsor`, `organizer`, `influencer`.
- **Files**: `backend/auth.py`, `frontend/src/pages/Login.jsx`, `Register.jsx`.
- **Endpoints**: `POST /auth/register`, `POST /auth/login`.

### Sponsorship Pipeline (Events)
- **Description**: Organizers create events; Sponsors discover and propose partnerships.
- **Files**: `OrganizerDashboard.jsx`, `SponsorDashboard.jsx`.
- **Endpoints**: `POST /events/`, `GET /events/`, `POST /deals/`.

### Influencer/Creator Pipeline
- **Description**: Sponsors launch brand campaigns for influencers to apply.
- **Files**: `InfluencerDashboard.jsx`, `backend/routers/campaigns.py`.
- **Endpoints**: `POST /campaigns/`, `GET /campaigns/`, `PUT /deals/{id}/accept`.

### Digital Deal Execution
- **Description**: Automated transition from Proposal -> Payment pending -> Signing -> Closed.
- **Files**: `PaymentModal.jsx`, `AgreementModal.jsx`, `backend/crud.py` (logic for `deal_accept`, `deal_payment`, `deal_sign`).

---

## 4. DATA FLOW ANALYSIS

### UI → API → Database
1. User clicks "Pay" in `SponsorDashboard`.
2. `PaymentModal` calls `markPaymentDone` in `api.js`.
3. Axios sends request to `PUT /deals/{id}/payment`.
4. FastAPI validates with `DealPayment` schema.
5. `crud.deal_payment` updates SQLAlchemy model and commits to SQLite/PostgreSQL.

### Authentication Flow
1. User sends credentials via `Login.jsx`.
2. Backend verifies hash via `pwd_context.verify`.
3. `auth.create_access_token` signs a JWT containing `user_id`.
4. Frontend stores token in `localStorage`.
5. `Axios` interceptor attaches `Authorization: Bearer <token>` to all future requests.

---

## 5. API DOCUMENTATION

| Method | Route | Description | Auth Req? |
|--------|-------|-------------|-----------|
| POST | `/auth/register` | Create new user & get token | No |
| POST | `/auth/login` | Login & get token | No |
| GET | `/users/{id}` | Fetch user profile | Yes |
| GET | `/events/` | List all marketplace events | Yes |
| POST | `/events/` | Create a new event | Yes (Organizer) |
| GET | `/deals/` | List user-specific deals | Yes |
| PUT | `/deals/{id}/accept` | Accept/Reject a proposal | Yes |
| PUT | `/deals/{id}/payment`| Mark deal as paid | Yes (Sponsor) |
| PUT | `/deals/{id}/sign` | Digital signature update | Yes |

---

## 6. DATABASE STRUCTURE

### Models (SQLAlchemy)
- **Users**: `id`, `email`, `password`, `role`, `full_name`, profiles (handle, niche, audience).
- **Events**: `id`, `title`, `budget`, `organizer_id`.
- **Campaigns**: `id`, `title`, `budget`, `creator_id`.
- **Deals**: `id`, `deal_type`, `status` (`proposed`, `payment_pending`, `signing_pending`, `closed`).
- **DealReviews**: `id`, `deal_id`, `reviewer_id`, `rating`.

### Relationships
- **Organizer** (1) ↔ (N) **Events**
- **Deal** (N) ↔ (1) **Event**, **Campaign**, **Sponsor**, **Partner**.

---

## 7. DEPENDENCY ANALYSIS

| Dependency | Purpose |
|------------|---------|
| `FastAPI` | High-performance Python backend framework. |
| `SQLAlchemy` | ORM for database abstraction. |
| `jose` | JWT token signing and verification. |
| `Axios` | Promise-based HTTP client for browser. |
| `jspdf` | Client-side PDF generation for invoices/agreements. |
| `confetti` | Visual feedback on deal completion. |

---

## 8. CONFIGURATION ANALYSIS
- **Environment**: `.env` in `backend` handles `DATABASE_URL`.
- **Frontend Config**: `VITE_API_URL` defaults to `localhost:8000`.
- **Security**: Hardcoded `SECRET_KEY` in `auth.py` (marked as improvement area).

---

## 9. BUSINESS LOGIC SUMMARY
- **Auto-Initiator Acceptance**: When a deal is created, the initiating party is automatically marked as `accepted`.
- **Pipeline Progression**: A deal cannot be `signed` until it is `paid`. It cannot be `paid` until both parties have `accepted`.
- **Role Isolation**: Dashboards filter marketplaces based on user role (e.g., Influencers only see Campaigns).

---

## 10. RISK & BUG-PRONE AREAS
- **Concurrency**: SQLite may lock during high-frequency concurrent writes in a production environment.
- **Validation**: Deliverables and Niche fields in Influencer profiles are free-text; possible formatting inconsistencies.
- **Race Condition**: Two users signing exactly at the same time might cause status update conflicts if not handled with row-locking.

---

## 11. TESTING CHECKLIST

### Functional Tests
- [ ] Register as Sponsor/Organizer/Influencer.
- [ ] Create Event/Campaign (verify attribution to correct user).
- [ ] Propose Partnership (verify initial status `proposed`).

### Edge Cases
- [ ] Sponsor trying to mark payment on a deal they don't own.
- [ ] Accepting a deal that was already rejected.
- [ ] Applying to a campaign twice.

### Security Tests
- [ ] Access `/deals` without a Bearer token.
- [ ] Attempting to login with incorrect password (verify bcrypt failure).

---

## 12. IMPROVEMENT SUGGESTIONS
1. **Security**: Move `SECRET_KEY` to an environment variable immediately.
2. **Architecture**: Implement **WebSockets** for the Chat component to replace `localStorage` polling/persistence.
3. **Database**: Use Alembic for migrations to handle schema changes gracefully.
4. **Logic**: Add a real Stripe/Paypal sandbox integration to `PaymentModal`.
