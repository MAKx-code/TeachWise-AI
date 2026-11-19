# TeachWise AI
### Faculty Intelligence & Student Learning Support Platform
> *Plan Better. Teach Smarter. Support Every Learner.*

Built with Flask + IBM Granite (watsonx.ai) for the IBM BOB Hackathon 2026.

---

## What It Does

TeachWise AI is a complete faculty intelligence platform that:

| Module | Function |
|---|---|
| **Lesson Studio** | AI lesson plans with CO alignment (Granite) |
| **Teaching Materials** | Lecture notes, examples, case studies (Granite) |
| **Assessment Studio** | MCQs, coding exercises, answer keys (Granite) |
| **Student Analytics** | CSV upload → 6-stage AI pipeline |
| **Academic Data** | Full academic dataset management (import, validate) |
| **CO & Analytics** | DB-computed CO attainment, topic gaps, at-risk students |
| **Learning Support** | Gap-matched resources + AI remediation plans |
| **Faculty Analytics** | Class performance dashboard |

### Core AI Pipeline (6 stages)
```
CSV Upload → Python Validation → Performance Calculations →
AI Interpretation (Granite) → Gap Detection → AI Explanations (Granite) →
Personalized Learning Support (Granite)
```

Also: **DB-backed pipeline** using the CS201 synthetic academic dataset:
```
DB Query → Python Analytics → Gap Detection → AI Gap Explanations (Granite) →
AI Support Plan (Granite) → CO Attainment (Python) → CO Interpretation (Granite)
```

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- IBM watsonx.ai credentials (API key + Project ID)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/teachwise-ai.git
cd teachwise-ai

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env and fill in your IBM watsonx.ai credentials

# 5. Initialize database and seed demo data
python run.py          # Creates tables on first start (Ctrl+C after "Running on...")
python seed_academic.py   # Seeds CS201 synthetic dataset (45 students, 1800 records)

# 6. Start the application
python run.py
```

Open: http://localhost:5000

### .env File
```
WATSONX_API_KEY=your_ibm_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
SECRET_KEY=any-random-string-you-choose
DATABASE_URL=sqlite:///teachwise.db
```

---

## Demo Workflow (3 minutes)

1. **Overview** → Dashboard shows CO attainment, at-risk count, gap alerts from live DB
2. **Lesson Studio** → Enter "Data Structures" / "Binary Search Trees" → Generate → Approve
3. **Assessment Studio** → Topic: "Graphs" / Hard / MCQ → Generate → Approve
4. **CO & Analytics** → Select CS201 → See topic performance charts, CO attainment table
5. **CO & Analytics** → Click "Run Full AI Pipeline" → Watch 6 Granite stages execute live
6. **Learning Support** (Academic) → See CS201 weak topics with linked resources + at-risk students
7. **Student Analytics** → Upload `data/demo_students.csv` → Run CSV pipeline → View gaps

---

## Deployment on Railway (Recommended — Free Tier)

Railway is the fastest way to host this Flask app publicly. No credit card required for basic usage.

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "TeachWise AI — initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/teachwise-ai.git
git push -u origin main
```

### Step 2 — Create Railway Account
Go to https://railway.app → Sign up with GitHub (free)

### Step 3 — Deploy

1. Click **"New Project"**
2. Click **"Deploy from GitHub repo"**
3. Select your `teachwise-ai` repository
4. Railway auto-detects Python and uses the `Procfile`

### Step 4 — Add Environment Variables

In Railway dashboard → your project → **Variables** tab, add:

| Variable | Value |
|---|---|
| `WATSONX_API_KEY` | Your IBM API key |
| `WATSONX_PROJECT_ID` | Your watsonx.ai project ID |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` |
| `WATSONX_MODEL_ID` | `ibm/granite-3-8b-instruct` |
| `SECRET_KEY` | Any random 32-character string |
| `DATABASE_URL` | `sqlite:///teachwise.db` |

### Step 5 — Seed the Database

After the first deploy, open Railway's terminal:

```bash
python seed_academic.py
```

