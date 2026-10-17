import React from 'react';
import { Trophy, Globe, ChevronDown } from 'lucide-react';
import { useCompetition } from '../context/CompetitionContext';

export default function CompetitionSelector({ variant = 'pills', className = '' }) {
  const { competition, setCompetition, competitions } = useCompetition();

  const getIcon = (id) => {
    switch (id) {
      case 'ipl':
        return <Trophy className="w-3.5 h-3.5 shrink-0" />;
      case 't20i':
        return <Globe className="w-3.5 h-3.5 shrink-0" />;
      default:
        return <Trophy className="w-3.5 h-3.5 shrink-0" />;
    }
  };

  if (variant === 'select') {
    return (
      <div className={`relative inline-block ${className}`}>
        <select
          id="competition-selector"
          aria-label="Tournament Selector"
          value={competition}
          onChange={(e) => setCompetition(e.target.value)}
          className="h-9 sm:h-10 xl:h-9 2xl:h-10 max-w-[125px] sm:max-w-[150px] xl:max-w-[155px] 2xl:max-w-[210px] appearance-none bg-[#121212] border border-[#2D2D2D] hover:border-[#D4AF57]/60 focus:border-[#D4AF57] text-[#F2F2F2] text-[12.5px] sm:text-[13px] 2xl:text-[14px] font-semibold rounded-lg pl-3 pr-7 sm:pr-8 py-1 sm:py-1.5 transition-colors cursor-pointer shadow-xs focus:outline-none truncate"
        >
          {competitions.map((c) => (
            <option key={c.id} value={c.id} className="bg-[#161616] text-[#F2F2F2]">
              {c.short_name} • {c.name}
            </option>
          ))}
        </select>
        <ChevronDown className="w-3.5 h-3.5 text-[#858585] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-1.5 p-1 bg-[#121212] border border-[#2D2D2D] rounded-lg ${className}`}>
      {competitions.map((c) => {
        const isActive = c.id === competition;
        return (
          <button
            key={c.id}
            type="button"
            onClick={() => setCompetition(c.id)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all duration-150 cursor-pointer ${
              isActive
                ? 'bg-[#D4AF57] text-[#080808] shadow-sm font-bold'
                : 'text-[#858585] hover:text-[#F2F2F2] hover:bg-[#1A1A1A]'
            }`}
            title={`${c.name} (${c.coverage || 'T20'})`}
          >
            {getIcon(c.id)}
            <span>{c.short_name}</span>
          </button>
        );
      })}
    </div>
  );
}
