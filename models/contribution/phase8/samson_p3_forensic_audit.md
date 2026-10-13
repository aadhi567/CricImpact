# Forensic Audit Report: Sanju Samson P3 Team-State Impact Analysis

**Document ID:** `models/contribution/phase8/samson_p3_forensic_audit.md`  
**Date:** 10 October 2026  
**Subject:** Sanju Samson (SV Samson) — 97* (50) vs West Indies, ICC Men's T20 World Cup 2026  
**Status:** COMPLETE FORENSIC AUDIT (READ-ONLY)  
**Audit Finding:** **P3 SCORE NOT VALIDATED / INCORRECT (Upstream Feature Sign Inversion in T20I/SMAT Ingestion Pipeline)**

---

## Executive Summary

This forensic audit investigates whether Sanju Samson's P3 (Team-State Impact) score of **37.2** (Adjusted P3: **37.4**, Final Contribution Score: **66.3**) from India's successful chase of 196 against the West Indies on 1 March 2026 at Eden Gardens, Kolkata, is mathematically and methodologically correct.

### Key Audit Conclusions:
1. **The Stored Value is Graphically Inconsistent with Match Impact:** Sanju Samson entered at 0/0 chasing 196, batted the entire innings (50 legal balls, 97* runs, strike rate 194.0, 12 fours, 4 sixes), liquidated 100% of the target, and struck the winning boundary on over 19.2 to seal a 5-wicket victory. His individual performance (P2) is rated an elite **95.9**, but his Team-State Impact (P3) is scored at **37.2**—sub-replacement / negative impact.
2. **Fresh Production Calculation Agrees with Stored Data Given the Input Row:** Running `compute_production_contribution(row, apply_attribution=True)` against the stored T20I dataset row reproduces `P1=47.7`, `P2=95.9`, `P3=37.2`, `Adj P2=95.2`, `Adj P3=37.4`, `Leverage=0.984`, `Score=66.3` with **0.00 discrepancy**. The API and UI faithfully reflect this calculation.
3. **Root Cause Confirmed — Upstream Feature Sign Inversion in Multi-Competition Ingestion:**
   - In the approved production model design (`src/contribution_framework.py`, `models/contribution/phase7/PHASE7I_P3_EXTREME_CHASE_REPORT.md`, `src/phase7p_vaibhav_p3_chase_diagnostic.py`), `required_rr_change` is defined as:
     $$\text{required\_rr\_change} = RRR_{\text{entry}} - RRR_{\text{exit}} \quad (\text{positive} = \text{pressure relief, negative} = \text{pressure increase})$$
   - Across the entire IPL dataset (`data/processed/batter_match_contributions.csv`, 9,325 second-innings rows), **100.0%** of rows adhere to $RRR_{\text{entry}} - RRR_{\text{exit}}$. In IPL, when a batter drops RRR from 9.8 to 0.0, $\text{required\_rr\_change} = +9.80$.
   - In the multi-competition ingestion pipeline (`scripts/ingest_competition_data.py`, lines 365–369), the feature calculation was inadvertently written in reverse:
     $$\text{b\_row}["\text{required\_rr\_change}"] = \text{round}(rrr\_out - rrr\_in, 2) \quad (\text{i.e. } RRR_{\text{exit}} - RRR_{\text{entry}})$$
   - In Samson's row: $RRR_{\text{entry}} = 9.80$, $RRR_{\text{exit}} = 0.00$. The ingestion pipeline recorded $\text{required\_rr\_change} = -9.80$ and $\text{rr\_gap\_change} = -9.80$.
   - When the production P3 model processed this row, it interpreted $-9.80$ not as a complete elimination of chase pressure, but as a catastrophic **+9.80 RPO explosion in required run rate**! It applied the maximum negative chase penalty ($z_{\text{rrr}} = -2.4555$, $z_{\text{gap}} = -2.4555$), subtracting $1.84$ raw points from Samson's team impact.
4. **Impact of Correction:** When evaluated with the canonical IPL convention ($\text{required\_rr\_change} = +9.80$), Samson's P3 immediately rises from **37.2 to 96.9**, his Adjusted P3 rises from **37.4 to 96.1**, and his Final Contribution Score rises from **66.3 to 95.6**, matching historical elite chase benchmarks in the IPL (e.g., Steve Smith 94.4, Gautam Gambhir 97.5, Chris Lynn 97.4).
5. **Strict Safety Compliance:** No production code, models, CSV datasets, database tables, or integrity locks were modified during this investigation.

---

## 1. Match Identification and Source Records

