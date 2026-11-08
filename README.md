# LedgerLine

A complete educational financial transaction management demo for the Snovasys Fresher Hiring Challenge 2026. LedgerLine uses simulated funds only.

## Stack

- React + Vite frontend
- Flask + Flask-JWT-Extended API
- SQLite database
- bcrypt password hashing

## Features

- Registration and login with JWT sessions
- User and administrator roles
- Protected, atomic, validated money transfers
- Transaction history for sent and received payments
- Interactive transaction receipts with sender, recipient, status, and reference details
- Authorization-aware security audit trail
- Responsive professional interface

## Local setup (Windows PowerShell)

### 1. Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The API starts at `http://localhost:5000`.

### 2. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| User | aarav@ledgerline.demo | Demo@1234 |
| User | maya@ledgerline.demo | Demo@1234 |
| Admin | admin@ledgerline.demo | Admin@1234 |

Aarav starts with ₹1,250, Maya with ₹850, and the admin starts with ₹5,000 of simulation-only balance.

## Production deployment

- Set `JWT_SECRET_KEY` to a long random value.
- Set `FRONTEND_ORIGINS` to the deployed frontend origin.
- Set `VITE_API_URL` in the frontend build to `https://your-api.example/api`.
- Run `npm run build` and deploy `frontend/dist` to a static host.
- Deploy Flask behind Gunicorn or a managed Python host. Install Gunicorn with `python -m pip install gunicorn`.
- Replace SQLite with PostgreSQL if deploying multiple persistent instances; this demo is configured for single-instance local deployment.

The SQLite file is created automatically in `backend/ledgerline.db`.

## Main API routes

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/me`
- `GET /api/dashboard`
- `GET /api/recipients`
- `POST /api/transfers`
- `GET /api/transactions`
- `GET /api/transactions/{transactionId}`
- `GET /api/admin/audit` (admin only)
- `GET /api/admin/users` (admin only)

## Test the project

Run the backend integration suite from Windows PowerShell:

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest -v test_app.py
```

Run frontend syntax and lint checks:

```powershell
cd frontend
npm run lint
npm run build
```

The backend suite verifies health, JWT access, login failures, registration validation, duplicate accounts, atomic transfers, transaction history, ownership-protected transaction details, audited logout, insufficient funds, self-transfers, and administrator authorization.

## Docker deployment

A production compose setup is included:

```powershell
docker compose up --build
```

The frontend is served on port `8080` and the API on port `5000`. For a persistent deployment, mount `backend/ledgerline.db` or move to PostgreSQL.

## Security notes

- Never use real banking credentials or real funds.
- Set a strong `JWT_SECRET_KEY` in production.
- Restrict `FRONTEND_ORIGINS` to trusted frontend origins.
- JWTs expire after eight hours.
- All account changes happen in an atomic SQLite transaction, and security decisions are stored in the audit log.
