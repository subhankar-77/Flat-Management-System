

## Local Setup (Step by Step)

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 15+ installed and running
- A Razorpay account (free, at razorpay.com)

### 2. Create the PostgreSQL database

```bash
psql -U postgres
CREATE DATABASE society_db;
\q
```

### 3. Clone and install dependencies

```bash
cd society_backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `DATABASE_URL` — your PostgreSQL connection string
- `SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` — from Razorpay dashboard
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — your admin login credentials
- `SOCIETY_NAME`, `SOCIETY_TOTAL_FLATS`, etc.

### 5. Create tables and seed data

```bash
python seed_data.py
```

This creates all PostgreSQL tables and inserts:
- All 9 flats + owners (edit `seed_data.py` first with real names/contacts)
- The admin account

### 6. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

API is now live at: http://localhost:8000
Interactive docs: http://localhost:8000/docs

---

## API Endpoints

### Auth
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/auth/login | Login → returns JWT token |
| GET  | /api/auth/me | Get current admin profile |

### Flats
| Method | URL | Description |
|--------|-----|-------------|
| GET    | /api/flats/ | List all flats (with owners) |
| POST   | /api/flats/ | Add a new flat |
| PUT    | /api/flats/{id} | Update flat details |
| DELETE | /api/flats/{id} | Soft-delete a flat |

### Flat Owners
| Method | URL | Description |
|--------|-----|-------------|
| GET    | /api/owners/ | List all owners |
| POST   | /api/owners/ | Add owner to a flat |
| PUT    | /api/owners/{id} | Update owner details |
| DELETE | /api/owners/{id} | Remove owner |

### Maintenance
| Method | URL | Description |
|--------|-----|-------------|
| GET    | /api/maintenance/?month_year=2025-05 | List charges, filter by month |
| POST   | /api/maintenance/ | Create charge for one flat |
| POST   | /api/maintenance/bulk | Create charges for ALL flats at once |
| PUT    | /api/maintenance/{id} | Update charge / mark paid |
| GET    | /api/maintenance/summary/2025-05 | Dashboard summary for a month |

### Payments
| Method | URL | Description |
|--------|-----|-------------|
| POST   | /api/payments/create-order | Create Razorpay order (step 1) |
| POST   | /api/payments/verify | Verify payment signature (step 2) |
| POST   | /api/payments/webhook | Razorpay webhook (auto-confirmation) |
| POST   | /api/payments/record-cash | Record offline cash payment |
| GET    | /api/payments/ | List all transactions |

### Notices
| Method | URL | Description |
|--------|-----|-------------|
| GET    | /api/notices/ | List active notices |
| POST   | /api/notices/ | Post a new notice |
| PUT    | /api/notices/{id} | Edit notice |
| DELETE | /api/notices/{id} | Delete notice |

---

## Razorpay Integration

### Step 1 — Get API Keys
1. Sign up at https://razorpay.com
2. Go to Dashboard → Settings → API Keys
3. Generate keys — use **Test keys** while developing
4. Copy Key ID and Key Secret into `.env`

### Step 2 — Add your Bank Account
Dashboard → Settings → Bank Account → Add your account details.
All payments will settle to this account automatically.

### Step 3 — Configure Webhook (for production)
1. Dashboard → Settings → Webhooks → Add New Webhook
2. URL: `https://yourdomain.com/api/payments/webhook`
3. Secret: same as `RAZORPAY_KEY_SECRET`
4. Events: select `payment.captured`

### Step 4 — Go Live
1. Complete Razorpay KYC (business verification)
2. Replace test keys with live keys in `.env`
3. Done — payments go directly to your bank account

---

## Deployment (Render — Free Tier)

### Deploy PostgreSQL
1. Go to https://render.com → New → PostgreSQL
2. Name it `society-db`, choose free tier
3. Copy the **External Database URL** (starts with `postgresql://`)

### Deploy the API
1. Push this code to a GitHub repository
2. Render → New → Web Service → connect your repo
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables (same as your `.env` file)
5. Deploy — your API will be live at `https://yourapp.onrender.com`

### After Deploying
Run the seed endpoint once to create the admin:
```
POST https://yourapp.onrender.com/api/auth/seed-admin
```
Then **disable** or remove that endpoint from `auth.py`.

---

## Security Checklist Before Going Live

- [ ] Change `ADMIN_PASSWORD` from default
- [ ] Generate a strong random `SECRET_KEY`
- [ ] Switch Razorpay keys from test to live
- [ ] Remove or disable `/api/auth/seed-admin` endpoint
- [ ] Set `CORS allow_origins` to only your frontend domain
- [ ] Enable HTTPS (Render does this automatically)
- [ ] Complete Razorpay KYC

---

## Database Schema (Summary)

```
users              — admin accounts (email + hashed password)
flats              — flat_number, floor, area_sqft
flat_owners        — name, email, phone, ownership_type → linked to flats
maintenance_charges— amount, month_year, due_date, status → per flat per month
payments           — razorpay_order_id, amount, status, paid_at → per flat
notices            — title, body, category, priority
```
