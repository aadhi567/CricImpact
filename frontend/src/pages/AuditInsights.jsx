import React from 'react';
import { ShieldCheck, CheckCircle2, FileText } from 'lucide-react';
import Breadcrumbs from '../components/Breadcrumbs';

const PILLARS = [
  {
    id: 'P1',
    title: 'Match Context',
    weight: 'Leverage Signal (0 direct pts)',
    question: 'What situation did the batter face?',
    desc: 'Evaluates situation inherited by the batter: entry over, match leverage, collapse pressure, pitch pace demands, and chase urgency. Acts as a leverage multiplier L(P1) in [0.65, 1.35] on execution deviations.',
  },
  {
    id: 'P2',
    title: 'Batter Execution',
    weight: '50% of Final Score',
    question: 'What did the batter actually do?',
    desc: 'Evaluates what the batter actually executed: runs, balls faced, strike rate, boundaries, and pace deviation above situational baseline expectation, adjusted by context leverage.',
  },
  {
    id: 'P3',
    title: 'Team-State Impact',
    weight: '50% of Final Score',
    isHighest: true,
    question: "How did the batter change the team's position while at the crease?",
    desc: "Measures how the batter changed the team's position while at the crease. Considers macro team trajectory, required-rate/chase progression, active partnership contribution, collapse recovery / stabilization, and team-state improvement, adjusted by context leverage.",
  },
  {
    id: 'P4',
    title: 'Counterfactual Diagnostic',
    weight: '0% (Diagnostic Only)',
    isDiagnostic: true,
    question: 'What could reasonably have been done differently?',
    desc: 'Separate diagnostic layer explaining what the batter could reasonably have done differently. Does NOT affect or modify the 0–100 Contribution Score.',
  },
];

const EDGE_CASES = [
  {
    case: '30 off 5 in death overs',
    scenario: 'Enters over 19.1 at 160/5, hits 5 sixes (SR 600). Team total reaches 190.',
    score: '89.6',
    verdict: 'Elite positive contextual contribution. High phase leverage and major delta EFS.',
  },
  {
    case: '5 balls, 30 runs early in innings',
    scenario: 'Enters over 7.1 at 75/0, scores 30 off 5. Excellent performance but lower context leverage.',
    score: '85.8',
    verdict: 'High performance recognition without exceeding death-over urgency.',
  },
  {
    case: '5 off 3 while team is already at 12 RPO',
    scenario: 'Team at 180/2 at 16.0 ov scoring fast. Adds 5 runs from 3 balls.',
    score: '52.4',
    verdict: 'Par-level incremental impact. Model avoids over-hyping short cameos when situation was already maximized.',
  },
  {
    case: '1* off 1 match-winning final ball',
    scenario: '1 run needed off 1 ball with 3 wickets in hand. Scores 1 to win.',
    score: '62.8',
    verdict: 'Strong positive recognition for sealing victory under maximum situational pressure.',
  },
  {
    case: 'Pure DNB (e.g. Specialist Bowler)',
    scenario: 'Specialist bowler in Playing XI for entire season, never came to crease.',
    score: 'NULL (—)',
    verdict: 'Strict DNB Rule: Denominator = 0. Never counted as 0 or 50. Preserves clean non-diluted evaluation.',
  },
];