The authoritative match record was identified and cross-verified across all layers of the system:

| Field | Source Value | Verification Source |
|---|---|---|
| **Match ID** | `1512770` | Cricsheet JSON & `matches.csv` |
| **Competition** | ICC Men's T20 World Cup | `matches.csv` / `1512770.json` info |
| **Match Details** | Match 52, Group/Super stage | `1512770.json` info |
| **Date** | 2026-03-01 | `1512770.json` dates: `["2026-03-01"]` |
| **Venue** | Eden Gardens, Kolkata | `1512770.json` info.venue |
| **Teams** | India vs West Indies | `1512770.json` info.teams |
| **Toss** | India, elected to field | `1512770.json` info.toss |
| **Innings 1** | West Indies: 195/4 in 20.0 overs | Deliveries 0.1 to 19.6 |
| **Innings 2** | India: 199/5 in 19.2 overs | Deliveries 0.1 to 19.2 |
| **Target** | 196 runs | $195 + 1$ |
| **Result** | India won by 5 wickets (4 balls remaining) | `1512770.json` info.outcome |
| **Player of Match**| SV Samson | `1512770.json` info.player_of_match |
| **Batter Identifier** | `SV Samson` (Sanju Samson) | `1512770.json` registry / roster |
| **Partition** | `data/processed/t20i/` | Independent T20I partition |
| **Record Row** | Row 31,696 in `data/processed/t20i/batter_match_contributions.csv` | Exact CSV row index |
| **API Endpoints** | `/api/match/1512770?competition=t20i`<br>`/api/match/1512770/player/SV%20Samson?competition=t20i` | FastMCP / FastAPI Service |

---

## 2. Verified Entry and Exit States from Raw Deliveries

Independent ball-by-ball reconstruction from `data/t20s_json/1512770.json`:

```
========================================================================================
SANJU SAMSON (SV SAMSON) INNINGS DELIVERIES BREAKDOWN
========================================================================================
Total match deliveries in Innings 2: 123 (116 legal balls, 6 wides, 1 no-ball)
Deliveries faced by SV Samson: 51 total (50 legal balls, 1 wide)
Statline: 97 runs off 50 legal balls (SR 194.00)
Boundary breakdown: 12 fours (48 runs), 4 sixes (24 runs) = 72 boundary runs (74.2%)
Non-boundary runs: 9 dots, 20 singles, 4 twos, 1 three (25 runs)
Dismissal status: NOT OUT
----------------------------------------------------------------------------------------
Entry State (Ball 0.1 / Over 0.0):
  - Team Score: 0/0 (0 runs, 0 wickets down, 10 wickets in hand)
  - Balls Remaining: 120 legal balls (20.0 overs)
  - Target: 196 runs
  - Runs Required: 196 runs
  - Required Run Rate (RRR): 196 / (120/6) = 9.80 RPO
----------------------------------------------------------------------------------------
Exit State (Over 19.2 / Legal ball 116):
  - Team Score: 199/5 (199 runs, 5 wickets down, 5 wickets in hand)
  - Partner dismissals during stay: 5
    * 2.1: Abhishek Sharma (c Powell b Joseph) — Team 27/1
    * 5.4: SA Yadav (c Pooran b Motie) — Team 62/2
    * 11.2: HH Pandya (b Russell) — Team 118/3
    * 14.6: TL Varma (c Hetmyer b Hosein) — Team 152/4
    * 17.5: AR Patel (b Joseph) — Team 178/5
  - Incoming non-striker at end: S Dube (27* off 14 balls)
  - Balls Remaining: 4 legal balls (0.4 overs)
  - Target: 196 runs
  - Runs Required: 0 runs (Target Reached & Exceeded)
  - Required Run Rate (RRR): 0.00 RPO
----------------------------------------------------------------------------------------
Terminal Delivery:
  - Over 19.2: Romario Shepherd to SV Samson
  - State before ball 19.2: 195/5, 5 balls rem, 1 run needed (target 196)
  - Delivery outcome: SV Samson hits FOUR runs!
  - Score updates to 199/5. Target is passed.
  - Innings ends immediately per T20 playing conditions.
========================================================================================
```

All raw values reconcile exactly with the display labels: 97 runs, 50 balls, SR 194.0, 12 fours, 4 sixes, 0/0 entry, 199/5 exit, 19.2 exit over, not out.

---

## 3. Current Stored Contribution Values

Values extracted directly from Row 31,696 of `data/processed/t20i/batter_match_contributions.csv`:

