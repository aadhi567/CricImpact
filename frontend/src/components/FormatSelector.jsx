import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Info } from 'lucide-react';
import { useCompetition } from '../context/CompetitionContext';

import { CRICKET_FORMATS } from '../constants/competitionConstants';

export default function FormatSelector({ variant = 'dropdown', className = '' }) {
  const { activeMeta } = useCompetition();
  const [selectedFormat, setSelectedFormat] = useState('T20');
  const [isOpen, setIsOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const dropdownRef = useRef(null);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  // Clear temporary notice after 4 seconds
  useEffect(() => {
    if (notice) {
      const timer = setTimeout(() => setNotice(''), 4000);
      return () => clearTimeout(timer);
    }
  }, [notice]);

  const handleSelectFormat = (formatId) => {
    if (formatId === 'T20') {
      setSelectedFormat('T20');
      setNotice('');
      setIsOpen(false);
    } else {
      setNotice(
        `CricImpact is specialized on T20 cricket (IPL and International T20Is). ${formatId} model calibration is currently in development.`
      );
    }
  };

  if (variant === 'select') {
    return (
      <div className={`relative inline-block ${className}`}>
        <select
          id="format-selector-native"
          aria-label="Format Selector"
          value={selectedFormat}
          onChange={(e) => handleSelectFormat(e.target.value)}
          className="h-8.5 sm:h-9 appearance-none bg-[#121212] border border-[#2D2D2D] hover:border-[#D4AF57]/60 focus:border-[#D4AF57] text-[#F2F2F2] text-[12px] sm:text-[12.5px] font-sans font-semibold rounded-md pl-3 pr-8 py-1 transition-colors cursor-pointer shadow-xs focus:outline-none"
        >
          {CRICKET_FORMATS.map((f) => (
            <option
              key={f.id}
              value={f.id}
              disabled={f.status !== 'active'}
              className="bg-[#161616] text-[#F2F2F2]"
            >
              {f.label} {f.status === 'active' ? '• Active' : `• (${f.activeBadge})`}
            </option>
          ))}
        </select>
        <ChevronDown className="w-3.5 h-3.5 text-[#858585] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
    );
  }

  return (
    <div ref={dropdownRef} className={`relative inline-block ${className}`}>
      {/* Primary Format Selector Button */}
      <button
        id="format-selector"
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Cricket Format Selector"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        className="h-8 sm:h-8.5 xl:h-8.5 2xl:h-9 flex items-center gap-1.5 px-2 sm:px-2.5 rounded-md bg-[#121212] hover:bg-[#161616] border border-[#2D2D2D] hover:border-[#D4AF57]/60 text-[#F2F2F2] transition-all duration-150 shadow-xs cursor-pointer focus:outline-none focus:border-[#D4AF57]"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
        <span className="text-[11.5px] sm:text-[12px] 2xl:text-[12.5px] font-sans font-bold tracking-wider text-[#F2F2F2]">
          {selectedFormat || activeMeta?.format || 'T20'}
        </span>
        <ChevronDown
          className={`w-3 h-3 text-[#858585] transition-transform duration-150 ${
            isOpen ? 'rotate-180 text-[#D4AF57]' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Available Cricket Formats"
          className="absolute right-0 mt-2 w-72 sm:w-80 rounded-xl bg-[#121212] border border-[#2D2D2D] p-2 shadow-2xl z-50 font-sans animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="px-3 py-2 border-b border-[#222222] mb-1.5 flex items-center justify-between">
            <span className="text-[12px] font-semibold uppercase tracking-wider text-[#858585]">
              Cricket Format
            </span>
            <span className="text-[11.5px] text-[#D4AF57] font-medium">Specialized</span>
          </div>

          <div className="space-y-1">
            {CRICKET_FORMATS.map((f) => {
              const isSelected = selectedFormat === f.id;
              const isActive = f.status === 'active';
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => handleSelectFormat(f.id)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-lg transition-colors flex items-start justify-between gap-3 cursor-pointer ${
                    isSelected
                      ? 'bg-[#1A1A1A] text-[#F2F2F2] border border-[#D4AF57]/40 shadow-xs'
                      : isActive
                      ? 'text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616]'
                      : 'text-[#666666] hover:bg-[#161616]/60 cursor-pointer'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[14px] font-bold text-[#F2F2F2] tracking-wide">
                        {f.label}
                      </span>
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${
                          isActive
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-[#222222] text-[#888888] border border-[#333333]'
                        }`}
                      >
                        {f.activeBadge}
                      </span>
                    </div>
                    <p className="text-[12px] text-[#858585] mt-1 leading-snug truncate">
                      {f.description}
                    </p>
                  </div>
                  {isSelected && (
                    <Check className="w-4 h-4 text-[#D4AF57] shrink-0 mt-1" />
                  )}
                </button>
              );
            })}
          </div>

          {notice && (
            <div className="mt-2 p-2.5 rounded-lg bg-[#241C12] border border-[#523F1C] text-[#E0C070] text-[12px] leading-relaxed flex items-start gap-2">
              <Info className="w-4 h-4 text-[#D4AF57] shrink-0 mt-0.5" />
              <span>{notice}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
