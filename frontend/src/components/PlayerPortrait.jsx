import React, { useState } from 'react';
import { getPlayerImageUrl, getPlayerInitials } from '../utils/playerImageMap';

/**
 * Reusable Player Portrait / Avatar component following CricImpact's Gold & Onyx aesthetic.
 *
 * Features:
 * - Direct lookup against normalized player image manifest
 * - Handles aliases, abbreviations, and canonical Cricsheet names
 * - Graceful fallback on missing image or failed load (onError)
 * - Gold & Onyx styled monogram fallback avatar
 * - Responsive sizing tokens (xs, sm, md, lg, xl)
 * - Optimized with lazy loading & decoding="async"
 */
export default function PlayerPortrait({
  playerName,
  playerId,
  size = 'lg',
  className = '',
  showBorder = true,
  alt,
}) {
  const [hasError, setHasError] = useState(false);

  const initialImageUrl = getPlayerImageUrl(playerName, playerId);
  const initials = getPlayerInitials(playerName || playerId || '');

  // Size token mappings
  const sizeClasses = {
    xs: 'w-7 h-7 text-[10px] rounded-lg',
    sm: 'w-9 h-9 text-xs rounded-xl',
    md: 'w-12 h-12 text-sm rounded-xl',
    lg: 'w-16 h-16 sm:w-20 sm:h-20 text-base sm:text-lg rounded-2xl',
    xl: 'w-24 h-24 sm:w-28 sm:h-28 text-xl sm:text-2xl rounded-2xl',
    profile: 'w-20 h-20 sm:w-24 sm:h-24 md:w-28 md:h-28 text-2xl sm:text-3xl rounded-2xl',
  };

  const containerSize = sizeClasses[size] || sizeClasses.lg;
  const borderStyles = showBorder
    ? 'border border-[#A8893D]/45 shadow-sm ring-1 ring-[#D4AF57]/20'
    : 'border border-[#2D2D2D]';

  const shouldRenderImage = Boolean(initialImageUrl) && !hasError;
  const isHighPriority = size === 'profile' || size === 'xl';

  return (
    <div
      className={`relative shrink-0 aspect-square overflow-hidden bg-[#121212] flex items-center justify-center select-none ${containerSize} ${borderStyles} ${className}`}
      data-testid="player-portrait"
    >
      {shouldRenderImage ? (
        <img
          src={initialImageUrl}
          alt={alt || `${playerName || 'Player'} portrait`}
          loading={isHighPriority ? 'eager' : 'lazy'}
          decoding="async"
          fetchpriority={isHighPriority ? 'high' : 'auto'}
          onError={() => setHasError(true)}
          className="w-full h-full object-cover object-top transition-transform duration-300 hover:scale-105"
        />
      ) : (
        <div
          className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-[#1C1810] via-[#141414] to-[#0D0D0D] text-[#D4AF57] font-bold font-heading tracking-wider"
          data-testid="player-portrait-fallback"
          title={playerName || 'Player Profile'}
        >
          <span>{initials}</span>
          {size === 'xl' && (
            <span className="text-[9px] uppercase tracking-widest text-[#858585] font-sans mt-0.5">
              Player
            </span>
          )}
        </div>
      )}

      {/* Subtle gold corner accent for premium Gold & Onyx feel */}
      {showBorder && (
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-[#D4AF57]/40 pointer-events-none" />
      )}
    </div>
  );
}