| Feature / Metric | Stored Value | Physical Meaning |
|---|---:|---|
| **Pillar 1 — Context Score (`score_context`)** | **47.7** | Average baseline entry pressure |
| **Pillar 2 — Batting Execution (`score_perf`)** | **95.9** | Elite execution (97 off 50 vs exp 62.5) |
| **Pillar 3 — Team-State Impact (`score_state`)** | **37.2** | Sub-par / negative team trajectory |
| **Adjusted P2 (`adjusted_p2`)** | **95.2** | $50.0 + (95.9 - 50.0) \times 0.9839$ |
| **Adjusted P3 (`adjusted_p3`)** | **37.4** | $50.0 + (37.2 - 50.0) \times 0.9839$ |
| **Context Leverage (`leverage`)** | **0.9839** | $1.0 + 0.35 \times ((47.7 - 50.0)/50.0)$ |
| **Final Contribution Score (`contribution_score`)** | **66.3** | $0.50 \times 95.16 + 0.50 \times 37.42$ |
| **Raw Contribution (`raw_contribution`)** | **66.5** | $0.50 \times 95.9 + 0.50 \times 37.2$ |
| **Actual Runs (`actual_runs`)** | **97** | Batter runs |
| **Expected Runs (`expected_runs`)** | **62.5** | Baseline expected runs for 50 balls |
| **Run Deviation (`run_deviation`)** | **+34.5** | Excess runs over expectation |
| **Actual Strike Rate (`actual_sr`)** | **194.0** | Batter strike rate |
| **Expected Strike Rate (`expected_sr`)** | **125.0** | Baseline expected strike rate |
| **SR Deviation (`sr_deviation`)** | **+69.0** | Excess strike rate |
| **Balls Faced (`balls_faced`)** | **50** | Legal deliveries faced |
| **Team Score Entry / Exit** | **0 / 199** | Complete match stay |
| **Balls Remaining Entry / Exit** | **120 / 4** | 20.0 overs to 0.4 overs remaining |
| **Wickets Remaining Entry / Exit** | **10 / 5** | 0 to 5 wickets lost |
| **Wicket Resource Change (`wicket_resource_change`)** | **-5** | 5 partner wickets lost |
| **Target (`target`)** | **196.0** | Innings 2 target |
| **Required RR Entry (`required_rr_entry`)** | **9.80** | $196 / (120/6)$ |
| **Required RR Exit (`required_rr_exit`)** | **0.00** | $0 / (4/6)$ |
| **Required RR Change (`required_rr_change`)** | **-9.80** | **STORED SIGN INVERSION** ($0.00 - 9.80$) |
| **RR Gap Change (`rr_gap_change`)** | **-9.80** | Set equal to `required_rr_change` |
| **Target Progress Change (`target_progress_change`)** | **+1.015** | $199/196 - 0/196$ |
| **Attribution Category (`attribution_category`)** | `NONE` | Phase 7U Model T |
| **Attribution Gamma (`attribution_gamma`)** | `1.0` | No 1st-innings collapse attribution |

---

## 4. Fresh Production Calculation Comparison

The stored row was passed directly to `compute_production_contribution(row, apply_attribution=True)`:

```python
fresh = compute_production_contribution(row, apply_attribution=True)
```

### Reconciliation Table:

| Metric | Stored CSV Value | Fresh Computation | Discrepancy |
|---|---:|---:|---:|
| Pillar 1 (Context) | 47.7 | 47.7 | 0.0 |
| Pillar 2 (Performance) | 95.9 | 95.9 | 0.0 |
| Pillar 3 (Team-State) | 37.2 | 37.2 | 0.0 |
| Context Leverage | 0.9839 | 0.9839 | 0.0000 |
| Adjusted P2 | 95.2 | 95.16 (rounds to 95.2) | 0.0 |
| Adjusted P3 | 37.4 | 37.42 (rounds to 37.4) | 0.0 |
| Final Contribution | 66.3 | 66.29 (rounds to 66.3) | 0.0 |

**Conclusion:** The production framework code reproduces the stored record with **100% precision**. There is zero drift, caching divergence, or post-processing mutation between `src/contribution_framework.py` and the stored dataset.

---

## 5. API and UI Comparison

Inspection of the backend API service (`app/services/data_service.py`) and live API response:

- **Endpoint:** `GET /api/match/1512770?competition=t20i`
- **Batter Object:**
  ```json
  {
    "player": "SV Samson",
    "innings": 2,
    "runs": 97,
    "balls": 50,
    "strike_rate": 194.0,
    "contribution_score": 66.3,
    "pillar1_context": 47.7,
    "pillar2_perf": 95.9,
    "pillar3_state": 37.2,
    "adjusted_p2": 95.2,
    "adjusted_p3": 37.4,
    "leverage": 0.984,
    "expected_runs": 62.5,
    "expected_sr": 125.0
  }
  ```
