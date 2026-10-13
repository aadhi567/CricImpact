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
          className="h-11 sm:h-12 appearance-none bg-[#121212] border border-[#2D2D2D] hover:border-[#D4AF57]/60 focus:border-[#D4AF57] text-[#F2F2F2] text-[14px] sm:text-[15px] font-semibold rounded-lg pl-4 pr-10 py-2 sm:py-2.5 transition-colors cursor-pointer shadow-xs focus:outline-none"
        >
          {competitions.map((c) => (
            <option key={c.id} value={c.id} className="bg-[#161616] text-[#F2F2F2]">
              {c.short_name} • {c.name}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 text-[#858585] absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
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
