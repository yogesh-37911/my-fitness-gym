# GymPro — Gym Membership Management System

A modern, production-ready gym management system built with Flask + SQLite.
Runs entirely locally — no cloud, no MongoDB, no internet required after install.

---

## Features

| Module | Details |
|--------|---------|
| **Auth** | PIN-based login with hashing, session management |
| **Dashboard** | Live stats, revenue charts, birthday alerts, notifications |
| **Members** | Add/Edit/Delete, QR code, photo ID card, attendance |
| **Membership** | With/Without Cardio plans, auto expiry calculation |
| **Payments** | Partial/Full tracking, payment history, due alerts |
| **Notifications** | Auto-generated expiry alerts (20/15/10/5/1 days) |
| **Reports** | Revenue charts, Excel export, PDF export |
| **Settings** | Change PIN, gym name/logo, prices, dark mode, DB backup |
| **Search** | Live global search, filter chips |

---

## Quick Start

### 1. Install Python 3.9+

Download from https://python.org

### 2. Clone / Extract the project

```
gym_management/
├── app.py
├── requirements.txt
└── app/
    ├── __init__.py
    ├── models.py
    ├── blueprints/
    ├── static/
    └── templates/
```

### 3. Install dependencies

```bash
cd gym_management
pip install -r requirements.txt
```

### 4. Run

```bash
python app.py
```

Open browser: **http://127.0.0.1:5000**

Default PIN: **1234** ← Change this after first login!

---

## Membership Plans

| Plan | Duration | Total |
|------|----------|-------|
| 1 Month | 1 | 1 month |
| 3+1 Month | 3 + 1 free | 4 months |
| 6+2 Month | 6 + 2 free | 8 months |
| 12+3 Month | 12 + 3 free | 15 months |

Both **With Cardio** and **Without Cardio** variants available.
Prices are editable from the Settings panel.

---

## Auto-Generated Member IDs

Members get sequential IDs: `GYM0001`, `GYM0002`, `GYM0003` ...

---

## Database

SQLite stored at `instance/gym.db`. Tables:

- `admin` — login PIN hash
- `settings` — gym name, logo, currency, dark mode
- `membership_plans` — plan definitions and prices
- `members` — all member data
- `payments` — payment transactions
- `notifications` — expiry alert records
- `attendance` — check-in/check-out logs

---

## Backup & Restore

Settings → **Download Backup** → saves `gym_backup.db`  
Settings → **Restore Database** → upload a `.db` file

---

## Export

- **Excel**: Settings or Reports page → exports all members as `.xlsx`
- **PDF**: Settings or Reports page → exports all members as `.pdf`

---

## Tech Stack

- **Backend**: Python 3.9+ / Flask 3.0 / SQLAlchemy ORM
- **Database**: SQLite (local file)
- **Frontend**: HTML5 / CSS3 / Bootstrap Icons / Chart.js
- **Fonts**: Times New Roman (System font)
- **Auth**: Werkzeug `generate_password_hash` / `check_password_hash`
- **Exports**: openpyxl (Excel), ReportLab (PDF)
- **QR Code**: qrcode + Pillow

---

## Folder Structure

```
gym_management/
├── app.py                    # Entry point
├── requirements.txt
├── instance/
│   └── gym.db                # SQLite database (auto-created)
└── app/
    ├── __init__.py           # App factory + seeding
    ├── models.py             # SQLAlchemy ORM models
    ├── blueprints/
    │   ├── auth.py           # Login / logout
    │   ├── dashboard.py      # Dashboard + notifications
    │   ├── members.py        # Member CRUD, profile, attendance
    │   ├── settings.py       # Admin settings
    │   ├── reports.py        # Excel + PDF exports
    │   └── api.py            # JSON endpoints for AJAX
    ├── static/
    │   ├── css/main.css      # Full design system
    │   ├── js/main.js        # UI logic
    │   └── uploads/          # Gym logo uploads
    └── templates/
        ├── base.html         # Sidebar + topbar layout
        ├── auth/login.html
        ├── dashboard/index.html
        ├── members/          # list, add, edit, profile, renew
        ├── settings/index.html
        └── reports/index.html
```

---

## Default Data

On first run, the system auto-creates:
- Admin PIN: `1234`
- Gym name: `My Fitness gym`
- All 8 membership plan price defaults

---

## Changing the Default PIN

1. Login with PIN `1234`
2. Go to **Settings**
3. Under **Change PIN**, enter new PIN (min 4 digits)
4. Click **Update PIN**
# my-fitness-gym
# my-fitness-gym
