# Heaven in a Bite — Project Documentation

**Client:** Koulla Constantinou  
**Studio:** 23 First Street, Bardene, Boksburg, 1459  
**Email:** accounts@heaveninabite.co.za  
**WhatsApp:** +27 84 202 0100  
**Managed by:** Nexera Ventures

---

## Project Overview

Two deliverables in this workspace:

| Deliverable | File | Purpose |
|---|---|---|
| Landing Page | `index.html` | Public-facing website for Heaven in a Bite |
| Invoice App | `app.py` + `templates/` | Internal iPad invoicing system |

---

## Production Environment

| Item | Value |
|---|---|
| **VM IP** | `156.155.253.123` |
| **Invoice App URL** | `http://156.155.253.123:5004` |
| **App Username** | `accounts` |
| **App Password** | `P@ssw0rd` |
| **GitHub Repo** | https://github.com/nexerav/heaveninabite-invoice.git |
| **Deploy Path** | `/home/costa/heaveninabite-invoice` |

---

## All Running Containers on VM

| Container | Port | Status |
|---|---|---|
| heaven-invoicing | 5004 | ✅ Healthy |
| nxtdoor-pl-manager | 5003 | ✅ Healthy |
| nexera-pl-manager | 5002 | Running |
| trading-platform | 5005 | Running |
| property-rental-manager | 5001 | Running |
| portainer_agent | 9001 | Running |

---

## Landing Page (`index.html`)

Single-screen no-scroll landing page. No frameworks — pure HTML/CSS.

**Sections:**
- Brand name & tagline
- Short business description
- Offering pills (Wedding Cakes, Celebration Cakes, Savory Platters, Sweet Platters, Cupcakes, Macarons)
- Contact details (Owner, Studio, WhatsApp, Email, Hours)
- WhatsApp Us + Send Email action buttons

**Changes made:**
- Removed "Our Logo" section and nav link
- Removed portfolio gallery, booking planner, FAQ, contact section
- Simplified to single-screen card layout

---

## Invoice App

### Stack
- **Backend:** Python / Flask + Gunicorn
- **Database:** SQLite (`data/database.db`)
- **PDF Generation:** ReportLab
- **Email:** Brevo (sib-api-v3-sdk)
- **Frontend:** Tailwind CSS (CDN)
- **Container:** Docker via `docker-compose.yml`

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Redirects to login or dashboard |
| `/login` | GET/POST | Login page |
| `/logout` | GET | Clears session |
| `/dashboard` | GET | Invoice list + KPI stats |
| `/invoice/new` | GET/POST | Create new invoice |
| `/invoice/<id>/edit` | GET/POST | Edit existing invoice |
| `/invoice/<id>/delete` | POST | Delete invoice |
| `/invoice/<id>/pdf` | GET | Generate & view PDF |
| `/invoice/<id>/email` | POST | Send invoice via Brevo |
| `/health` | GET | Docker health check |

### Invoice Form Features
- Client dropdown (Marble Group, Akti Bassonia, Other)
- Dynamic multi-row items (Description / Qty / Price) with **+ Add Item** button
- Live calculated total
- FNB banking details displayed with invoice reference

### Dashboard Features
- KPI cards: Total Invoiced, Outstanding (Unpaid), Settled (Paid)
- Filter by status, search by client/invoice number
- Action buttons per row: **PDF**, **Email**, **Edit**, **Delete**
- Email button opens modal to enter recipient address

---

## Email Configuration (Brevo)

| Item | Value |
|---|---|
| **Provider** | Brevo (formerly Sendinblue) |
| **Sender** | `accounts@heaveninabite.co.za` |
| **Sender Status** | ✅ Verified |
| **CC on every send** | `accounts@heaveninabite.co.za` |
| **Attachment** | Invoice PDF auto-generated and attached |

### Email `.env` variables (set on VM only, not in Git)
```
BREVO_API_KEY=xkeysib-...
SENDER_EMAIL=accounts@heaveninabite.co.za
```

---

## VM `.env` File (at `/home/costa/heaveninabite-invoice/.env`)

```
SECRET_KEY=heaveninabite-prod-secret-2026
APP_USERNAME=accounts
APP_PASSWORD=P@ssw0rd
BREVO_API_KEY=<your-brevo-api-key>
SENDER_EMAIL=accounts@heaveninabite.co.za
```

> ⚠️ `.env` is excluded from Git (in `.gitignore`). Credentials are managed directly on the VM.

---

## DevOps Deployment Pipeline

### Standard deploy (code changes):
```bash
# 1. Local — commit and push to GitHub
git add . && git commit -m "your message" && git push

# 2. On VM — pull and rebuild
cd /home/costa/heaveninabite-invoice
git pull && docker compose up -d --build
```

### Credentials-only change (no code change):
```bash
# On VM only — edit .env then restart
cd /home/costa/heaveninabite-invoice
nano .env
docker compose up -d
```

### If container won't start:
```bash
cd /home/costa/heaveninabite-invoice
docker compose down --rmi all
docker compose up -d --build
```

---

## Git Commit History

| Hash | Description |
|---|---|
| `68a4950` | feat: CC accounts@heaveninabite.co.za on every invoice email |
| `839b09e` | fix: show red error banner on failed email |
| `a9a4604` | fix: update login footer to Powered by Nexera Ventures |
| `85675df` | fix: pass BREVO_API_KEY and SENDER_EMAIL into docker-compose |
| `22946f9` | feat: email prompt modal — user enters recipient address |
| `fa79b85` | feat: integrate Brevo transactional email with PDF attachment |
| `e2760a0` | feat: add labels to dashboard action buttons |
| `ffcb35f` | Initial commit — Heaven in a Bite invoice app + landing page |

---

## VS Code Workspace

File: `heaveninabite.code-workspace`  
Open this file in VS Code to load the full project with all settings, tasks and launch configs.

### Tasks available (Terminal → Run Task):
- **Install Requirements** — `pip install -r requirements.txt`
- **Init Database** — `python db_init.py`
- **Run with Docker Compose** — `docker-compose up --build`

### Launch config:
- **Run Flask App** — runs `app.py` locally on port `5004` with `FLASK_DEBUG=1`

---

*Documentation generated by IBM Bob — Nexera Ventures*