- **Match Page Display:**
  The frontend UI displays the exact same values:
  - Contribution Score: **66.3**
  - Performance (P2): **95.2**
  - Impact (P3): **37.4**
  - Match Context (P1): **47.7**

**Conclusion:** The database, API layer, and frontend display are 100% aligned. The discrepancy originates entirely within the feature generation pipeline.

---

## 6. Audit of Expected-Runs and Expected-Strike-Rate Baselines

The baseline expectations for Samson are:
$$\text{Expected Runs} = 62.5 \quad \text{for } 50 \text{ balls faced}$$
$$\text{Expected Strike Rate} = 125.0$$

### Mathematical & Methodological Verification:
1. **Consistency:** $\frac{62.5}{50} \times 100 = 125.0$. The expected runs and expected strike rate are in exact agreement.
2. **Opportunity Scope:** The model predicts expected runs for the **50 balls actually faced by Samson**, not the full 120-ball innings. This conforms with the project's established individual opportunity definition.
3. **No Look-Ahead Information Leakage:** The entry features reflect $0.0$ overs, $0/0$, target $196$, 10 wickets in hand, and 120 balls remaining. At 0.0 overs against a 196 target, a top-order batter in T20 cricket is expected to score at approximately $7.50$ RPO (SR 125.0).
4. **Performance Delta:**
   $$\text{Run Deviation} = 97 - 62.5 = +34.5 \text{ runs}$$
   $$\text{SR Deviation} = 194.0 - 125.0 = +69.0 \text{ SR}$$
   This $+34.5$ run surplus over 50 balls ranks in the 99th percentile, yielding the elite P2 score of **95.9**.

The P2 baseline calculation is completely verified and methodologically sound.

---

## 7. Audit of Completed-Chase and Required Run Rate Handling

This is the pivotal section of the audit.

### 7.1. Physical Reality vs. Data Representation
In cricket, a chase begins with a required run rate determined by the target:
$$RRR_{\text{entry}} = \frac{196 - 0}{120 / 6} = 9.80 \text{ RPO}$$
When India reached 199/5 on ball 19.2, the target was achieved:
$$\text{Runs Required}_{\text{exit}} = \max(0, 196 - 199) = 0$$
$$\text{Balls Remaining}_{\text{exit}} = 4$$
$$RRR_{\text{exit}} = \frac{0}{4 / 6} = 0.00 \text{ RPO}$$

During Samson's stay, the team went from needing **9.80 runs per over** to needing **0.00 runs per over**. The required run rate dropped by **9.80 RPO**, representing **100% elimination of chase pressure**.

### 7.2. The Canonical Definition in Model Design
In the production contribution architecture documentation (`PHASE7I_P3_EXTREME_CHASE_REPORT.md` line 54) and the diagnostic calibration suite (`phase7p_vaibhav_p3_chase_diagnostic.py` lines 837–838, `phase7t_p3_wicket_causality_diagnostic.py` line 400):
> *"Because required_rr_change is defined as RRR_entry - RRR_exit (positive = relief), the UI erroneously displayed negative... "*
> *"required_rr_change = sc['rrr_entry'] - sc['rrr_exit']"*

When RRR falls from 9.80 to 0.00:
$$\Delta RRR_{\text{canonical}} = RRR_{\text{entry}} - RRR_{\text{exit}} = 9.80 - 0.00 = \mathbf{+9.80} \quad (\text{Relief})$$

### 7.3. The Implementation in the Ingestion Pipeline
In `scripts/ingest_competition_data.py` (lines 358–369):
```python
if innings_num == 2 and target_runs:
    req_entry = max(1.0, target_runs - ent["team_score"])
    req_exit = max(0.0, target_runs - ex["team_score"])
    rrr_in = round(req_entry / (ent["balls_rem"] / 6.0), 2) if ent["balls_rem"] > 0 else 9.0
    rrr_out = round(req_exit / (ex["balls_rem"] / 6.0), 2) if ex["balls_rem"] > 0 else (0.0 if req_exit == 0 else 36.0)
    b_row["required_rr_entry"] = rrr_in
    b_row["required_rr_exit"] = rrr_out
    b_row["required_rr_change"] = round(rrr_out - rrr_in, 2)     # <--- INVERTED SIGN!
    b_row["rr_gap_entry"] = round(rrr_in - ent["team_rr"], 2)
    b_row["rr_gap_exit"] = round(rrr_out - ex["team_rr"], 2)
    b_row["rr_gap_change"] = b_row["required_rr_change"]         # <--- INVERTED SIGN!
```

