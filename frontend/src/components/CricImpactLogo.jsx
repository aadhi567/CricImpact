import React from 'react';
import { Link } from 'react-router-dom';

/**
 * CricImpactLogo
 * Official Brand Asset component for CricImpact Cricket Analytics.
 * Preserves the exact 2:1 aspect ratio, contains without distortion,
 * with enhanced desktop visibility (150–190px width) on Raw Carbon dark backgrounds.
 */
export default function CricImpactLogo({
  size = 'navbar',
  className = '',
  linkTo = null,
  alt = 'CricImpact Cricket Analytics',
  priority = false,
}) {
  // Width presets tailored for prominent brand visibility while preserving 2:1 ratio
  const sizeClasses = {
    xs: 'w-[95px] sm:w-[115px]',
    sm: 'w-[110px] sm:w-[135px]',
    navbar: 'w-[110px] sm:w-[125px] md:w-[135px] lg:w-[140px] xl:w-[130px] 2xl:w-[150px]',
    md: 'w-[170px] sm:w-[195px]',
    lg: 'w-[210px] sm:w-[240px]',
    xl: 'w-[260px] sm:w-[300px]',
  };

  const selectedSize = sizeClasses[size] || size;

  const imageElement = (
    <div className={`inline-flex items-center shrink-0 ${className}`}>
      <img
        src="/cricimpact-logo.png"
        alt={alt}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        className={`${selectedSize} h-auto max-w-full object-contain select-none transition-transform duration-200 hover:scale-[1.02]`}
        style={{ aspectRatio: '2 / 1' }}
      />
    </div>
  );

  if (linkTo) {
    return (
      <Link
        to={linkTo}
        className="inline-flex items-center focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF57] rounded-sm group transition-opacity hover:opacity-95"
        aria-label={alt}
      >
        {imageElement}
      </Link>
    );
  }

  return imageElement;
}
