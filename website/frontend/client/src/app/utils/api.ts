import { Coordinates, Weights, TransportModes } from '../store/transit-store';

export async function fetchRoutes(
  start: Coordinates,
  end: Coordinates,
  weights: Weights,
  modes: TransportModes
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
