# 🦈 LEAD SHARK — Lead Discovery & Compliant Outreach Intelligence Platform

**Lead Shark** is an enterprise-grade lead intelligence and cold outreach platform built with strict adherence to CAN-SPAM, GDPR Article 21, the India DPDP Act 2023, and global email deliverability standards.

Developed as a full-stack companion platform to the **RAG Lead Segregation Agent**, Lead Shark guarantees that cold communications are dispatched only to lawful, verified corporate contacts after human-in-the-loop review.

---

## 🏛️ System Architecture

```mermaid
flowchart LR
    A[Public Sources / CSV Upload] --> B[Lawful Ingestion & Dedup]
    B --> C[DNS / MX Deliverability Verifier]
    C --> D[RAG Lead Segregation Agent]
    D --> E[Human Reviewer Queue]
    E --> F[Sequence & Template Engine]
    F --> G{Pre-Send Compliance Checklist}
    G -- Pass --> H[Safe Virtual Outbound Queue]
    G -- Block --> I[Suppression / Blacklist Log]
    H --> J[Event Webhooks: Replies & Bounces]
    J --> K[Auto-Pause & Reputation Engine]
```

### Core Architecture Pipeline:
1. **Lawful Discovery**: Discovers business leads from open directories (OpenStreetMap, public APIs, CSV imports). Strictly respects `robots.txt`, avoids login-walled data (e.g. LinkedIn), and never solves CAPTCHAs.
2. **Deduplication Engine**: Normalizes email addresses, company domains, and business names to filter duplicates before insertion.
3. **Email Verification**: Multi-stage DNS/MX resolution, syntax checks, role-based tagging (`info@`, `sales@`), and freemail exclusion (`gmail.com`, `yahoo.com` excluded from cold B2B outreach).
4. **RAG Sector Classification**: Interacts with the external RAG Lead Segregation Agent (`POST /api/leads/classify`) with an intelligent transparent local fallback. Low confidence leads (< 75%) are automatically held in the "Needs Review" queue.
5. **Campaign Management**: Sequences with up to 2 follow-ups, merge tags (`{{first_name}}`, `{{company}}`, `{{sector}}`), and email preview modal with mandatory physical postal footer and one-click unsubscribe headers.
6. **Separation of Duties**: Campaign creators cannot approve their own campaigns. Template edits reset approval to Draft.
7. **Strict Compliance & Global Suppression**: Atomic pre-send verification guarantees zero messages are sent to suppressed contacts, unverified emails, or unapproved campaigns.
8. **Public One-Click Unsubscribe**: Unauthenticated public opt-out endpoint immediately adds recipients to permanent suppression.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, Recharts |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy, Pydantic v2, dnspython, email-validator |
| **Database** | PostgreSQL (Supabase) via `DATABASE_URL` / SQLite fallback for development |
| **Auth & Security** | JWT (HS256) Bearer tokens, Role-Based Access Control (`admin`, `reviewer`, `sales`) |
| **Outbound Engine** | Safe Demo Virtual Provider (zero unwanted emails) / SES & SendGrid integration |
| **Deployment** | Backend: **Render** (`render.yaml`, Dockerfile) \| Frontend: **Vercel** (`vercel.json`) |

---

## 🚀 Quickstart Local Execution

### 1. Prerequisites
- Python 3.10+
- Node.js v18+ & npm

### 2. Backend Setup
```bash
cd lead-shark/backend

# Create virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run backend API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend will start at `http://localhost:8000`. Health check: `http://localhost:8000/health`. Swagger Docs: `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
cd lead-shark/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Frontend will start at `http://localhost:3000`.

---

## 🧪 Automated Test Suite

A comprehensive test suite is included in `lead-shark/backend/tests/test_lead_shark.py`:

```bash
cd lead-shark/backend
pytest -v tests
```

### Verified Test Cases:
- [x] Backend startup & `/health` endpoint returns 200 OK
- [x] Database connection & initial user seeding
- [x] JWT Authentication & role switching
- [x] Email deliverability verification (valid MX, risky freemail, invalid syntax)
- [x] Deduplication by email and company domain
- [x] Lawful Lead Discovery job execution
- [x] RAG Sector Classification & confidence scoring
- [x] Campaign lifecycle & mandatory approval separation of duties
- [x] Pre-send compliance checklist blocks unapproved/invalid/suppressed sends
- [x] Public one-click unsubscribe executes without authentication and suppresses permanently
- [x] Analytics overview and compliance audit logging

---

## ☁️ Production Deployment Guide

### A. Backend Deployment on Render
1. Push this repository to GitHub or GitLab.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically detect `lead-shark/backend/render.yaml`.
4. Configure Environment Variables in Render:
   - `DATABASE_URL`: Your Supabase PostgreSQL connection string (`postgresql://postgres:...@...supabase.co:5432/postgres`).
   - `SECRET_KEY`: A secure random secret string.
   - `FRONTEND_ORIGIN`: Your deployed Vercel URL (or `*`).
   - `RAG_AGENT_URL`: External RAG Agent endpoint (optional).
   - `SENDING_MODE`: `safe_demo` (or `live_provider`).
5. Render will build and deploy the web service with `/health` health checks.

### B. Frontend Deployment on Vercel
1. In the [Vercel Dashboard](https://vercel.com), click **Add New** -> **Project**.
2. Select your repository and configure root directory:
   - **Root Directory**: `lead-shark/frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://your-backend.onrender.com` (Your deployed Render backend URL).
4. Click **Deploy**. Vercel will build and serve the application with SPA fallback routing defined in `vercel.json`.

---

## 👥 Default Demo Credentials & Roles

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Admin** | `admin@leadshark.io` | `LeadShark2026!` | Full platform access, suppression management, GDPR erasure |
| **Reviewer** | `reviewer@leadshark.io` | `LeadShark2026!` | Review and approve leads, approve campaigns, review RAG sectors |
| **Sales** | `sales@leadshark.io` | `LeadShark2026!` | Create discovery jobs, import CSVs, draft campaign copy |

*Note: You can seamlessly switch between roles live using the top navigation role switcher in the UI.*

---

## ⚖️ Compliance & Privacy Safeguards
- **CAN-SPAM**: Mandatory physical address footer (`COMPANY_POSTAL_ADDRESS`), truthful sender/subject, instant unsubscribe header (`List-Unsubscribe`).
- **GDPR Article 17**: Dedicated Right to Erasure endpoint (`DELETE /api/leads/by-email`) that purges dossiers while keeping the address suppressed.
- **GDPR Article 21 / India DPDP Act**: One-click unauthenticated public opt-out landing page (`/unsubscribe/:token`).
- **Auto-Pause Thresholds**: Automatic campaign freeze if bounce rate exceeds 3% or spam complaints exceed 0.1%.
