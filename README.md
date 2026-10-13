# CricImpact — Cricket Batting Contribution Analytics System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0+-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3+-646CFF.svg)](https://vitejs.dev/)
[![Tests Passing](https://img.shields.io/badge/tests-621%20passed-brightgreen.svg)](tests/)
[![Scoring Engine](https://img.shields.io/badge/Scoring%20Engine-v8.5.1--strategy4--hybrid-success.svg)](src/scoring_engine_config.py)

**CricImpact** is a context-aware cricket batting analytics platform that moves beyond traditional batting average and strike rate. By modeling phase of play, match leverage, required run rate pressure, wickets in hand, and entry/exit situations, CricImpact measures a batter's true situational impact on match outcomes across the Indian Premier League (IPL) and Men's International T20Is.

---

## 1. Key Features & Analytics Capabilities

- **Single Source of Truth:** Mathematical scores are calculated deterministically in the backend engine and served pre-computed; zero client-side contribution approximation.
- **Active Scoring Engine: Strategy 4 Calibrated Hybrid Model (`v8.5.1-strategy4-hybrid`)**:
  - Contextual phase segmentation across Powerplay ($P_1$), Middle ($P_2$), and Death ($P_3$).
  - Situational and asymmetric leverage indices.
  - Hyper-score damping preventing score blowouts in high-scoring anomalies.
  - Strict **DNB-Null Invariant**: Did-Not-Bat squad members return `null` (`None`), never misleading 0 or 50 scores.
- **Multi-Tournament & International Scope:**
  - **Indian Premier League (IPL):** Complete historical coverage from 2008 to present.
  - **Men's International T20Is (T20I):** Approved 14-nation scope (India, Australia, England, South Africa, New Zealand, Pakistan, West Indies, Sri Lanka, Bangladesh, Afghanistan, Zimbabwe, Ireland, Scotland, USA) plus registered outside opponents.
  - **Tournament Views:** ICC Men's T20 World Cups (2022, 2024, 2026), Men's Asia Cup 2022, and bilateral/tri-series filters with cross-calendar tour resolution.
- **Interactive Visualizations:** Scatter plots of consistency vs impact, head-to-head batter comparisons, match-level anchor innings breakdown, and situational matchup matrices.

---

## 2. Technology Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pandas, NumPy, Scikit-learn, Joblib.
- **Frontend:** React 19, Vite, Tailwind CSS, Lucide Icons, Recharts.
- **Testing:** Pytest, AnyIO, FastAPI TestClient.

---

## 3. Project Structure

```text
contribution/
├── app/                      # FastAPI Backend Application
│   ├── main.py               # API entrypoint, CORS & middleware
│   └── services/
│       ├── data_service.py   # Data access service & caching layer
│       └── cricket_api_adapter.py # Optional live cricket data adapters
├── frontend/                 # React 19 + Vite Frontend SPA
│   ├── src/
│   │   ├── components/       # UI widgets, filters, charts, leaderboards
│   │   ├── services/api.js   # Client API client (configurable via VITE_API_BASE_URL)
│   │   └── App.jsx           # Main application view & router
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite build & proxy configuration
├── src/                      # Core Contribution Scoring Framework
│   ├── contribution_framework.py # Frozen mathematical engine (SHA256 verified)
│   ├── scoring_engine_config.py  # Active scoring engine selector
│   ├── season_aggregation.py     # Aggregation & leaderboard generation
│   ├── expected_score.py         # Phase-wise expected total models
│   └── expected_batter.py        # Batter expectation regression models
├── models/                   # Pre-trained ML Regressors & Trajectory Models
│   ├── expected_score/       # Random Forest expected innings total
│   ├── expected_score_phase/ # Phase expectation models (PP, Middle, Death)
│   └── expected_batter/      # Batter runs and strike rate models
├── data/
│   ├── processed/            # Curated production CSV datasets
│   │   ├── ipl/              # Processed IPL metrics & matches
│   │   └── t20i/             # Curated T20I matches, rosters & contributions
│   └── scoring_engine_config.json # Runtime engine selection configuration
├── tests/                    # 621 Automated Regression & Unit Tests
├── requirements.txt          # Python runtime dependencies
├── pytest.ini                # Pytest configuration
├── start.bat / stop.bat      # Windows one-click start/stop scripts
└── .env.example              # Environment variable template
```

---

## 4. Getting Started

### 4.1 Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, or 3.13
- **Node.js**: Version 18.x or higher
- **Git**

### 4.2 Clone and Setup Environment

```bash
git clone https://github.com/aadhi567/CricImpact.git
cd CricImpact

# Create and activate Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Frontend dependencies
cd frontend
npm install
cd ..
```

### 4.3 Environment Configuration

Copy the example configuration:
```bash
cp .env.example .env
```

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `HOST` | `127.0.0.1` | Backend host binding |
| `PORT` | `8000` | Backend port |
| `VITE_API_BASE_URL` | `/api` | Base URL for API calls from frontend |
| `CRICKETDATA_API_KEY` | `""` | Optional API key for live provider integration |

---

## 5. Running the Application

### Option A: Windows One-Click (Recommended)
Double-click `start.bat` or run:
```bat
start.bat
```
To shut down all running background processes:
```bat
stop.bat
```

### Option B: Manual Command Line

**Terminal 1 — Backend:**
```bash
# With .venv activated
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 6. Running Tests & Verifications

### Backend Automated Test Suite (621 Tests)
```bash
pytest
```
*All 621 tests pass with 0 failures, covering tournament filtering, DNB null invariants, Strategy 4 leverage, and multi-competition isolation.*

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 7. Active Scoring Engine & Maintenance

### Active Production Engine
CricImpact runs on **Strategy 4 Calibrated Hybrid Model (`v8.5.1-strategy4-hybrid`)**.  
Configuration file: `data/scoring_engine_config.json`
```json
{
  "active_engine": "v8.5.1-strategy4-hybrid",
  "target_engine": "v8.5.1-strategy4-hybrid",
  "baseline_engine": "phase7u"
}
```

### Framework Integrity Check
The core mathematical formulas in `src/contribution_framework.py` are protected by cryptographic integrity:
- **Approved Checksum:** `8C5CFBC613D583CB7B70887C9F8BCE489912C8370FCBD96EF56FBE7E9C8AA277`

### Rollback Runbook
If an emergency reversion is required:
1. Run `python scripts/rollback_to_phase7u.py`.
2. The engine configuration switches back to `phase7u`.
3. Clear `data_service` memory cache by restarting the backend service.

---

## 8. License & Attribution

- Match ball-by-ball data is sourced from and adheres to [Cricsheet](https://cricsheet.org/) terms (Creative Commons Attribution-ShareAlike 4.0 International).
