import React from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Calculator,
  Compass,
  Zap,
  TrendingUp,
  ShieldCheck,
  Scale,
  Activity,
  Layers,
  CheckCircle2,
  Code2,
  Database,
  Sliders,
} from 'lucide-react';

export default function Methodology() {

  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* Page Header */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold bg-[#101010] text-[#D4AF57] border border-[#D4AF57]/40 tracking-wider">
              Mathematical model specification
            </span>
            <span className="text-[12px] font-mono text-[#858585]">Production Phase 7U</span>
          </div>
          <h1 className="font-heading text-[30px] sm:text-[34px] lg:text-[36px] font-bold text-[#F2F2F2] mt-2.5 tracking-wider leading-tight">
            How the Contribution Score is calculated
          </h1>
          <p className="text-[15px] sm:text-[16px] text-[#B8B8B8] mt-2 max-w-3xl leading-relaxed font-normal">
            The complete mathematical and statistical methodology governing the Cricket Batter Contribution Model. Trace the calculation pipeline from raw ball-by-ball match state to final contextual scores without simplified approximations.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto shrink-0">
          <Link
            to="/about"
            className="px-4 py-2.5 rounded-lg bg-[#101010] text-[#F2F2F2] hover:bg-[#202020] border border-[#2D2D2D] text-[13px] sm:text-[13.5px] font-semibold transition-colors flex items-center gap-2"
          >
            <BookOpen className="w-4 h-4 text-[#D4AF57]" />
            <span>Cricket intuition (About)</span>
          </Link>
          <Link
            to="/dashboard"
            className="px-4 py-2.5 rounded-lg bg-[#D4AF57] text-[#080808] hover:bg-[#E1C878] text-[13px] sm:text-[13.5px] font-bold shadow-xs transition-colors flex items-center gap-2"
          >
            <Activity className="w-4 h-4" />
            <span>Explore dashboard</span>
          </Link>
        </div>
      </div>

      {/* Pipeline Architecture Banner */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <div className="border-b border-[#2D2D2D] pb-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Layers className="w-5 h-5 text-[#D4AF57]" />
              End-to-end calculation flow
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Strict deterministic data flow from match telemetry to normalized contribution scores.
            </p>
          </div>
          <span className="text-[12px] font-mono text-[#858585] bg-[#101010] px-3 py-1 rounded border border-[#2D2D2D] self-start sm:self-auto">
            Single Source of Truth: src/contribution_framework.py
          </span>
        </div>

        {/* 7-Step Pipeline Diagram */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2.5 text-xs pt-2">
          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 1</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">Raw match data</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Balls, runs, wickets, overs, and targets.</p>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 2</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">Context features</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Wicket crisis, chase demand, entry phase.</p>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 3</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">P1 Context</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Bounded leverage signal L(P1) in [0.65, 1.35].</p>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 4</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">Expected baseline</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Situational E[Runs] & E[SR] models.</p>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 5</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">P2 Execution</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Run & SR deviation normalized to 0-100.</p>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D]">
            <div className="text-[11px] font-semibold text-[#858585] font-mono">Step 6</div>
            <div className="font-semibold text-[#F2F2F2] mt-0.5 text-[13px]">P3 State impact</div>
            <p className="text-[11px] text-[#858585] mt-1 font-normal">Attributable delta EFS with preservation floor.</p>
          </div>

          <div className="bg-[#161616] p-3 rounded-lg border border-[#D4AF57]/40">
            <div className="text-[11px] font-bold text-[#D4AF57] font-mono">Step 7</div>
            <div className="font-bold text-[#D4AF57] mt-0.5 text-[13px]">Final contribution</div>
            <p className="text-[11px] text-[#E1C878] mt-1 font-normal">0.50 × Adj P2 + 0.50 × Adj P3.</p>
          </div>
        </div>
      </div>

      {/* SECTION 1 & 2: RAW INPUTS & FEATURE CONSUMPTION */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Database className="w-5 h-5 text-[#D4AF57]" />
              1. Raw model inputs
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Features strictly consumed by the production calculation engine in <code className="text-[#D4AF57] font-mono">src/contribution_framework.py</code>.
            </p>
          </div>
          <span className="text-[12px] text-[#858585] bg-[#101010] px-3 py-1 rounded border border-[#2D2D2D] font-mono font-medium self-start sm:self-auto">
            Zero outcome leakage
          </span>
        </div>

        <p className="text-[14px] sm:text-[15px] text-[#B8B8B8] leading-relaxed font-normal">
          The model does not consume arbitrary statistics. Every feature corresponds strictly to the state observable at the point of action. Historical win results, post-match summaries, and future ball outcomes are strictly barred from the inputs.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-[13.5px] sm:text-[14px]">
          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-3">
            <div className="font-semibold text-[#D4AF57] text-[13.5px] sm:text-[14px]">
              Batter execution features
            </div>
            <ul className="space-y-1.5 text-[#B8B8B8] text-[13px] sm:text-[13.5px]">
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">actual_runs</code>: Total runs scored off the bat</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">balls_faced</code>: Legal deliveries faced</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">actual_sr</code>: Strike rate (runs per 100 balls)</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">fours, sixes</code>: Boundary volume</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">dot_balls, dot_ball_percentage</code>: Delivery-level non-scoring rate</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">dismissal_status</code>: Out vs. Not Out</li>
            </ul>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-3">
            <div className="font-semibold text-[#D4AF57] text-[13.5px] sm:text-[14px]">
              Match state & entry resources
            </div>
            <ul className="space-y-1.5 text-[#B8B8B8] text-[13px] sm:text-[13.5px]">
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">entry_over, exit_over</code>: Exact crease stay window</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">innings</code>: 1st (setting) or 2nd (chasing)</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">team_score_entry, team_score_exit</code>: Team score progression</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">wickets_remaining_entry / exit</code>: Wickets in hand</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">balls_remaining_entry / exit</code>: Deliveries remaining</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">wickets_lost_during_stay</code>: Total dismissals in window</li>
            </ul>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-3">
            <div className="font-semibold text-[#D4AF57] text-[13.5px] sm:text-[14px]">
              Situational & chase demands
            </div>
            <ul className="space-y-1.5 text-[#B8B8B8] text-[13px] sm:text-[13.5px]">
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">expected_runs, expected_sr</code>: Baseline expectations</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">expected_final_entry / exit</code>: Projected team final total</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">target, runs_required_entry / exit</code>: Chase target parameters</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">required_rr_entry / exit</code>: Required run rate trajectory</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">partnership_runs, partner_runs</code>: Tandem production</li>
              <li>• <code className="font-mono font-semibold text-[#F2F2F2]">batter_partnership_share</code>: Share of partnership runs</li>
            </ul>
          </div>
        </div>
      </div>

      {/* SECTION 3: EXPECTED BATTER PERFORMANCE */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
            <Sliders className="w-5 h-5 text-[#D4AF57]" />
            2. Expected batter performance models
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
            Statistical situational expectations answering: "What would normally be expected from a batter in this exact match state?"
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-[14px] text-[#F2F2F2]">
          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-3.5">
            <div className="text-[14px] font-semibold text-[#D4AF57]">
              Expected runs: E[Runs]
            </div>
            <div className="font-mono bg-[#080808] p-3.5 rounded border border-[#2D2D2D] text-[#F2F2F2] text-[13px]">
              <span className="text-[#D4AF57]">E[Runs]</span> = f(Entry Over, Wickets Remaining, Balls Remaining, Innings)
            </div>
            <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              Derived empirically from historical T20 distributions for batters entering with the identical number of remaining overs and wickets in hand. An opener entering in over 0.1 with 10 wickets has an E[Runs] ~28-30, whereas a death-over finisher entering in over 18.0 with 4 wickets has an E[Runs] ~8-12.
            </p>
            <div className="pt-2.5 border-t border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585]">
              <strong className="text-[#F2F2F2]">Cricket meaning:</strong> Expected runs establish the baseline scoring hurdle before rewarding positive execution.
            </div>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-3.5">
            <div className="text-[14px] font-semibold text-[#D4AF57]">
              Expected strike rate: E[SR]
            </div>
            <div className="font-mono bg-[#080808] p-3.5 rounded border border-[#2D2D2D] text-[#F2F2F2] text-[13px]">
              <span className="text-[#D4AF57]">E[SR]</span> = f(Phase, Target Demands, Team Run Rate Baseline)
            </div>
            <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              Expected strike rate accounts for phase tempo demands. Powerplay baselines center around 115-125 SR against the new ball; death-over expectations escalate to 160-185 SR where field restrictions and delivery risk reward maximal boundary aggression.
            </p>
            <div className="pt-2.5 border-t border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585]">
              <strong className="text-[#F2F2F2]">Cricket meaning:</strong> Strike rate is evaluated relative to phase requirements, preventing powerplay consolidation from being penalized by death-over standards.
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 4 & 5: P1 CONTEXT & P2 BATTING EXECUTION */}
      {/* SECTION 4 & 5: P1 CONTEXT & P2 BATTING EXECUTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* P1 Context */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] space-y-4">
          <div className="border-b border-[#2D2D2D] pb-3.5">
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Compass className="w-5 h-5 text-[#D4AF57]" />
              3. P1 — Match context & leverage signal
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Evaluates situational difficulty and converts it into a multiplier.
            </p>
          </div>

          <div className="space-y-3.5 text-[14px]">
            <div className="bg-[#080808] p-4 rounded-lg border border-[#2D2D2D] space-y-2 font-mono text-[12.5px] sm:text-[13px]">
              <div className="text-[#858585]">// Effective context score</div>
              <div><span className="text-[#D4AF57]">C_eff</span> = w_wkt × C_wkt + (1 - w_wkt) × C_chase</div>
              <div className="text-[#858585]">// Linear bounded leverage</div>
              <div>dev = (C_eff - 50.0) / 50.0</div>
              <div><span className="text-[#D4AF57]">L(P1)</span> = clip(1.0 + 0.35 × dev, 0.65, 1.35)</div>
            </div>

            <div className="space-y-2 text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              <p>
                <strong className="text-[#F2F2F2]">Variable definitions:</strong>
              </p>
              <ul className="space-y-1.5 list-disc list-inside">
                <li><code className="font-mono text-[#D4AF57]">C_wkt</code>: Wicket collapse crisis signal (0–100) based on wickets remaining vs. balls remaining.</li>
                <li><code className="font-mono text-[#D4AF57]">C_chase</code>: Required run rate pressure in 2nd innings chases.</li>
                <li><code className="font-mono text-[#D4AF57]">L(P1)</code>: Context leverage multiplier strictly bounded between <code className="font-mono font-bold text-[#D4AF57]">0.65×</code> and <code className="font-mono font-bold text-[#D4AF57]">1.35×</code>.</li>
              </ul>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585] leading-relaxed">
              <strong className="text-[#F2F2F2]">Cricket meaning:</strong> High-pressure entries (e.g. 20/3 in a chase) generate leverage &gt; 1.0×, amplifying rewards for successful counter-attacks. Low-pressure dead-rubbers dampen scores toward par.
            </div>
          </div>
        </div>

        {/* P2 Batting Execution */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] space-y-4">
          <div className="border-b border-[#2D2D2D] pb-3.5">
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Zap className="w-5 h-5 text-[#D4AF57]" />
              4. P2 — Batting execution
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Individual execution performance relative to situational expectations.
            </p>
          </div>

          <div className="space-y-3.5 text-[14px]">
            <div className="bg-[#080808] p-4 rounded-lg border border-[#2D2D2D] space-y-2 font-mono text-[12.5px] sm:text-[13px]">
              <div className="text-[#858585]">// Standardized deviations</div>
              <div><span className="text-[#D4AF57]">Delta_R</span> = actual_runs - expected_runs</div>
              <div><span className="text-[#D4AF57]">Delta_SR</span> = actual_sr - expected_sr</div>
              <div><span className="text-[#D4AF57]">z_ind</span> = (Delta_R / 14.5) + 0.5 × (Delta_SR / 48.0) × sqrt(opp_usage)</div>
              <div><span className="text-[#D4AF57]">P2</span> = clip(100.0 / (1.0 + exp(-1.4 × z_ind)), 0.1, 99.9)</div>
            </div>

            <div className="space-y-2 text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              <p>
                <strong className="text-[#F2F2F2]">Variable definitions:</strong>
              </p>
              <ul className="space-y-1.5 list-disc list-inside">
                <li><code className="font-mono text-[#D4AF57]">Delta_R</code>: Run deviation above or below situational baseline.</li>
                <li><code className="font-mono text-[#D4AF57]">Delta_SR</code>: Strike rate deviation above or below phase expectation.</li>
                <li><code className="font-mono text-[#D4AF57]">opp_usage</code>: Fraction of available deliveries consumed.</li>
                <li><code className="font-mono text-[#D4AF57]">P2</code>: Standardized logistic score centered at Par 50.0.</li>
              </ul>
            </div>

            <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585] leading-relaxed">
              <strong className="text-[#F2F2F2]">Cricket meaning:</strong> Rewards run volume and scoring pace in harmony, preventing a 1-ball 600 SR cameo from outscoring a dominant 70 off 45 knock.
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 6, 7 & 8: P3, WICKET ATTRIBUTION & PRESERVATION FLOOR */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
            <TrendingUp className="w-5 h-5 text-[#D4AF57]" />
            5. P3 — Team-state impact & causal attribution
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
            How the team trajectory evolved across the batter's crease occupation, with Phase 7U causal attribution and Phase 7Q preservation.
          </p>
        </div>

        {/* P3 Formulation */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-[14px] text-[#F2F2F2]">
          <div className="space-y-3.5">
            <h3 className="font-semibold text-[#D4AF57] text-[14px]">
              1st innings trajectory equation
            </h3>
            <div className="font-mono bg-[#080808] p-4 rounded border border-[#2D2D2D] space-y-1.5 text-[12.5px] sm:text-[13px]">
              <div><span className="text-[#D4AF57]">Delta_EFS</span> = EFS_exit - EFS_entry</div>
              <div><span className="text-[#D4AF57]">z_efs</span> = Delta_EFS_attributable / 12.0</div>
              <div><span className="text-[#D4AF57]">accel</span> = clip((window_rr - team_rr_entry) / 3.0, -3.0, 3.0)</div>
              <div><span className="text-[#D4AF57]">Raw_P3</span> = 0.50 × z_efs + 0.25 × traj_dev + 0.25 × accel + S_res</div>
            </div>
            <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              Measures the net shift in projected team total (EFS in runs). If a batter enters with team projected at 160 and exits with team projected at 195, <code className="font-mono text-[#D4AF57]">Delta_EFS = +35 runs</code>.
            </p>
          </div>

          <div className="space-y-3.5">
            <h3 className="font-semibold text-[#D4AF57] text-[14px]">
              2nd innings (chase) trajectory equation
            </h3>
            <div className="font-mono bg-[#080808] p-4 rounded border border-[#2D2D2D] space-y-1.5 text-[12.5px] sm:text-[13px]">
              <div><span className="text-[#D4AF57]">Delta_RRR</span> = RRR_entry - RRR_exit</div>
              <div><span className="text-[#D4AF57]">z_rrr</span> = R_eff / 3.0</div>
              <div><span className="text-[#D4AF57]">z_gap</span> = G_eff / 3.0</div>
              <div><span className="text-[#D4AF57]">Raw_P3</span> = 0.50 × z_rrr + 0.25 × z_gap + 0.25 × z_prog + S_res</div>
            </div>
            <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
              Evaluates chase pressure liquidation. Reducing the required run rate and closing the required-vs-current run rate gap generates positive team-state impact.
            </p>
          </div>
        </div>

        {/* Phase 7U Wicket Causality Attribution */}
        <div className="p-5 sm:p-6 bg-[#101010] rounded-xl border border-[#2D2D2D] space-y-3.5 text-[14px]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#2D2D2D] pb-3">
            <h3 className="font-heading font-bold text-[#F2F2F2] text-[15px] sm:text-[16px]">
              Phase 7U Model T: Wicket causality decomposition
            </h3>
            <span className="text-[12px] font-mono text-[#D4AF57] self-start sm:self-auto">
              Attributable Delta_EFS = Delta_R_batter + gamma_attr × External Drag
            </span>
          </div>

          <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
            When partner wickets fall during a batter's stay, the team's projected score declines due to lost resource equity. Phase 7U decomposes this decline so an innocent, high-striking batter is not penalized for a partner's independent error.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
            <div className="bg-[#161616] p-3.5 rounded border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#C25454] block uppercase tracking-wider">gamma = 1.00</span>
              <strong className="text-[#F2F2F2] block mt-0.5 text-[14px]">Batter caused pressure</strong>
              <p className="text-[12px] sm:text-[12.5px] text-[#858585] mt-1 font-normal leading-relaxed">Dots &ge; 50% or SR &lt; 100 on 10+ balls. Full accountability for team deterioration.</p>
            </div>

            <div className="bg-[#161616] p-3.5 rounded border border-[#2A4D30]">
              <span className="text-[11px] font-semibold text-[#5A9E60] block uppercase tracking-wider">gamma = 0.15</span>
              <strong className="text-[#F2F2F2] block mt-0.5 text-[14px]">Independent partner dismissal</strong>
              <p className="text-[12px] sm:text-[12.5px] text-[#858585] mt-1 font-normal leading-relaxed">Batter scored briskly (SR &ge; 150, dots &lt; 45%). Shields batter from 85% of partner drag.</p>
            </div>

            <div className="bg-[#161616] p-3.5 rounded border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#D4AF57] block uppercase tracking-wider">gamma = 0.50</span>
              <strong className="text-[#F2F2F2] block mt-0.5 text-[14px]">Multi-wicket collapse</strong>
              <p className="text-[12px] sm:text-[12.5px] text-[#858585] mt-1 font-normal leading-relaxed">&ge; 2 partner wickets fell. Shared responsibility for middle-order collapse.</p>
            </div>

            <div className="bg-[#161616] p-3.5 rounded border border-[#2D2D2D]">
              <span className="text-[11px] font-semibold text-[#858585] block uppercase tracking-wider">gamma = 0.70</span>
              <strong className="text-[#F2F2F2] block mt-0.5 text-[14px]">General stagnation</strong>
              <p className="text-[12px] sm:text-[12.5px] text-[#858585] mt-1 font-normal leading-relaxed">Single partner wicket without qualifying Category B tempo.</p>
            </div>
          </div>
        </div>

        {/* Phase 7Q Preservation Floor */}
        <div className="p-5 sm:p-6 bg-[#101010] rounded-xl border border-[#2D2D2D] space-y-3.5 text-[14px]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[#2D2D2D] pb-3">
            <h3 className="font-heading font-bold text-[#F2F2F2] text-[15px] sm:text-[16px]">
              Phase 7Q Model B: Decoupled state-preservation floor (Default: 64.0)
            </h3>
            <span className="text-[12px] font-mono text-[#5A9E60] self-start sm:self-auto">
              P3_final = max(P3_score, 64.0) if qualifying
            </span>
          </div>

          <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
            When a team inherits an elite position (e.g. 190+ EFS or low RRR), an active batter maintaining that advantage previously suffered from low Delta EFS due to ceiling compression. The preservation floor guarantees a floor of 64.0, provided strict anti-free-rider conditions are satisfied.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-1">
            <div className="bg-[#161616] p-4 rounded border border-[#2D2D2D] space-y-1.5">
              <strong className="text-[#F2F2F2] block text-[13px] sm:text-[13.5px] font-semibold">1st innings qualifying gates:</strong>
              <ul className="space-y-1 text-[#858585] list-disc list-inside text-[12.5px]">
                <li>Inherited platform: <code className="font-mono text-[#D4AF57]">EFS_entry &ge; 180.0</code></li>
                <li>No deterioration: <code className="font-mono text-[#D4AF57]">Delta_EFS &ge; -2.5</code></li>
                <li>Window team rate: <code className="font-mono text-[#D4AF57]">window_rr &ge; 9.0 RPO</code></li>
                <li>Personal tempo: <code className="font-mono text-[#D4AF57]">personal_rr &ge; 8.5 RPO</code></li>
                <li>Minimum involvement: balls &ge; 8 or runs &ge; 15 (no ducks)</li>
              </ul>
            </div>

            <div className="bg-[#161616] p-4 rounded border border-[#2D2D2D] space-y-1.5">
              <strong className="text-[#F2F2F2] block text-[13px] sm:text-[13.5px] font-semibold">2nd innings qualifying gates:</strong>
              <ul className="space-y-1 text-[#858585] list-disc list-inside text-[12.5px]">
                <li>Controlled chase: <code className="font-mono text-[#D4AF57]">RRR_entry &le; 7.5 RPO</code></li>
                <li>No blowout: <code className="font-mono text-[#D4AF57]">Delta_RRR &ge; -0.5</code></li>
                <li>Meaningful progress: <code className="font-mono text-[#D4AF57]">target_progress &ge; 20%</code></li>
                <li>Personal tempo: <code className="font-mono text-[#D4AF57]">personal_rr &ge; RRR_entry</code></li>
                <li>Minimum involvement: balls &ge; 8 or runs &ge; 15</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Phase 7O Early-Over Stabilization */}
        <div className="p-5 sm:p-6 bg-[#101010] rounded-xl border border-[#2D2D2D] space-y-2.5 text-[14px]">
          <h3 className="font-heading font-bold text-[#F2F2F2] text-[15px] sm:text-[16px]">
            Phase 7O: Early-over P3 stabilization
          </h3>
          <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
            In the opening overs (entry over &lt; 4.0), team run rates are noisy due to minuscule delivery sample sizes. Phase 7O applies Bayesian shrinkage toward par run rate (10.0 RPO):
          </p>
          <div className="font-mono bg-[#080808] p-3 rounded border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#F2F2F2]">
            <span className="text-[#D4AF57]">alpha</span> = min(1.0, balls_bowled / 24.0); <span className="text-[#D4AF57]">effective_rr_entry</span> = alpha × team_rr_entry + (1 - alpha) × 10.0
          </div>
          <p className="text-[#858585] text-[12px] sm:text-[12.5px]">
            This prevents an entry after 3 balls from creating an artificial -15 RPO deterioration penalty.
          </p>
        </div>

        {/* Phase 7I Model E Extreme Chase Feasibility */}
        <div className="p-5 sm:p-6 bg-[#101010] rounded-xl border border-[#2D2D2D] space-y-2.5 text-[14px]">
          <h3 className="font-heading font-bold text-[#F2F2F2] text-[15px] sm:text-[16px]">
            Phase 7I Model E: Chase feasibility saturation
          </h3>
          <p className="text-[#858585] leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
            As balls remaining approach zero in an impossible chase (e.g. 36 needed off 3 balls), raw required run rate explodes toward infinity (720 RPO). Model E bounds the penalty using physical feasibility:
          </p>
          <div className="font-mono bg-[#080808] p-3 rounded border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#F2F2F2]">
            <span className="text-[#D4AF57]">pen_cap</span> = 4.0 + 6.0 × F_chase; <span className="text-[#D4AF57]">R_eff</span> = -pen_cap × tanh(|Delta_RRR| / pen_cap)
          </div>
          <p className="text-[#858585] text-[12px] sm:text-[12.5px]">
            Allows high chase pressure to matter, but mathematically prevents mathematical singularities from destroying realistic scoring.
          </p>
        </div>
      </div>

      {/* SECTION 9, 10 & 11: FINAL CONTRIBUTION & AGGREGATIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Final Contribution Formula */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] space-y-4">
          <div className="border-b border-[#2D2D2D] pb-3.5">
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Scale className="w-5 h-5 text-[#D4AF57]" />
              6. Final contribution synthesis
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Production Phase 7L Context-as-Leverage Formula.
            </p>
          </div>

          <div className="space-y-3.5 text-[14px]">
            <div className="bg-[#080808] p-4 rounded-lg border border-[#2D2D2D] space-y-2 font-mono text-[12.5px] sm:text-[13px]">
              <div className="text-[#858585]">// Context adjustments around par = 50.0</div>
              <div><span className="text-[#D4AF57]">Adjusted_P2</span> = clip(50.0 + (P2 - 50.0) × L, 0.1, 99.9)</div>
              <div><span className="text-[#D4AF57]">Adjusted_P3</span> = clip(50.0 + (P3 - 50.0) × L, 0.1, 99.9)</div>
              <div className="text-[#858585]">// Equal-weighted synthesis</div>
              <div className="text-[#D4AF57] font-bold">Contribution Score = 0.50 × Adjusted_P2 + 0.50 × Adjusted_P3</div>
            </div>

            <div className="p-3.5 bg-[#101010] rounded-lg border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] leading-relaxed">
              <strong className="text-[#F2F2F2]">Par Invariance Law:</strong> If an innings achieves par execution (P2 = 50.0) and par team-state impact (P3 = 50.0), its Contribution Score is strictly 50.0 at ANY context leverage:
              <code className="font-mono block mt-1 text-[#D4AF57]">50 + (50 - 50) × L = 50.0</code>
            </div>

            <div className="p-3.5 bg-[#101010] rounded-lg border border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585] leading-relaxed">
              <span className="text-[#858585] block font-semibold mb-0.5">Historical reference only:</span>
              Legacy Phase 7D previously used direct additive weights (0.25 P1 + 0.35 P2 + 0.40 P3). This was deprecated in Phase 7F in favor of Context-as-Leverage to prevent high context from artificially boosting poor batting execution.
            </div>
          </div>
        </div>

        {/* Raw Contribution & Season Aggregations */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] space-y-4">
          <div className="border-b border-[#2D2D2D] pb-3.5">
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Calculator className="w-5 h-5 text-[#D4AF57]" />
              7. Raw contribution & season shares
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Formulas used for season-long attribution and team share.
            </p>
          </div>

          <div className="space-y-3.5 text-[14px]">
            <div className="bg-[#080808] p-4 rounded-lg border border-[#2D2D2D] space-y-2 font-mono text-[12.5px] sm:text-[13px]">
              <div className="text-[#858585]">// Raw contribution in standardized z-space</div>
              <div><span className="text-[#D4AF57]">C_raw</span> = 0.50 × (z2 × L) + 0.50 × (z3 × L)</div>
              <div className="text-[#858585]">// Positive contribution for volume share</div>
              <div><span className="text-[#D4AF57]">C_pos</span> = max(0.0, C_raw)</div>
              <div className="text-[#858585]">// Season team contribution share</div>
              <div className="text-[#5A9E60] font-bold">Team_Share = (Sigma C_pos_player / Sigma C_pos_team) × 100</div>
            </div>

            <div className="p-3.5 bg-[#101010] rounded-lg border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] leading-relaxed">
              <strong className="text-[#F2F2F2]">Why positive contribution:</strong> Negative contributions indicate below-par innings, but they do not subtract from a teammate's positive value created. A batter's team share reflects their fraction of the total positive equity generated by the batting unit.
            </div>

            <div className="p-3.5 bg-[#101010] rounded-lg border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] leading-relaxed">
              <strong className="text-[#F2F2F2]">DNB mathematical rule:</strong> Did-Not-Bat (DNB) appearances return <code className="font-mono text-[#D4AF57]">NULL</code>. They are strictly excluded from batting innings counts, denominators, and averages. A player who does not bat cannot be penalized for an unreceived opportunity.
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 14: WORKED MATHEMATICAL EXAMPLE (REAL DATA) */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#D4AF57]/40 space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
              <Code2 className="w-5 h-5 text-[#D4AF57]" />
              8. Complete worked numerical example
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
              Step-by-step trace using actual production data from <strong className="text-[#F2F2F2]">Match #1082602 (2017) — Virat Kohli</strong> (62 runs off 47 balls vs. Mumbai Indians).
            </p>
          </div>
          <span className="text-[12px] font-mono text-[#D4AF57] bg-[#101010] px-3 py-1.5 rounded border border-[#D4AF57]/40 font-bold self-start sm:self-auto">
            Final Score: 55.5 (Par 50.0)
          </span>
        </div>

        <p className="text-[14px] sm:text-[15px] text-[#B8B8B8] leading-relaxed font-normal">
          Follow every arithmetic step from raw telemetry to final contribution. Notice how the model evaluates a high-profile 62-run innings: individual execution was outstanding (+32.3 runs above expected), but team projected score dropped by -11.0 runs during his crease occupation due to partner stagnation.
        </p>

        {/* 13 Step Trace Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 1: Match situation</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">Innings 1 • ov 0.1 → 15.3</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">Entry score: 1/0 • Exit score: 110/2. Wickets in hand: 10 → 8.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 2: Actual batting</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">62 runs • 47 balls • SR 131.9</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">5 fours, 2 sixes, 14 dot balls (29.8% dots).</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 3: Expected batting</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">E[Runs] = 29.7 • E[SR] = 115.0</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">Situational hurdle for top-order powerplay entry.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 4: Deviations</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">Delta_R = +32.3 • Delta_SR = +16.9</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">62 - 29.7 = +32.3 runs; 131.9 - 115.0 = +16.9 SR points.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 5: P2 Execution</span>
            <div className="font-mono text-[#5A9E60] font-bold text-[14px] tabular-nums">Raw P2 = 81.4 / 100</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">z_ind = 1.157 → logistic mapping yields 81.4 (elite).</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 6: Team-state delta</span>
            <div className="font-mono text-[#C25454] font-bold text-[14px] tabular-nums">Delta_EFS = -11.0 runs</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">EFS entry 169.7 → EFS exit 158.6 over 15.3 overs.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 7: External drag</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">External Drag = -43.3 runs</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">Delta_EFS (-11.0) - Delta_R (+32.3) = -43.3 runs.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 8: Attribution</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">gamma_attr = 1.00 (Standard)</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">Gayle fell for 22 (27b); 1 partner wicket with general drag.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 9: P3 State impact</span>
            <div className="font-mono text-[#C25454] font-bold text-[14px] tabular-nums">Raw P3 = 30.4 / 100</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">Reflects boundary restriction and total projection drop.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 10: P1 & Leverage</span>
            <div className="font-mono text-[#D4AF57] font-bold text-[14px] tabular-nums">P1 = 40.2 → L = 0.926×</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">1.0 + 0.35 × ((40.2 - 50)/50) = 0.926 (slight dampening).</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 11: Adjusted P2</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">Adj P2 = 79.1 / 100</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">50 + (81.4 - 50) × 0.926 = 50 + 29.08 = 79.1.</p>
          </div>

          <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-1.5">
            <span className="font-semibold text-[#D4AF57] text-[12px]">Step 12: Adjusted P3</span>
            <div className="font-mono text-[#F2F2F2] font-bold text-[14px] tabular-nums">Adj P3 = 31.8 / 100</div>
            <p className="text-[12px] text-[#858585] leading-relaxed">50 + (30.4 - 50) × 0.926 = 50 - 18.15 = 31.8.</p>
          </div>

          <div className="bg-[#161616] p-5 rounded-lg border border-[#D4AF57] space-y-2 col-span-1 sm:col-span-2 lg:col-span-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="font-semibold text-[#D4AF57] text-[12px] block uppercase tracking-wider">
                  Step 13: Final production contribution score
                </span>
                <span className="font-mono text-[24px] sm:text-[28px] font-bold text-[#D4AF57] tabular-nums">
                  0.50 × 79.1 + 0.50 × 31.8 = 55.5
                </span>
              </div>
              <div className="text-right text-[13px] font-mono text-[#858585] tabular-nums">
                C_raw = +0.214 • Positive C_pos = +0.214
              </div>
            </div>
            <p className="text-[13px] sm:text-[13.5px] text-[#B8B8B8] mt-1 pt-2.5 border-t border-[#2D2D2D] leading-relaxed font-normal">
              <strong className="text-[#D4AF57] font-semibold">Synthesis verdict:</strong> Kohli batted with supreme individual skill (P2 = 81.4), but team projection declined over 15.3 overs (P3 = 30.4). The 50/50 balance correctly gives 55.5: a valuable, above-par knock (+5.5 above par), without ignoring the reality that Mumbai Indians successfully restrained the overall team total.
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 15: MODEL SAFEGUARDS & INVARIANTS */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <div className="border-b border-[#2D2D2D] pb-3.5">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-[#5A9E60]" />
            9. Mathematical safeguards & scientific invariants
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
            Strict structural safeguards validated through Phase 7 testing that prevent unrealistic distortions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 text-xs">
          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>Par invariance</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              An execution score of 50.0 remains exactly 50.0 under any context leverage: 50 + (50 - 50) × L = 50.0. No artificial inflation from mere crisis participation.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>Bounded leverage [0.65, 1.35]</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              Leverage is strictly bounded. Prevents extreme situations from multiplying scores to 150+ or compressing them to zero.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>No outcome leakage</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              No match result knowledge (win/loss), tournament standings, or future ball information is available to the model. Evaluated strictly in real time.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>No role or opener bonus</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              Openers, anchors, and finishers are evaluated by the identical objective mathematics. No discretionary bonus points for batting positions.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>No player identity bias</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              Calculations are blind to player names, reputation, price tags, and past accolades. Only raw deliveries and state trajectories matter.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2">
            <div className="flex items-center gap-2 font-semibold text-[#F2F2F2] text-[14px] sm:text-[15px]">
              <CheckCircle2 className="w-4 h-4 text-[#5A9E60]" />
              <span>Strict DNB preservation</span>
            </div>
            <p className="text-[#858585] leading-relaxed text-[12.5px] sm:text-[13px] font-normal">
              Specialist batters who did not bat receive NULL. They are strictly excluded from season averages, preserving statistical validity.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