Line 365 explicitly computes:
$$\text{required\_rr\_change} = rrr\_out - rrr\_in = 0.00 - 9.80 = \mathbf{-9.80}$$

### 7.4. Population Invariant Audit Across Partitions

An automated population audit of all second-innings records across partitions confirms this systemic inversion:

| Dataset Partition | Total Innings 2 Rows | Rows following $RRR_{\text{entry}} - RRR_{\text{exit}}$ | Rows following $RRR_{\text{exit}} - RRR_{\text{entry}}$ | Convention Consistency |
|---|---:|---:|---:|:---:|
| **IPL** (`batter_match_contributions.csv`) | 9,325 | **9,325 (100.0%)** | 0 (0.0%) | **Canonical** |
| **T20I** (`t20i/batter_match_contributions.csv`) | 17,258 | 0 (0.0%) | **17,258 (100.0%)** | **Inverted** |
| **SMAT** (`smat/batter_match_contributions.csv`) | 657 | 0 (0.0%) | **657 (100.0%)** | **Inverted** |

**Conclusion:** The IPL dataset uses the canonical convention $RRR_{\text{entry}} - RRR_{\text{exit}}$. However, when the multi-competition ingestion pipeline (`scripts/ingest_competition_data.py`) was constructed for T20I and SMAT, `required_rr_change` was accidentally defined as `rrr_out - rrr_in`. Every successful chase in T20I is systematically inverted.

---

## 8. Step-by-Step P3 Numerical Reconstruction

Here we trace the exact mathematical execution inside `compute_dampened_p3_raw` in `src/contribution_framework.py`.

### 8.1. Parameter Calculation:
1. **Entry State:**
   - $B_{\text{rem}} = 120$
   - $W_{\text{rem}} = 10$
   - $RRR_{\text{entry}} = 9.80$
2. **Chase Feasibility ($F_{\text{chase}}$):**
   $$V_{\text{max}} = 12.0 + 3.0 \times \tanh\left(\frac{10 - 3.5}{2.0}\right) + 4.0 \times \left(\frac{12.0}{120 + 6.0}\right) = 12.0 + 2.972 + 0.381 = 15.353 \text{ RPO}$$
   $$\rho = \frac{9.80}{\max(6.0, 15.353)} = \frac{9.80}{15.353} = 0.6383$$
   $$F_{\text{chase}} = \frac{1}{1 + \exp(4.0 \times (0.6383 - 1.25))} = \frac{1}{1 + \exp(-2.4468)} = 0.9206$$
3. **Dynamic Penalty Cap:**
   $$\text{cap} = 6.0 + 4.0 \times 0.9206 - 0.2 \times \max(0, 9.80 - 6.0) = 6.0 + 3.6824 - 0.760 = 8.922 \to \text{clipped to } 9.5233$$

---

### 8.2. Branch A: Current Execution with Inverted Sign ($\text{rrr\_chg} = -9.80$)

1. **Effective RRR Shift ($r_{\text{eff}}$):**
   $$r_{\text{eff}} = -9.5233 \times \tanh\left(\frac{9.80}{9.5233}\right) = -9.5233 \times 0.7735 = -7.3666$$
2. **Z-Scores:**
   $$z_{\text{rrr}} = \frac{-7.3666}{3.0} = \mathbf{-2.4555}$$
   $$z_{\text{gap}} = \frac{-7.3666}{3.0} = \mathbf{-2.4555}$$
   $$z_{\text{prog}} = \frac{1.015 - 0.15}{0.15} = \frac{0.865}{0.15} = \mathbf{+5.7667}$$
3. **Dynamic Wicket Resource Impact ($S_{\text{res}}$):**
   $$W_{\text{lost}} = 5, \quad B_{\text{exit}} = 4, \quad W_{\text{exit}} = 5$$
   $$C_w = 0.05 \times \left(1.0 + \frac{4}{60.0}\right) \times \left(1.0 + 0.5 \times \left(\frac{5 - 5}{5.0}\right)\right) = 0.0533$$
   $$d_w = \exp\left(-\frac{50}{15.0}\right) = 0.0357$$
   $$S_{\text{res}} = -5 \times 0.0533 \times 0.0357 \times \tanh(0.74) = \mathbf{-0.0071}$$
