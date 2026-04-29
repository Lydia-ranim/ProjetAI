/**
 * Hook: usePeakHour
 * Reactively detects Algiers peak hours and updates every minute
 */

import { useState, useEffect } from 'react';
import { isPeakHour, isNightHours, getPeakLabel, getAlgiersTime, formatTimeFull } from '../utils/time';

export function usePeakHour() {
  const [peak, setPeak] = useState(isPeakHour());
  const [night, setNight] = useState(isNightHours());
  const [label, setLabel] = useState(getPeakLabel());
  const [clock, setClock] = useState(formatTimeFull(getAlgiersTime()));

  useEffect(() => {
    const interval = setInterval(() => {
      const now = getAlgiersTime();
      setPeak(isPeakHour(now));
      setNight(isNightHours(now));
      setLabel(getPeakLabel());
      setClock(formatTimeFull(now));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return { isPeak: peak, isNight: night, label, clock };
}
