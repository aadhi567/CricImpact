# Phase 6A Frontend: Cricket Batter Contribution Analytics Dashboard

A modern, responsive web application and API layer visualizing validated outputs from the **Phase 5B Contextual Batter Contribution Model** and **Phase 6A Season Aggregation & Small-Opportunity Innings Audit**.

---

## Architecture & Principles

1. **Python/Backend is the Single Source of Truth**:
   - The React frontend does NOT calculate contribution scores or alternative formulas.
   - All metrics are served pre-computed from Phase 5B and Phase 6A artifacts.
2. **Phase 5B Four-Pillar Architecture (25% Weight Each)**:
   - **P1 Match Context** (25%): Situation difficulty, entry point, phase leverage, chase urgency.
   - **P2 Batter Performance** (25%): Runs, balls, strike rate, boundaries deviation from situational baseline.
   - **P3 Team-State Impact** (25%): Exact entry-to-exit trajectory change ($\Delta EFS$ in 1st innings, $\Delta RRR$ in chase).
   - **P4 Counterfactual Value** (25%): Incremental value above a replacement-level situational alternative.
3. **Strict Did-Not-Bat (DNB) Rule**:
   - DNB appearances return `NULL` (`None` / `null`) and are displayed as `N/A`.
   - DNB appearances are **never treated as zero, 50, or negative**.
   - DNB appearances **never enter the denominator** of batting averages or contribution metrics.
4. **Contextual Segmentation**:
   - 1st Innings, Chase, Powerplay, Middle Overs, Death Overs, High Pressure.
   - Unobserved segments return `NULL` (`N/A`) and never imply poor performance.
5. **Configurable Player Selection Filters**:
   - Minimum runs (All, 100+, 200+, 300+, 400+, 500+), team, and season filters select subsets without altering underlying contribution metrics.

---

## Technology Stack

- **Backend**: FastAPI, Uvicorn, Pandas, Pytest
- **Frontend**: React 19, Vite 8, React Router 7, Tailwind CSS 4, Recharts, Lucide React

---

## Starting the Application

### Option A: One-Command Startup (Recommended)
From the repository root:
- **Start**: Double-click `start.bat` or run `.\start.bat` in PowerShell.
- **Stop**: Double-click `stop.bat` or run `.\stop.bat` in PowerShell.

This automatically launches both the FastAPI backend and React frontend development server in separate dedicated terminal windows, verifies health, displays URLs, and tracks process PIDs.

### Option B: Manual Multi-Terminal Startup

#### 1. Start the Backend API Server
From the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **Base URL**: `http://127.0.0.1:8000`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/api/health`

### 2. Start the Frontend Development Server
In a separate terminal, from the `frontend/` directory:

```powershell
cd frontend
npm run dev
```

The React dashboard will be accessible at:
- **Local URL**: `http://localhost:5173`

*(Vite is configured to proxy all `/api/*` requests directly to `http://127.0.0.1:8000`)*.

---

## API Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/health` | Health check & service metadata |
| `GET` | `/api/seasons` | Available seasons list & default season |
| `GET` | `/api/teams?season=2016` | Teams list, optionally filtered by season |
| `GET` | `/api/dashboard/summary?season=2016&min_runs=300` | Summary cards: players, innings, average score, positive raw, team share |
| `GET` | `/api/players?season=2016&min_runs=300&search=Kohli` | Analytical player table records with View A and View B metrics |
| `GET` | `/api/player/{player_id}/season/{season}` | Deep player profile: View A, View B, contextual segmentation |
| `GET` | `/api/player/{player_id}/matches?season=2016` | All match appearances (batting innings & DNB matches separated) |
| `GET` | `/api/match/{match_id}/player/{player_id}` | Granular match breakdown: 4 pillars @ 25%, trajectory audit, dynamic explanation |
| `GET` | `/api/charts/scatter?season=2016` | Scatter plot points for Runs vs Score and SR vs Score |

---

## Frontend Pages & Routing

- `/dashboard`: Main dashboard with season selector, team filter, minimum-run pills, analytical table, summary metrics, and scatter plots.
- `/player/:playerId/:season`: Comprehensive player season analysis (e.g. `/player/V%20Kohli/2016`). Shows contribution gauge (Par = 50.0), team contribution share, context breakdown, timeline chart, and match-by-match table.
- `/match/:matchId/player/:playerId`: Granular match contribution detail (e.g. `/match/980907/player/V%20Kohli`). Inspects the 4 pillars (25% each), signals-driven dynamic explanation, entry/exit state, and projected trajectory shift.
- `/audit`: Model specifications, strict DNB rationale, and empirical small-opportunity benchmark edge cases.

---

## Running Automated Tests

```powershell
.\.venv\Scripts\pytest
```

All 140 tests pass (including 9 backend API integration tests and 131 model validation tests).