4. **Raw P3:**
   $$\text{P3}_{\text{raw}} = 0.50 \times (-2.4555) + 0.25 \times (-2.4555) + 0.25 \times (+5.7667) - 0.0071$$
   $$\text{P3}_{\text{raw}} = -1.2278 - 0.6139 + 1.4417 - 0.0071 = \mathbf{-0.4071}$$
5. **Standardization to P3 Score:**
   $$z_3 = \frac{\text{P3}_{\text{raw}} - \mu_3}{\sigma_3} = \frac{-0.4071 - 0.159}{1.513} = \frac{-0.5661}{1.513} = \mathbf{-0.3742}$$
   $$\text{P3} = \frac{100}{1 + \exp(-1.40 \times (-0.3742))} = \frac{100}{1 + \exp(+0.5238)} = \frac{100}{2.6885} = \mathbf{37.2}$$
6. **Adjusted P3 & Final Score:**
   $$\text{Adjusted P3} = 50.0 + (37.19 - 50.0) \times 0.9839 = 50.0 - 12.58 = \mathbf{37.4}$$
   $$\text{Final Contribution} = 0.50 \times 95.16 + 0.50 \times 37.42 = 47.58 + 18.71 = \mathbf{66.3}$$

**Summary of Failure:** The model assigns a **-1.84 raw point penalty** for RRR change because it believes Samson increased the required run rate by 9.80 RPO!

---

### 8.3. Branch B: Execution with Canonical IPL Sign ($\text{rrr\_chg} = +9.80$)

Now evaluate the exact same formula with the correct relief sign:

1. **Effective RRR Shift ($r_{\text{eff}}$):**
   $$r_{\text{eff}} = +9.5233 \times \tanh\left(\frac{9.80}{9.5233}\right) = +7.3666$$
2. **Z-Scores:**
   $$z_{\text{rrr}} = \frac{+7.3666}{3.0} = \mathbf{+2.4555}$$
   $$z_{\text{gap}} = \frac{+7.3666}{3.0} = \mathbf{+2.4555}$$
   $$z_{\text{prog}} = \frac{1.015 - 0.15}{0.15} = \mathbf{+5.7667}$$
3. **Dynamic Wicket Resource Impact ($S_{\text{res}}$):**
   $$S_{\text{res}} = \mathbf{-0.0071}$$
4. **Raw P3:**
   $$\text{P3}_{\text{raw}} = 0.50 \times (+2.4555) + 0.25 \times (+2.4555) + 0.25 \times (+5.7667) - 0.0071$$
   $$\text{P3}_{\text{raw}} = +1.2278 + 0.6139 + 1.4417 - 0.0071 = \mathbf{+3.2764}$$
5. **Standardization to P3 Score:**
   $$z_3 = \frac{+3.2764 - 0.159}{1.513} = \frac{+3.1174}{1.513} = \mathbf{+2.0604}$$
   $$\text{P3} = \frac{100}{1 + \exp(-1.40 \times (+2.0604))} = \frac{100}{1 + \exp(-2.8846)} = \frac{100}{1.05588} = \mathbf{96.9}$$
6. **Adjusted P3 & Final Score:**
   $$\text{Adjusted P3} = 50.0 + (96.90 - 50.0) \times 0.9839 = 50.0 + 46.15 = \mathbf{96.1}$$
   $$\text{Final Contribution} = 0.50 \times 95.16 + 0.50 \times 96.15 = 47.58 + 48.07 = \mathbf{95.6}$$

---

### Comparison of Current vs. Canonical Valuation:

| Metric | Current Inverted Ingestion | Canonical Model Specification | Delta |
|---|---:|---:|---:|
| $z_{\text{rrr}}$ (RRR relief component) | -2.4555 | +2.4555 | +4.9110 |
| $z_{\text{gap}}$ (RR gap component) | -2.4555 | +2.4555 | +4.9110 |
| $z_{\text{prog}}$ (Target progress) | +5.7667 | +5.7667 | 0.0000 |
| Raw P3 | -0.4071 | +3.2764 | +3.6835 |
| **Pillar 3 (State Impact)** | **37.2** | **96.9** | **+59.7** |
| Adjusted P3 | 37.4 | 96.1 | +58.7 |
| Adjusted P2 | 95.2 | 95.2 | 0.0 |
| **Final Contribution Score** | **66.3** | **95.6** | **+29.3** |

---

## 9. Check the P1 Context Leverage Calculation

The historical report showed P1 = 47.7 and leverage $L = 0.9839$.

