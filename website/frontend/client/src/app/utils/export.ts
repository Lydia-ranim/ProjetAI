import type { Route } from '../utils/algorithms';

export function exportRouteAsJSON(route: Route) {
  const blob = new Blob([JSON.stringify(route, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `algiers-route-${route.label}-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function exportRouteAsText(route: Route): string {
  const segs = route.segments.map((seg, i) =>
    `${i + 1}. ${seg.mode.toUpperCase()}: ${seg.fromName} → ${seg.toName} (${Math.round(seg.durationMin)} min, ${seg.costDzd} DZD, ${Math.round(seg.co2G)}g CO₂)`
  ).join('\n');

  return [
    `Algiers Transit AI — ${route.label.toUpperCase()} ROUTE`,
    `Algorithm: ${route.algorithmUsed} (${route.nodesExpanded} nodes expanded)`,
    ``,
    `Total Time:  ${Math.round(route.summary.totalTimeMin)} min`,
    `Total Cost:  ${route.summary.totalCostDzd} DZD`,
    `CO₂:         ${Math.round(route.summary.totalCo2G)}g (saved ${route.co2SavedVsCarG}g vs car)`,
    `Transfers:   ${route.summary.numTransfers}`,
    ``,
    `Steps:`,
    segs,
  ].join('\n');
}

export function copyRouteToClipboard(route: Route): Promise<void> {
  return navigator.clipboard.writeText(exportRouteAsText(route));
}

export function shareRoute(route: Route) {
  const text = exportRouteAsText(route);
  if (navigator.share) {
    navigator.share({
      title: `Algiers Route — ${route.label}`,
      text,
    }).catch(console.error);
  } else {
    copyRouteToClipboard(route);
  }
}
