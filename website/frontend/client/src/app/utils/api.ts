export async function fetchStops() {
  const r = await fetch('/api/stops');
  if (!r.ok) throw new Error('Failed to fetch stops');
  const data: Array<{ id: string; name: string; lat: number; lon: number; type: string; isHub: boolean }> = await r.json();
  return data.map(s => ({
    id: s.id,
    name: s.name,
    lat: s.lat,
    lng: s.lon,
    type: (s.type === 'train' ? 'bus' : s.type) as import('../utils/algiers-graph').TransportMode,
    lines: [] as string[],
    isTransfer: s.isHub,
  }));
}

export async function fetchRoutes(
  start: { lat: number; lon: number; stopId?: string },
  end:   { lat: number; lon: number; stopId?: string },
  weights: { time: number; cost: number; co2: number },
  modes: Record<string, boolean>
) {
  try {
    const response = await fetch('/api/route', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        start,
        end,
        weights,
        transportModes: modes,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch routes');
    }

    const data = await response.json();
    return data.routes;
  } catch (error) {
    console.error('Route API error:', error);
    throw error;
  }
}