export default function AuditInsights() {
  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* Breadcrumb Navigation */}
      <Breadcrumbs
        items={[
          { to: '/dashboard', label: 'Dashboard' },
          { label: 'Model Validation & Audit' },
        ]}
        backTo="/dashboard"
        backLabel="Back to Dashboard"
      />

      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-[12px] font-semibold text-[#D4AF57] tracking-wider mb-1 font-mono uppercase">
          <ShieldCheck className="w-4 h-4" />
          <span>Model architecture and audit specifications</span>
        </div>
        <h1 className="font-heading text-[30px] sm:text-[34px] lg:text-[36px] font-bold text-[#F2F2F2] mt-2.5 tracking-wider leading-tight">
          Phase 7 Methodological Foundation
        </h1>
        <p className="text-[15px] sm:text-[16px] text-[#B8B8B8] mt-2 max-w-3xl leading-relaxed font-mono">
          The mathematical models remain the single source of truth in Python. The frontend visualizes the validated outputs without recalculation or alteration.
        </p>
      </div>

      {/* 4 Pillars Section */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
          <div>
            <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
              Context-as-leverage architecture (50% Adj P2 + 50% Adj P3)
            </h2>
            <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-mono">
              Contribution Score = 50% × Adjusted P2 + 50% × Adjusted P3, with P1 as context leverage multiplier L(P1) in [0.65, 1.35]. P4 is diagnostic only (0% weight).
            </p>
          </div>
          <div className="px-3.5 py-1.5 rounded-lg bg-[#152718] border border-[#2A4D30] text-[12px] text-[#5A9E60] font-semibold font-mono self-start sm:self-auto">
            50% P2 + 50% P3
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {PILLARS.map((p) => (
            <div
              key={p.id}
              className={`rounded-xl p-5 sm:p-6 border flex flex-col justify-between transition-all ${
                p.isHighest
                  ? 'bg-[#101010] border-[#3D351E]'
                  : p.isDiagnostic
                  ? 'bg-[#101010] border-[#222222]'
                  : 'bg-[#101010] border-[#2D2D2D]'
              }`}
            >
              <div>
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded border font-mono ${
                    p.isHighest
                      ? 'bg-[#1C1A14] text-[#D4AF57] border-[#3D351E]'
                      : p.isDiagnostic
                      ? 'bg-[#161616] text-[#858585] border-[#2D2D2D]'
                      : 'bg-[#161616] text-[#B8B8B8] border-[#2D2D2D]'
                  }`}
                >
                  {p.id} • {p.weight}
                </span>
                <h3 className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2] mt-3">{p.title}</h3>
                <div className="text-[13px] italic text-[#858585] mt-1 font-mono">"{p.question}"</div>
                <p className="text-[13px] sm:text-[13.5px] text-[#B8B8B8] mt-2.5 leading-relaxed font-mono">{p.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strict DNB Rule & Two-View Architecture */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strict DNB Rule */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-4">
          <div className="flex items-center gap-2 text-[12px] font-semibold text-[#5A9E60] tracking-wider mb-1 font-mono uppercase">
            <CheckCircle2 className="w-4 h-4" />
            <span>Strict did-not-bat (DNB) rule</span>
          </div>
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
            DNB = NULL (never counted as zero)
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#B8B8B8] leading-relaxed font-mono">
            In cricket, lower-order batters and specialist bowlers frequently do not bat when their team wins comfortably. Across all match appearances in the validated dataset:
          </p>
          <div className="grid grid-cols-2 gap-4 my-4 text-center">
            <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D]">
              <div className="text-[12px] text-[#858585] font-semibold font-mono">Batting innings</div>
              <div className="text-[22px] sm:text-[24px] font-bold text-[#5A9E60] mt-1 tabular-nums font-mono">19,111 (68.5%)</div>
            </div>
            <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D]">
              <div className="text-[12px] text-[#858585] font-semibold font-mono">DNB appearances</div>
              <div className="text-[22px] sm:text-[24px] font-bold text-[#C25454] mt-1 tabular-nums font-mono">8,798 (31.5%)</div>
            </div>
          </div>
          <p className="text-[13px] sm:text-[13.5px] text-[#858585] leading-relaxed font-mono">
            Treating DNB as 0 would artificially punish 31.5% of all appearances. The denominator for contribution score averages is strictly the count of actual batting innings.
          </p>
        </div>

        {/* View A vs View B */}
        <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-4">
          <div className="flex items-center gap-2 text-[12px] font-semibold text-[#D4AF57] tracking-wider mb-1 font-mono uppercase">
            <FileText className="w-4 h-4" />
            <span>Two-view architecture</span>
          </div>
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
            View A (primary) vs. View B (sensitivity)
          </h2>
          <div className="space-y-3.5 text-[14px] text-[#F2F2F2] mt-3">
            <div className="p-4 rounded-lg bg-[#101010] border border-[#2D2D2D]">
              <div className="font-semibold text-[#F2F2F2] mb-1 font-mono text-[14px] sm:text-[15px]">View A — All-innings primary record:</div>
              <span className="text-[#858585] text-[13px] sm:text-[13.5px] font-mono leading-relaxed block">Complete, transparent account of every genuine batting opportunity. No arbitrary exclusions.</span>
            </div>
            <div className="p-4 rounded-lg bg-[#101010] border border-[#3D351E]">
              <div className="font-semibold text-[#D4AF57] mb-1 font-mono text-[14px] sm:text-[15px]">View B — Qualified sensitivity:</div>
              <span className="text-[#858585] text-[13px] sm:text-[13.5px] font-mono leading-relaxed block">Excludes only empirically verified negligible non-dismissal innings (&le;2 balls, not out, |C_raw| &le; 0.10, minimal state change). High-impact cameos are NEVER removed.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Model Edge Cases Reference */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
          Empirical validation and benchmark edge cases
        </h2>

        <div className="divide-y divide-[#222222]">
          {EDGE_CASES.map((ec, idx) => (
            <div key={idx} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
              <div className="max-w-2xl">
                <div className="font-semibold text-[#F2F2F2] text-[15px] sm:text-[16px] font-mono">{ec.case}</div>
                <div className="text-[#858585] mt-1 text-[13px] sm:text-[13.5px] font-mono">{ec.scenario}</div>
                <div className="text-[#B8B8B8] mt-1.5 text-[13px] sm:text-[13.5px] font-mono leading-relaxed">{ec.verdict}</div>
              </div>
              <div className="sm:text-right shrink-0">
                <span className="text-[12px] text-[#858585] block font-semibold font-mono">Par score:</span>
                <span className="text-[20px] sm:text-[22px] font-mono font-bold text-[#D4AF57] tabular-nums">{ec.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
