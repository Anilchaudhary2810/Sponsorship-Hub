# 🤝 Sponsorship Management System
## 📌 What is this project?
The **Sponsorship Management System** is a fullstack web application designed to connect **Event Organizers**, **Brands (Sponsors)**, and **Creators (Influencers)**. It streamlines the entire sponsorship lifecycle from discovery and proposals to contract signing and secure payments.
### ✨ Key Features
* **Role-Based Access Control (RBAC):** Dedicated, secure dashboards tailored for Sponsors, Organizers, and Influencers.
* **Deal Lifecycle Management:** An intelligent state machine handling proposals, acceptances, signing, and closed deals.
* **Real-time WebSockets:** Live chat between parties and instant in-app dashboard notifications without refreshing.
* **Secure Authentication:** JWT-based authentication with password hashing.
* **Modern Tech Stack:** 
  - **Backend:** Data-validated Python API via FastAPI & SQLAlchemy.
  - **Frontend:** Fast, responsive React SPA powered by Vite.
  - **Database:** PostgreSQL (Production) / SQLite (Local Dev).
---
## 🚀 How to run backend locally
1. **Navigate to the backend directory:**
   ```bash
   cd backend
Create and activate a virtual environment:

Windows:
bash
python -m venv .venv
.venv\Scripts\activate
Mac/Linux:
bash
python3 -m venv .venv
source .venv/bin/activate
Install the dependencies:

bash
pip install -r requirements.txt
Set up environment variables:

Create a 

.env
 file in the backend/ directory (see variables below).
Start the server:

bash
uvicorn main:app --reload
Available at http://localhost:8000 (API Docs at http://localhost:8000/docs)

🎨 How to run frontend locally
Navigate to the frontend directory:

bash
cd frontend
Install node modules:

bash
npm install
Start the development server:

bash
npm run dev
Available at http://localhost:5173

🌍 Deployment instructions
Backend Deployment (Render / Railway / DigitalOcean)
Build command: pip install -r requirements.txt
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
Add all production environment variables to your host (especially DATABASE_URL pointing to your hosted PostgreSQL database and a strong SECRET_KEY).
Ensure CORS_ORIGINS in your environment variables includes your deployed frontend URL.
Frontend Deployment (Vercel / Netlify)
Ensure the framework preset is set to Vite.
Build command: npm run build
Output directory: dist
Add frontend environment variables (like VITE_API_URL pointing to your deployed FastAPI backend URL).
🔐 Environment variables list
Backend (backend/.env)
env
APP_NAME="Sponsorship Management"
ENV="development" # Change to "production" when deployed
# Security (Change in production)
SECRET_KEY="your_super_secret_jwt_key_here"  
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
# Database (PostgreSQL or SQLite)
DATABASE_URL="postgresql://user:password@localhost:5432/sponsorship_db"
# CORS (Must match frontend URL in production)
CORS_ORIGINS='["http://localhost:5173", "http://127.0.0.1:5173"]'
# Razorpay (Payments)
RAZORPAY_KEY_ID=""
RAZORPAY_KEY_SECRET=""
RAZORPAY_WEBHOOK_SECRET=""
# SMTP (Email Notifications)
SMTP_HOST="localhost"
SMTP_PORT=1025
SMTP_USER=""
SMTP_PASS=""
SMTP_FROM="noreply@sponsorship.com"
Frontend (frontend/.env)
env
VITE_API_URL="http://localhost:8000"
VITE_WS_URL="ws://localhost:8000"
