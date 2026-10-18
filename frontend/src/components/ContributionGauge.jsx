import React from 'react';

export default function ContributionGauge({ score }) {
  if (score === null || score === undefined) {
    return (
      <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D] text-center">
        <span className="text-[#858585] text-xs">Contribution Score: </span>
        <span className="text-[#F2F2F2] font-bold">—</span>
        <p className="text-[11px] text-[#858585] mt-1">No observed batting opportunities.</p>
      </div>
    );
  }

  const num = Number(score);
  const clamped = Math.max(0, Math.min(100, num));

  const isAbovePar = num > 50.0;
  const isPar = Math.abs(num - 50.0) <= 0.5;

  return (
    <div className="bg-[#161616] rounded-xl p-3.5 sm:p-4 border border-[#2D2D2D] shadow-xs">
      <div className="flex items-center justify-between mb-2.5">
        <div>
          <span className="text-[10.5px] sm:text-[11px] font-semibold text-[#858585] block">
            Overall contribution score
          </span>
          <p className="text-[11px] sm:text-xs font-normal text-[#858585]">Par benchmark = 50.0</p>
        </div>
        <div className="text-right">
          <span className="text-[22px] sm:text-[24px] font-bold text-[#D4AF57] tabular-nums font-mono leading-none">
            {num.toFixed(1)}
          </span>
          <span className="text-[#858585] text-xs font-medium font-mono"> / 100</span>
        </div>
      </div>

      {/* Progress Track */}
      <div className="relative w-full h-3 bg-[#222222] rounded-full overflow-hidden mb-2">
        {/* Par Reference Line at 50% */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-[#D4AF57] z-10"
          style={{ left: '50%' }}
          title="Par contextual contribution (50.0)"
        />

        {/* Dynamic Score Fill */}
        <div
          className={`h-full transition-all duration-500 rounded-full ${
            num >= 65
              ? 'bg-[#5A9E60]'
              : num >= 50
              ? 'bg-[#5A9E60]/80'
              : 'bg-[#C25454]'
          }`}
          style={{ width: `${clamped}%` }}
        />
      </div>

      {/* Zone Indicators */}
      <div className="flex justify-between items-center text-[10px] sm:text-[11px] text-[#858585]">
        <span>0 <span className="hidden xs:inline">(Below Par)</span></span>
        <span className="text-[#D4AF57] font-semibold">▲ 50.0 Par<span className="hidden sm:inline"> Benchmark</span></span>
        <span>100 <span className="hidden xs:inline">(Elite)</span></span>
      </div>

      <div className="mt-3 pt-3 border-t border-[#2D2D2D] flex items-center justify-between text-[13px]">
        <span className="text-[#858585]">Performance vs. Par:</span>
        <span
          className={`font-semibold px-2.5 py-0.5 rounded-full text-[12px] ${
            isAbovePar
              ? 'bg-[#152718] text-[#5A9E60] border border-[#2A4D30]'
              : isPar
              ? 'bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40'
              : 'bg-[#271414] text-[#C25454] border border-[#4D2626]'
          }`}
        >
          {isAbovePar
            ? `+${(num - 50.0).toFixed(1)} Above Par`
            : isPar
            ? 'At Par (50.0)'
            : `${(num - 50.0).toFixed(1)} Below Par`}
        </span>
      </div>
    </div>
  );
}