Or add it to `nixpacks.toml` build phase (already included).

### Step 6 — Get Your URL

Railway automatically assigns a public URL like `teachwise-ai-production.up.railway.app`

> **Note:** Railway's free tier has 500 hours/month. The SQLite database resets on redeploy — for persistent data, upgrade to Railway's PostgreSQL plugin (free) and set `DATABASE_URL` to the PostgreSQL connection string.

---

## Alternative Deployment: Render

```bash
# render.yaml is not included but setup is identical:
# 1. Connect GitHub repo at https://render.com
# 2. Build command: pip install -r requirements.txt
# 3. Start command: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
# 4. Add same environment variables
```

---

## Running Tests

```bash
python test_p1.py           # DB models + seeded data (23 tests)
python test_p2_validation.py  # Validation engine (27 tests)
python test_pipeline_db.py  # DB-backed pipeline with Granite (requires .env)
python test_app.py          # Full integration suite (requires Granite)
python test_security.py     # Input guardrails (requires Granite)
```

---

## Project Structure

```
teachwise-ai/
├── run.py                     # App entry point
├── seed_academic.py           # CS201 synthetic dataset seeder
├── requirements.txt
├── Procfile                   # Gunicorn for Railway/Heroku
├── railway.json               # Railway deployment config
├── nixpacks.toml              # Build config for Railway
├── .env.example               # Credential template (never commit .env)
│
├── app/
│   ├── __init__.py            # Flask factory
│   ├── models.py              # 22 SQLAlchemy models
│   ├── granite.py             # IBM Granite client (chat API)
│   ├── pipeline.py            # 6-stage CSV pipeline orchestrator
│   ├── analytics.py           # DB analytics (CO attainment, gaps, at-risk)
│   ├── validator.py           # Academic data validation engine
│   ├── routes.py              # Main pages + CSV pipeline API
│   ├── routes_academic.py     # Academic data + DB pipeline routes
│   │
│   ├── agents/
│   │   ├── lesson_planning.py
│   │   ├── teaching_material.py
│   │   ├── assessment.py
│   │   ├── performance_analysis.py
│   │   ├── gap_detection.py
│   │   ├── learning_support.py
│   │   └── co_attainment.py   # CO interpretation agent
│   │
│   ├── templates/             # Jinja2 HTML templates
│   └── static/                # CSS + JS
│
├── data/
│   └── demo_students.csv      # 40-student demo CSV for pipeline
│
└── migrations/                # Flask-Migrate / Alembic
```

---

## IBM Granite Integration

- **SDK:** `ibm-watsonx-ai==1.9.1`
- **API:** `ModelInference.chat()` (current endpoint, not deprecated `generate()`)
- **Model:** `ibm/granite-3-8b-instruct` (configurable via `WATSONX_MODEL_ID`)
- **Agents:** 7 named agent modules, each with separate system prompts
- **Guardrails (application-level):**
  - Input length limits on all API endpoints
  - CSV values treated as untrusted data (not system instructions)
  - Student IDs excluded from numeric stats sent to Granite
  - All AI output marked advisory; faculty approval required
  - Granite never determines data validity (Python-only validation)

> IBM service-level guardrails (HAP/PII) require `generate()` endpoint and are not activated. Application-level controls are implemented and tested.

---

## Known Limitations

| Issue | Impact | Workaround |
|---|---|---|
| Granite JSON truncation at 1024 tokens | Assessment/support plan parse_error (intermittent) | Re-generate; most runs succeed |
| SQLite resets on Railway redeploy | Demo data lost | Re-run `seed_academic.py`; or use Railway PostgreSQL |
| Course names not length-validated in lesson plan form | Low security risk | Fixed in routes.py (CSV upload) |
| `seed_academic.py` requires app to be run once first | First-deploy ordering | Handled in nixpacks.toml build phase |

---

## Credits

Built for the IBM BOB Hackathon 2026 using:
- **IBM Granite** via watsonx.ai
- **Flask** + SQLAlchemy + Flask-Migrate
- **Chart.js** for visualisations
- **pandas** / **numpy** for analytics
