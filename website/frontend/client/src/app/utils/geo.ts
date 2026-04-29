/**
 * Geographic utilities for the Algiers Transit AI
 * Haversine distance, coordinate helpers, and snapping logic
 */

export interface LatLng {
  lat: number;
  lng: number;
}

/** Earth radius in meters */
const R = 6_371_000;

/** Convert degrees to radians */
function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

/**
 * Haversine distance between two lat/lng points in meters
 */
export function haversineDistance(a: LatLng, b: LatLng): number {
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const sinLat = Math.sin(dLat / 2);
  const sinLng = Math.sin(dLng / 2);
  const h = sinLat * sinLat + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * sinLng * sinLng;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/**
 * Walk time in minutes at 5 km/h (83.3 m/min)
 */
export function walkTimeMinutes(distanceM: number): number {
  return distanceM / 83.3;
}

/**
 * Find nearest stop to a given coordinate
 */
export function findNearestStop<T extends LatLng>(point: LatLng, stops: T[]): T | null {
  if (stops.length === 0) return null;
  let nearest = stops[0];
  let minDist = haversineDistance(point, stops[0]);
  for (let i = 1; i < stops.length; i++) {
    const d = haversineDistance(point, stops[i]);
    if (d < minDist) {
      minDist = d;
      nearest = stops[i];
    }
  }
  return nearest;
}

/**
 * Generate intermediate points between two coordinates for smooth polylines
 */
export function interpolateCoords(from: LatLng, to: LatLng, steps: number): [number, number][] {
  const coords: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    coords.push([
      from.lat + (to.lat - from.lat) * t,
      from.lng + (to.lng - from.lng) * t,
    ]);
  }
  return coords;
}

/** Check if a point is within Algiers bounds */
export function isWithinAlgiers(point: LatLng): boolean {
  return (
    point.lat >= 36.60 &&
    point.lat <= 36.90 &&
    point.lng >= 2.80 &&
    point.lng <= 3.35
  );
}

/** Format distance for display */
export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}
