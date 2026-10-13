import React from 'react';
import { Target, Zap, Clock, ShieldAlert, Award, Compass } from 'lucide-react';

const CONTEXT_CONFIG = [
  {
    key: 'first_innings_contribution',
    label: 'First Innings',
    desc: 'Setting the target / early trajectory setting',
    icon: Compass,
    accentColor: 'text-[#858585]',
  },
  {
    key: 'chase_contribution',
    label: 'Chase (2nd Innings)',
    desc: 'Pursuing target under RRR evolution',
    icon: Target,
    accentColor: 'text-[#D4AF57]',
  },
  {
    key: 'powerplay_contribution',
    label: 'Powerplay (0–6)',
    desc: 'Fielding restrictions & opening tempo',
    icon: Zap,
    accentColor: 'text-[#D4AF57]',
  },
  {
    key: 'middle_over_contribution',
    label: 'Middle Overs (6–16)',
    desc: 'Spin consolidation & strike rotation',
    icon: Clock,
    accentColor: 'text-[#858585]',
  },
  {
    key: 'death_over_contribution',
    label: 'Death Overs (16–20)',
    desc: 'High-leverage acceleration & boundary finish',
    icon: Award,
    accentColor: 'text-[#D4AF57]',
  },
  {
    key: 'high_pressure_contribution',
    label: 'High Pressure',
    desc: 'Steep required run rate or collapse recovery',
    icon: ShieldAlert,
    accentColor: 'text-[#C25454]',
  },
];

export default function ContributionBreakdown({ breakdown = {} }) {
  return (
    <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D] shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Contextual breakdown by phase
          </h3>
          <p className="text-[12px] font-normal text-[#858585] mt-0.5">
            Contribution evaluated across innings type, match phases, and situational pressure.
          </p>
        </div>
        <div className="text-[11px] text-[#858585] bg-[#101010] px-2.5 py-1 rounded-md border border-[#2D2D2D] font-medium">
          Par = 50.0
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {CONTEXT_CONFIG.map(({ key, label, desc, icon: Icon, accentColor }) => {
          const val = breakdown[key];
          const isNull = val === null || val === undefined;
          const num = !isNull ? Number(val) : null;

          let scoreColor = 'text-[#858585]';
          if (!isNull) {
            if (num >= 65) {
              scoreColor = 'text-[#5A9E60]';
            } else if (num >= 50) {
              scoreColor = 'text-[#5A9E60]/80';
            } else {
              scoreColor = 'text-[#C25454]';
            }
          }

          return (
            <div
              key={key}
              className="bg-[#101010] rounded-lg p-3.5 border border-[#2D2D2D] flex flex-col justify-between transition-colors hover:bg-[#181818]"
            >
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Icon className={`w-3.5 h-3.5 ${accentColor}`} />
                  <span className="text-[13px] font-semibold text-[#F2F2F2] truncate" title={label}>
                    {label}
                  </span>
                </div>
                <div className="text-[11px] text-[#858585] leading-tight line-clamp-2">
                  {desc}
                </div>
              </div>

              <div className="mt-3 flex items-baseline justify-between border-t border-[#2D2D2D] pt-2">
                <span className={`text-[20px] font-bold font-mono tabular-nums ${scoreColor}`}>
                  {isNull ? '—' : num.toFixed(1)}
                </span>
                {!isNull && (
                  <span className="text-[11px] text-[#858585] font-medium tabular-nums font-mono">
                    {num > 50 ? `+${(num - 50).toFixed(1)}` : `${(num - 50).toFixed(1)}`}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3.5 pt-2.5 border-t border-[#2D2D2D] text-[11px] text-[#858585] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1">
        <span>* "—" indicates no observed batting opportunities in this segment.</span>
        <span className="text-[#858585]">Unobserved situations do not penalize player score.</span>
      </div>
    </div>
  );
}