### Verification:
1. **Entry Components:**
   - Wicket context: $C_{\text{wkt}} = 35.0$ (10 wickets in hand, low pressure)
   - Chase context: $C_{\text{chase}} = 63.3$ (RRR 9.80, moderate pressure)
   - Opening context: $C_{\text{open}} = 38.0$ (over 0.0, low pressure)
   - Blended Context: $C_{\text{eff}} = 0.20 \times 35.0 + 0.60 \times 63.3 + 0.20 \times 38.0 = 7.0 + 38.0 + 7.6 = \mathbf{47.7}$
2. **Leverage Formula:**
   $$L(P1) = 1.0 + 0.35 \times \left(\frac{P1 - 50.0}{50.0}\right) = 1.0 + 0.35 \times \left(\frac{47.7 - 50.0}{50.0}\right) = 1.0 - 0.0161 = \mathbf{0.9839}$$
3. **Properties Verified:**
   - Clipping bounds: $L \in [0.65, 1.35]$ (satisfied).
   - Par Invariance: If $P1 = 50.0 \implies L = 1.0000$ (satisfied).
   - Equal Application: Both P2 and P3 are modulated by the identical multiplier $0.9839$.
   - No Double-Counting: No secondary context adjustment exists in the pipeline.

The P1 calculation and leverage damping are functioning strictly as intended.

---

## 10. Comparison of Phase 7Q and Phase 7U

Phase 8 migrated stored records to align with Phase 7U Model T wicket-causality attribution.

### Audit of Phase 7U Attribution for Samson's Innings:
- **Phase 7U Model T Scope:** Attribution specifically targets **first-innings batting collapses** where rapid succession of partner dismissals suppresses the team's projected final score ($EFS$). It dynamically scales attribution weight $\gamma$ based on batter strike rate and partner dot-ball pressure.
- **Second-Innings Chases:** In chases, team-state impact is governed by the dampened RRR mechanism (`compute_dampened_p3_raw`) rather than $EFS$ projection.
- **Dynamic Wicket Cost:** In second-innings chases, partner dismissals enter through the dynamic resource cost $S_{\text{res}}$. Because Samson batted until the chase was completed (4 balls remaining), the marginal value of unused wickets at exit was essentially zero ($d_w = 0.0357$), resulting in a trivial cost of $S_{\text{res}} = -0.0071$.
- **Attribution Trigger:** `attribution_category` is evaluated as `NONE`, and $\gamma = 1.0$.

**Conclusion:** Phase 7U attribution has **zero delta** compared to Phase 7Q for this match. Samson's score was neither helped nor hurt by Phase 8's Phase 7U alignment.

---

## 11. Regression and Invariant Checks

### 11.1. Full Repository Test Suite Status
The full repository test suite was executed:
- **Test Command:** `.venv\Scripts\pytest.exe`
- **Result:** **527 passed in 38.64s**
- **Failures:** 0
- **Errors:** 0

### 11.2. Comparison with Completed Chases in IPL
In the IPL partition, where $RRR_{\text{entry}} - RRR_{\text{exit}}$ is correctly signed positive for relief, comparable masterclass chases receive elite P3 scores:

| Batter | Match | Chase Statline | Entry RRR | Exit RRR | $\Delta RRR$ | P2 Score | P3 Score | Contribution Score |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **Steve Smith** | RPS vs KKR 2016 | 101* (54) | 9.4 | 0.0 | +9.4 | 94.6 | **94.4** | **94.5** |
| **Gautam Gambhir** | KKR vs GL 2017 | 93* (51) | 9.2 | 0.0 | +9.2 | 96.1 | **97.5** | **96.8** |
| **Chris Lynn** | KKR vs GL 2017 | 93* (41) | 9.2 | 0.0 | +9.2 | 97.8 | **97.4** | **97.6** |
| **David Warner** | SRH vs GL 2016 | 93* (58) | 8.2 | 0.0 | +8.2 | 95.2 | **95.9** | **95.6** |
| **Glenn Maxwell** | KXIP vs CSK 2014 | 95 (43) | 10.3 | 4.8 | +5.5 | 98.4 | **93.1** | **95.8** |
| **Sanju Samson (Current T20I)** | IND vs WI 2026 | 97* (50) | 9.8 | 0.0 | **-9.8** (err) | 95.9 | **37.2** (err) | **66.3** (err) |
| **Sanju Samson (Corrected)** | IND vs WI 2026 | 97* (50) | 9.8 | 0.0 | **+9.8** | 95.9 | **96.9** | **95.6** |

In all historical IPL chases of equivalent caliber, the model scores P3 between **93.0 and 97.5**. Samson's P3 of 37.2 is a dramatic statistical anomaly caused solely by the feature sign inversion.

