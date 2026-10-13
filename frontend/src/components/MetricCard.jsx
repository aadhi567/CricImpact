import React from 'react';
import { HelpCircle } from 'lucide-react';

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  unit = '',
  tooltip,
  variant = 'default',
  badge,
  isScore = false,
}) {
  // STRICT NULL HANDLING: null or undefined displays '—', never 0
  const isNull = value === null || value === undefined || value === '—' || value === 'N/A';
  const displayValue = isNull ? '—' : `${value}${unit}`;

  // Color selection based on sports analytics hierarchy
  let valueColor = 'text-[#F2F2F2]';

  if (!isNull && isScore) {
    const num = Number(value);
    if (num >= 65) {
      valueColor = 'text-[#5A9E60]'; // Muted green
    } else if (num >= 52) {
      valueColor = 'text-[#D4AF57]'; // Metallic gold
    } else if (num >= 48) {
      valueColor = 'text-[#F2F2F2]'; // Par Bone White
    } else {
      valueColor = 'text-[#C25454]'; // Restrained muted red
    }
  } else if (!isNull) {
    if (variant === 'gold' || variant === 'accent') {
      valueColor = 'text-[#D4AF57]';
    } else if (variant === 'indigo' || variant === 'secondary') {
      valueColor = 'text-[#F2F2F2]';
    } else if (variant === 'cyan' || variant === 'positive') {
      valueColor = 'text-[#5A9E60]';
    }
  }

  return (
    <div className="bg-[#161616] rounded-xl p-4 sm:p-5 border border-[#2D2D2D] transition-all hover:border-[#3D3D3D] flex flex-col justify-between font-mono">
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-[12px] sm:text-[12.5px] font-semibold text-[#858585] tracking-wider uppercase truncate">
            <span className="truncate">{title}</span>
            {tooltip && (
              <span title={tooltip} className="cursor-help text-[#858585] hover:text-[#D4AF57] shrink-0">
                <HelpCircle className="w-3.5 h-3.5" />
              </span>
            )}
          </div>
          {Icon && (
            <div className="w-7 h-7 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] shrink-0">
              <Icon className="w-4 h-4" />
            </div>
          )}
        </div>

        <div className="mt-2.5 flex items-baseline gap-2.5">
          <span className={`text-[28px] sm:text-[32px] font-semibold tracking-tight tabular-nums font-mono leading-none ${valueColor}`}>
            {displayValue}
          </span>
          {badge && (
            <span className="text-[12px] px-2 py-0.5 rounded font-mono bg-[#101010] text-[#D4AF57] border border-[#2D2D2D]">
              {badge}
            </span>
          )}
        </div>
      </div>

      {subtitle && (
        <div className="mt-3 pt-2 border-t border-[#222222] text-[12px] sm:text-[12.5px] font-normal text-[#858585] truncate font-mono">
          {subtitle}
        </div>
      )}
    </div>
  );
}
