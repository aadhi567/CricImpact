import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronRight, ArrowLeft } from 'lucide-react';

/**
 * Breadcrumbs
 * Accessible, responsive breadcrumb trail with an optional quick back button.
 * Adheres to the CricImpact Gold & Onyx design system.
 */
export default function Breadcrumbs({ items = [], backTo = null, backLabel = 'Back', className = '' }) {
  const navigate = useNavigate();

  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex flex-wrap items-center justify-between gap-3 text-xs font-mono py-2 ${className}`}
    >
      <ol className="flex flex-wrap items-center gap-1.5 text-[#858585]">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={index} className="flex items-center gap-1.5">
              {index > 0 && <ChevronRight className="w-3.5 h-3.5 text-[#555555] shrink-0" />}
              {isLast || !item.to ? (
                <span
                  className={`font-semibold truncate max-w-[240px] sm:max-w-none ${
                    isLast ? 'text-[#D4AF57]' : 'text-[#B8B8B8]'
                  }`}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.to}
                  className="hover:text-[#F2F2F2] hover:underline transition-colors truncate max-w-[180px] sm:max-w-none"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>

      {backTo && (
        <button
          type="button"
          onClick={() => (backTo === -1 ? navigate(-1) : navigate(backTo))}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-[#B8B8B8] hover:text-[#F2F2F2] bg-[#161616] hover:bg-[#202020] border border-[#2D2D2D] rounded-md transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-[#D4AF57]" />
          <span>{backLabel}</span>
        </button>
      )}
    </nav>
  );
}