### 11.3. Collateral Damage on Other Batters in the Same Match
The inversion also corrupted other batters in the same match:
- **Shivam Dube:** 27* off 14 balls (SR 192.9), entered at 152/4 (RRR 10.20), finished not out at 199/5 (RRR 0.00).
- Stored `required_rr_change`: $-10.20$.
- Resulting P3: **13.0**!
- Despite scoring 27* off 14 to close out a World Cup chase, Dube received a P3 score in the 13th percentile because the model evaluated him as blowing the required run rate by +10.2 RPO.

---

## 12. Confirmed Bugs vs. Valid Model Behavior

| Component | Status | Explanation |
|---|---|---|
| **Production Model Formula (`src/contribution_framework.py`)** | **VALID** | The formula correctly implements feasibility-dampened chase dynamics. It expects positive $\Delta RRR$ for relief and correctly bounds extreme scenarios. |
| **P1 Context & Leverage Formula** | **VALID** | Formula preserves bounds $[0.65, 1.35]$ and par invariance at $P1=50.0$. |
| **Phase 7U Model T Attribution Engine** | **VALID** | Works as specified for collapse attribution; correctly neutral for chases. |
| **API & Web Presentation Layer** | **VALID** | Correctly delivers and renders stored and calculated values. |
| **Ingestion Pipeline (`scripts/ingest_competition_data.py`)** | **CONFIRMED BUG** | Lines 365–369 compute $rrr\_out - rrr\_in$ instead of $rrr\_in - rrr\_out$. This inverts the sign of every second-innings chase metric across T20I and SMAT datasets. |

---

## 13. Recommended Correction (For Future Implementation)

While this forensic audit is strictly read-only, we provide the exact correction plan to resolve the issue across the multi-competition datasets:

### Proposed Fix:
1. **Patch `scripts/ingest_competition_data.py` (Line 365):**
   ```python
   # Current (Inverted):
   b_row["required_rr_change"] = round(rrr_out - rrr_in, 2)
   
   # Corrected (Canonical):
   b_row["required_rr_change"] = round(rrr_in - rrr_out, 2)
   ```
2. **Propagate to Dependent Relief Features (Lines 368–369):**
   Ensure `rr_gap_change` and `chase_pressure_relief_rr` inherit the corrected `required_rr_change`.
3. **Regenerate T20I and SMAT Datasets:**
   Run the ingestion pipeline to refresh `data/processed/t20i/` and `data/processed/smat/` partitions.
4. **Re-Verify Samson Record:**
   Confirm that Samson's record in `data/processed/t20i/batter_match_contributions.csv` updates to:
   - $P1 = 47.7$
   - $P2 = 95.9$
   - $P3 = 96.9$
   - $\text{Adjusted } P2 = 95.2$
   - $\text{Adjusted } P3 = 96.1$
   - $\text{Contribution Score} = 95.6$

---

## 14. Files Inspected and Safety Certification

### Files Inspected:
1. `data/t20s_json/1512770.json` (Raw Cricsheet ball-by-ball delivery data)
2. `data/processed/t20i/matches.csv` (Processed match metadata)
3. `data/processed/t20i/batter_match_contributions.csv` (Stored T20I contributions)
4. `data/processed/batter_match_contributions.csv` (Stored IPL contributions)
5. `data/processed/smat/batter_match_contributions.csv` (Stored SMAT contributions)
6. `scripts/ingest_competition_data.py` (Multi-competition ingestion pipeline)
7. `scripts/regenerate_production_pipeline.py` (IPL regeneration pipeline)
8. `src/contribution_framework.py` (Production contribution engine)
9. `src/phase7u_p3_wicket_causality.py` (Attribution engine)
10. `models/contribution/phase7/PHASE7I_P3_EXTREME_CHASE_REPORT.md` (P3 model specification)
11. `src/phase7p_vaibhav_p3_chase_diagnostic.py` (P3 chase diagnostic calibration)
12. `app/services/data_service.py` (Backend API service)
13. `frontend/src/pages/MatchContributionPage.jsx` (Frontend UI rendering)

### Safety Certification:
In strict compliance with the audit instructions:
- **Zero production scoring formulas, weights, or leverage thresholds were altered.**
- **Zero trained ML models or baseline scalers were modified.**
- **Zero processed CSVs, database tables, or raw JSON data files were modified.**
- **Zero integrity locks were bypassed.**
- **Zero automated regeneration commands were executed.**
- This audit remains 100% read-only.
