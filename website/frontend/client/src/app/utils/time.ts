/**
 * Time utilities for Algiers Transit AI
 * Handles Algiers timezone (UTC+1), peak hours, and time formatting
 */

/** Get current Algiers time (UTC+1) */
export function getAlgiersTime(): Date {
  const now = new Date();
  const utc = now.getTime() + now.getTimezoneOffset() * 60000;
  return new Date(utc + 3600000); // UTC+1
}

/** Format time as HH:MM */
export function formatTime(date: Date): string {
  return date.toLocaleTimeString('fr-DZ', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Africa/Algiers',
  });
}

/** Format current time as HH:MM:SS for live clock */
export function formatTimeFull(date: Date): string {
  return date.toLocaleTimeString('fr-DZ', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'Africa/Algiers',
  });
}

/** Check if it's peak hour in Algiers */
export function isPeakHour(date?: Date): boolean {
  const d = date || getAlgiersTime();
  const h = d.getHours();
  const m = d.getMinutes();
  const timeVal = h * 60 + m;
  // Morning: 7:00-9:00, Lunch: 12:00-13:00, Evening: 17:00-19:00
  return (
    (timeVal >= 420 && timeVal <= 540) || // 7-9 AM
    (timeVal >= 720 && timeVal <= 780) || // 12-1 PM
    (timeVal >= 1020 && timeVal <= 1140)   // 5-7 PM
  );
}

/** Check if it's night hours (after 10PM) */
export function isNightHours(date?: Date): boolean {
  const d = date || getAlgiersTime();
  const h = d.getHours();
  return h >= 22 || h < 5;
}

/** Get peak multiplier for wait times */
export function getPeakMultiplier(date?: Date): number {
  return isPeakHour(date) ? 1.5 : 1.0;
}

/** Add minutes to a date */
export function addMinutes(date: Date, minutes: number): Date {
  return new Date(date.getTime() + minutes * 60000);
}

/** Format minutes as human-readable duration */
export function formatDuration(minutes: number): string {
  if (minutes < 1) return '< 1 min';
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m > 0 ? `${h}h ${m}min` : `${h}h`;
}

/** Get peak hour label */
export function getPeakLabel(): string {
  const now = getAlgiersTime();
  const h = now.getHours();
  if (h >= 7 && h < 9) return 'Morning Rush';
  if (h >= 12 && h < 13) return 'Lunch Rush';
  if (h >= 17 && h < 19) return 'Evening Rush';
  if (h >= 22 || h < 5) return 'Night Service';
  return 'Off-Peak';
}

/** Compute departure time string from now + offset */
export function computeDepartureTime(offsetMinutes: number): string {
  const now = getAlgiersTime();
  const departure = addMinutes(now, offsetMinutes);
  return formatTime(departure);
}
