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
    <div className="bg-[#161616] rounded-lg p-3 sm:p-3.5 border border-[#2D2D2D] transition-all hover:border-[#3D3D3D] flex flex-col justify-between font-sans">
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 text-[11px] sm:text-[11.5px] font-semibold text-[#858585] tracking-wider uppercase truncate">
            <span className="truncate">{title}</span>
            {tooltip && (
              <span title={tooltip} className="cursor-help text-[#858585] hover:text-[#D4AF57] shrink-0">
                <HelpCircle className="w-3 h-3" />
              </span>
            )}
          </div>
          {Icon && (
            <div className="w-6 h-6 rounded-md bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] shrink-0">
              <Icon className="w-3.5 h-3.5" />
            </div>
          )}
        </div>

        <div className="mt-2 flex items-baseline gap-2">
          <span className={`text-[20px] sm:text-[24px] font-semibold tracking-tight tabular-nums font-sans leading-none ${valueColor}`}>
            {displayValue}
          </span>
          {badge && (
            <span className="text-[11px] px-1.5 py-0.5 rounded font-sans bg-[#101010] text-[#D4AF57] border border-[#2D2D2D]">
              {badge}
            </span>
          )}
        </div>
      </div>

      {subtitle && (
        <div className="mt-2 pt-1.5 border-t border-[#222222] text-[11px] sm:text-[11.5px] font-normal text-[#858585] truncate font-sans">
          {subtitle}
        </div>
      )}
    </div>
  );
}
