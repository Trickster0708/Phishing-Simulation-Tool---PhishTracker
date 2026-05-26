# 🎣 PhishTracker — Phishing Simulation & Awareness Platform

> ⚠️ **ETHICAL USE ONLY** — This tool is designed exclusively for authorized cybersecurity awareness training within organizations. Never use it against targets without explicit written permission.

---

## Overview

PhishTracker is a full-stack ethical phishing simulation platform built for security teams to train employees on recognizing phishing attacks. It provides campaign management, email simulation, real-time tracking, a fake login page, and an analytics dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask |
| Database | SQLite |
| Frontend | HTML5, Vanilla CSS, JavaScript |
| Charts | Chart.js |
| Email | SMTP / Mailtrap |

---

## Project Structure

```
PhishSim/
├── app.py                  # Main Flask app
├── database.py             # SQLite schema & helpers
├── email_sender.py         # SMTP email with tracking
├── tracker.py              # Tracking pixel, click, phish routes
├── requirements.txt
├── .env.example            # Environment variable template
├── phishsim.db             # Auto-generated SQLite DB
├── templates/
│   ├── base.html           # Sidebar layout
│   ├── login.html          # Admin login
│   ├── dashboard.html      # Analytics dashboard
│   ├── campaigns.html      # Campaign list
│   ├── new_campaign.html   # Create campaign form
│   ├── campaign_detail.html# Per-recipient tracking
│   ├── phishing_page.html  # Fake login landing page
│   └── awareness.html      # Post-submission message
└── static/
    ├── css/style.css       # Dark dashboard theme
    └── js/main.js          # Charts, sidebar, interactivity
```

---

## Quick Start

### 1. Prerequisites

- Python 3.9+
- pip

### 2. Install Dependencies

```bash
cd d:\PhishSim
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)

Copy `.env.example` to `.env` and fill in your SMTP/Mailtrap credentials:

```bash
copy .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-random-secret-key
MAIL_SERVER=smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USERNAME=your_mailtrap_username
MAIL_PASSWORD=your_mailtrap_password
MAIL_FROM=phishsim@yourcompany.com
```

> 💡 **Mailtrap** (https://mailtrap.io) is a free email sandbox — emails won't reach real inboxes during testing.

### 4. Run the App

```bash
python app.py
```

On first run, the database and a default admin account are automatically created:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

> ⚠️ Change the default password immediately after first login!

Visit: **http://127.0.0.1:5000**

---

## Vercel & Neon (PostgreSQL) Production Deployment

PhishTracker supports seamless production deployment on **Vercel** with a cloud **PostgreSQL** database (such as **Neon** or **Supabase**) to ensure database persistence in serverless environments.

### 1. Set Up Neon PostgreSQL
1. Sign up for a free PostgreSQL database at [neon.tech](https://neon.tech).
2. Copy your PostgreSQL connection string (looks like `postgresql://user:pass@host/db?sslmode=require`).

### 2. Configure Vercel Environment Variables
Add the following Environment Variables in your Vercel Project Settings under **Settings ➔ Environment Variables**:

| Environment Key | Description |
|-----------------|-------------|
| `DATABASE_URL` | *Your copied Neon connection string* |
| `SECRET_KEY` | *A long random security string* |
| `MAIL_SERVER` | *e.g. sandbox.smtp.mailtrap.io* |
| `MAIL_PORT` | *e.g. 2525* |
| `MAIL_USERNAME` | *Your SMTP username* |
| `MAIL_PASSWORD` | *Your SMTP password* |
| `MAIL_FROM` | *e.g. phishsim@yourcompany.com* |

When Vercel starts, it will automatically connect to your Neon database, initialize all the tables, and seed the default admin account (`admin` / `admin123`). All data remains stateful and never resets.

---

## Using the Platform

### Create an Admin (CLI)

```bash
flask --app app create-admin
```

### Initialize DB Manually

```bash
flask --app app init-db
```

---

## Workflow

1. **Login** at `/login` with admin credentials
2. **Create Campaign** — Set name, email subject, HTML body, and target emails
3. **Launch Campaign** — Sends phishing emails with unique tracking tokens
4. **Track Results** — View per-recipient open/click/credential data in Campaign Detail
5. **Analytics** — Dashboard shows aggregate click rates, open rates, and submission rates

---

## Tracking Events

| Event | How It's Detected |
|-------|-------------------|
| Email Sent | Logged at time of sending |
| Email Opened | 1×1 GIF tracking pixel `GET /track/open/<token>` |
| Link Clicked | Redirect via `GET /track/click/<token>` |
| Creds Submitted | `POST /phish/submit` |

---

## Security Notes

- Passwords are hashed using Werkzeug's PBKDF2 before storage
- Only the first 2 characters of captured practice passwords are stored; the rest are masked
- All admin routes are protected by Flask-Login
- The tool logs IP addresses and User-Agent strings for audit purposes

---

## License

For educational and ethical security training use only. Redistribution for malicious purposes is strictly prohibited.
