import { useState, useEffect } from 'react';

/**
 * Hook that returns current window width, updating smoothly on resize.
 * Safely defaults to 1200 for SSR and test execution environments.
 */
export function useWindowWidth() {
  const [width, setWidth] = useState(() => (typeof window !== 'undefined' ? window.innerWidth : 1200));

  useEffect(() => {
    if (typeof window === 'undefined') return;

    let timer = null;
    const handleResize = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        setWidth(window.innerWidth);
      }, 75);
    };

    window.addEventListener('resize', handleResize, { passive: true });
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return {
    width,
    isMobile: width < 640,
    isNarrowMobile: width < 400,
    valueOf: () => width,
    toString: () => String(width),
  };
}

/**
 * Returns true if window width is below breakpoint (default 640px).
 */
export function useIsMobile(breakpoint = 640) {
  const { width } = useWindowWidth();
  return width < breakpoint;
}
